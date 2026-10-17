"""Deterministic static analysis. Uploaded code is parsed, never executed."""
import ast
import hashlib
import io
import json
import tokenize
from collections import Counter
import networkx as nx

ENGINE_VERSION = '1.0.0'
MAX_BYTES = 1_000_000
MAX_NODES = 1500
MAX_EDGES = 6000

class AnalysisError(ValueError):
    pass

def check_text(text):
    if not isinstance(text, str) or not text.strip():
        raise AnalysisError('Provide a non-empty UTF-8 file or pasted input.')
    if len(text.encode('utf-8')) > MAX_BYTES:
        raise AnalysisError('Input exceeds the 1 MB analysis limit.')

def identifier(value):
    if isinstance(value, bool) or not isinstance(value, (str, int)) or not str(value).strip():
        raise AnalysisError('Every node and edge endpoint needs a non-empty string or integer ID.')
    if len(str(value)) > 160:
        raise AnalysisError('Node IDs must contain at most 160 characters.')
    return str(value)

def normalize_flow(data):
    explicit = []
    if isinstance(data, list):
        items, adapter = data, 'node-red'
    elif isinstance(data, dict) and isinstance(data.get('nodes'), list):
        items, adapter = data['nodes'], 'custom'
        if 'edges' in data:
            if not isinstance(data['edges'], list):
                raise AnalysisError('edges must be an array.')
            explicit = data['edges']
    else:
        raise AnalysisError('Expected a Node-RED node array or an object containing a nodes array. Native Zapier and Power Automate exports require a dedicated adapter.')
    if len(items) > MAX_NODES:
        raise AnalysisError(f'At most {MAX_NODES} nodes can be analyzed.')
    nodes, connections, warnings, ignored = {}, [], [], []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise AnalysisError(f'Node at index {index} must be an object.')
        kind = item.get('type', item.get('action', 'generic'))
        if not isinstance(kind, str):
            raise AnalysisError('Node type or action must be a string.')
        if kind in {'tab', 'comment', 'group'}:
            ignored.append(str(item.get('id', index)))
            continue
        if kind.startswith('subflow') or kind in {'link in', 'link out', 'link call'}:
            raise AnalysisError('Subflows and Node-RED link nodes are not expanded by this adapter. Export an explicit flattened graph before analysis.')
        key = identifier(item.get('id'))
        if key in nodes:
            raise AnalysisError(f'Duplicate node ID: {key}')
        name = item.get('name') or item.get('label') or kind
        if not isinstance(name, str) or len(name) > 240:
            raise AnalysisError('Node names must be strings of at most 240 characters.')
        nodes[key] = {'id': key, 'label': name, 'type': kind, 'source_index': index}
        if 'wires' in item:
            wires = item['wires']
            if not isinstance(wires, list) or any(not isinstance(port, list) for port in wires):
                raise AnalysisError(f'wires on {key} must be an array of output-port arrays.')
            for port, targets in enumerate(wires):
                for target in targets:
                    connections.append((key, identifier(target), port))
        if 'next' in item:
            targets = item['next']
            if isinstance(targets, (str, int)) and not isinstance(targets, bool):
                targets = [targets]
            if not isinstance(targets, list):
                raise AnalysisError(f'next on {key} must be an ID or an array of IDs.')
            for target in targets:
                connections.append((key, identifier(target), None))
        if len(connections) > MAX_EDGES:
            raise AnalysisError(f'At most {MAX_EDGES} connections can be analyzed.')
    if not nodes:
        raise AnalysisError('No executable workflow nodes were found.')
    if len(explicit) + len(connections) > MAX_EDGES:
        raise AnalysisError(f'At most {MAX_EDGES} connections can be analyzed.')
    for edge in explicit:
        if not isinstance(edge, dict):
            raise AnalysisError('Each explicit edge needs source and target fields.')
        connections.append((identifier(edge.get('source')), identifier(edge.get('target')), None))
    graph = nx.DiGraph()
    graph.add_nodes_from(nodes)
    for source, target, port in connections:
        if source not in nodes or target not in nodes:
            raise AnalysisError(f'Dangling connection {source} → {target}. Define both endpoints.')
        graph.add_edge(source, target)
    if len(connections) != graph.number_of_edges():
        warnings.append('Repeated endpoint pairs are collapsed for topology metrics; connection_count retains all exported wires, including separate output ports.')
    if ignored:
        warnings.append(f'Excluded {len(ignored)} Node-RED metadata nodes (tabs, comments or groups).')
    if adapter == 'node-red':
        warnings.append('Node-RED wiring is structural: function bodies, message topics, hidden dependencies and branch feasibility are not interpreted.')
    return graph, nodes, connections, warnings, adapter

def score_result(penalties):
    penalties = [dict(code=k, label=label, points=round(min(100, value), 2)) for k, label, value in penalties if value > 0]
    total = round(min(100, sum(x['points'] for x in penalties)), 2)
    score = round(100 - total, 2)
    return {'value': score, 'grade': 'A' if score >= 85 else 'B' if score >= 70 else 'C' if score >= 50 else 'D', 'penalties': penalties, 'penalty_total': total, 'policy_version': 'structural-review-v1', 'meaning': 'Transparent project heuristic for review prioritization; not a validated maintainability or defect prediction model.'}

def analyze_flow(text):
    try:
        data = json.loads(text)
    except (ValueError, RecursionError) as exc:
        raise AnalysisError(f'Invalid JSON: {str(exc)[:200]}') from None
    graph, nodes, connections, warnings, adapter = normalize_flow(data)
    sccs = sorted([sorted(c) for c in nx.strongly_connected_components(graph)], key=lambda c:c[0])
    condensed = nx.condensation(graph, sccs)
    layers = dict.fromkeys(condensed, 0)
    for component in nx.topological_sort(condensed):
        layers[component] = max((layers[p] + 1 for p in condensed.predecessors(component)), default=0)
    mapping = condensed.graph['mapping']
    cycles = [c for c in sccs if len(c) > 1 or graph.has_edge(c[0], c[0])]
    cyclic_ids = {n for c in cycles for n in c}
    entry_ids = [key for key, node in nodes.items() if node['type'] in {'inject', 'start', 'trigger', 'http in', 'mqtt in'} or node['type'].startswith('trigger_')]
    reached = set(entry_ids)
    for key in entry_ids:
        reached.update(nx.descendants(graph, key))
    unreachable = sorted(set(nodes) - reached) if entry_ids else []
    if not entry_ids:
        warnings.append('No recognized trigger or explicit start node: entry reachability is unavailable, rather than assuming an entry.')
    components = nx.number_weakly_connected_components(graph)
    source_count = sum(condensed.in_degree(c) == 0 for c in condensed)
    sink_count = sum(condensed.out_degree(c) == 0 for c in condensed)
    n, e = len(nodes), graph.number_of_edges()
    normalized = e - n + source_count + sink_count
    findings = []
    def finding(code, severity, ids, title, detail):
        findings.append({'code':code, 'severity':severity, 'node_ids':ids, 'title':title, 'detail':detail})
    for key in nodes:
        out, inward = graph.out_degree(key), graph.in_degree(key)
        nodes[key].update(fan_out=out, fan_in=inward, layer=layers[mapping[key]], cyclic=key in cyclic_ids, unreachable=key in unreachable)
        if out >= 4:
            finding('fan-out', 'warning', [key], f'{out} outgoing targets', 'Review whether this node mixes routing and parallel responsibilities; isolate cohesive branches and document error handling.')
        if inward >= 4:
            finding('fan-in', 'info', [key], f'{inward} incoming sources', 'Review merge semantics and idempotency. Incoming messages are not necessarily synchronized.')
    for cycle in cycles:
        finding('cycle', 'warning', cycle, f'Feedback group with {len(cycle)} node(s)', 'Check termination, retry bounds and backoff. This is a strongly connected component, not an enumeration of every elementary cycle.')
    if unreachable:
        finding('unreachable', 'warning', unreachable, 'Nodes unreachable from recognized entries', 'Review unused branches or missing trigger classification. Reachability depends on the supported entry-type list.')
    if components > 1:
        finding('disconnected', 'info', [], f'{components} disconnected components', 'Independent flows may be intentional. Analyze their ownership and lifecycle separately.')
    depth = max(layers.values(), default=0)
    if depth >= 8:
        finding('depth', 'info', [], f'{depth} transitions between feedback groups', 'Review long dependency chains. Condensed depth does not measure conditional nesting.')
    quality = score_result([
        ('branching','Outgoing targets above two',sum(max(0, graph.out_degree(k)-2)*3 for k in nodes)),
        ('feedback','Feedback groups',len(cycles)*8),
        ('depth','Condensed depth above five',max(0,depth-5)*2),
        ('unreachable','Nodes unreachable from recognized entries',len(unreachable)*3),
        ('components','Disconnected components above one',max(0,components-1)*4),
    ])
    return {'kind':'workflow','adapter':adapter,'metrics':{'nodes':n,'edges':e,'connection_count':len(connections),'components':components,'graph_cycle_rank':e-n+components,'normalized_complexity':normalized,'source_groups':source_count,'sink_groups':sink_count,'condensed_depth':depth,'dag_depth':nx.dag_longest_path_length(graph) if not cycles else None,'cycle_groups':len(cycles),'cyclic_nodes':len(cyclic_ids),'max_fan_out':max(dict(graph.out_degree()).values()),'max_fan_in':max(dict(graph.in_degree()).values()),'unreachable_nodes':len(unreachable) if entry_ids else None},'quality':quality,'findings':findings,'warnings':warnings,'graph':{'nodes':list(nodes.values()),'edges':[{'source':a,'target':b} for a,b in graph.edges()],'cycle_groups':cycles,'entries':entry_ids},'units':[]}

CONTROL = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.TryStar, ast.With, ast.AsyncWith, ast.Match)
FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)
class ScopeVisitor(ast.NodeVisitor):
    def __init__(self):
        self.decisions = 0
        self.nesting = 0
        self.depth = 0
    def visit_FunctionDef(self, node):
        pass
    visit_AsyncFunctionDef = visit_FunctionDef
    visit_Lambda = visit_FunctionDef
    def visit(self, node):
        if isinstance(node, (ast.If,ast.For,ast.AsyncFor,ast.While,ast.IfExp,ast.ExceptHandler,ast.Assert)):
            self.decisions += 1
        if isinstance(node, ast.BoolOp):
            self.decisions += len(node.values)-1
        if isinstance(node, ast.comprehension):
            self.decisions += 1 + len(node.ifs)
        if isinstance(node, ast.match_case):
            wildcard = isinstance(node.pattern, ast.MatchAs) and node.pattern.pattern is None
            self.decisions += int(not wildcard) + int(node.guard is not None)
        increment = isinstance(node, CONTROL)
        if increment:
            self.depth += 1
            self.nesting = max(self.nesting, self.depth)
        result = super().visit(node)
        if increment:
            self.depth -= 1
        return result

def analyze_python(text):
    try:
        tree = ast.parse(text)
        if sum(1 for _ in ast.walk(tree)) > 100_000:
            raise AnalysisError('Python input exceeds the 100000 AST node limit.')
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (SyntaxError, tokenize.TokenError, RecursionError, ValueError) as exc:
        raise AnalysisError(f'Python parse error: {str(exc)[:240]}') from None
    doc_lines = set()
    doc_spans = set()
    for item in ast.walk(tree):
        if isinstance(item,(ast.Module,ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)) and item.body:
            first = item.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                doc_lines.update(range(first.lineno,first.end_lineno+1))
                doc_spans.add((first.value.lineno,first.value.col_offset,first.value.end_lineno,first.value.end_col_offset))
    code_lines, comment_lines = set(), set()
    skip = {tokenize.ENCODING, tokenize.ENDMARKER, tokenize.NEWLINE, tokenize.NL, tokenize.INDENT, tokenize.DEDENT, tokenize.COMMENT}
    physical = text.splitlines(keepends=True)
    for token in tokens:
        if token.type == tokenize.COMMENT:
            comment_lines.add(token.start[0])
        elif token.type not in skip:
            if token.type == tokenize.STRING:
                start = (token.start[0], len(physical[token.start[0]-1][:token.start[1]].encode('utf-8')))
                end = (token.end[0], len(physical[token.end[0]-1][:token.end[1]].encode('utf-8')))
                if any((a,b) <= start and end <= (c,d) for a,b,c,d in doc_spans):
                    continue
            code_lines.update(range(token.start[0], token.end[0]+1))
    sloc = len(code_lines)
    units = []
    module = ScopeVisitor(); module.visit(tree)
    units.append({'name':'<module>','kind':'module','line':1,'end_line':max(1,len(text.splitlines())),'complexity':module.decisions+1,'decisions':module.decisions,'nesting':module.nesting})
    def collect(node, prefix=''):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, FUNCTIONS):
                name = prefix + (child.name if not isinstance(child,ast.Lambda) else '<lambda>')
                visitor = ScopeVisitor()
                contents = child.body if isinstance(child.body,list) else [child.body]
                for statement in contents: visitor.visit(statement)
                units.append({'name':name,'kind':'lambda' if isinstance(child,ast.Lambda) else 'function','line':child.lineno,'end_line':child.end_lineno,'complexity':visitor.decisions+1,'decisions':visitor.decisions,'nesting':visitor.nesting})
                collect(child,name+'.')
            elif isinstance(child,ast.ClassDef):
                collect(child,prefix+child.name+'.')
            else:
                collect(child,prefix)
    collect(tree)
    callables = [x for x in units if x['kind'] != 'module']
    max_cc = max(x['complexity'] for x in units)
    max_depth = max(x['nesting'] for x in units)
    findings=[]
    for unit in units:
        if unit['complexity'] > 10:
            findings.append({'code':'complexity','severity':'warning','node_ids':[],'line':unit['line'],'title':f"{unit['name']} has complexity {unit['complexity']}",'detail':'Separate responsibilities and test each decision outcome before refactoring.'})
        if unit['nesting'] > 3:
            findings.append({'code':'nesting','severity':'warning','node_ids':[],'line':unit['line'],'title':f"{unit['name']} nests {unit['nesting']} control levels",'detail':'Consider guard clauses and cohesive helper functions.'})
    quality = score_result([('complexity','Maximum scope complexity above five',max(0,max_cc-5)*4),('nesting','Control nesting above three',max(0,max_depth-3)*5),('size','Callable spans above fifty lines',sum(max(0,x['end_line']-x['line']+1-50)/10 for x in callables))])
    return {'kind':'python','adapter':'python-ast-v1','metrics':{'loc':len(text.splitlines()),'sloc':sloc,'blank_lines':sum(not x.strip() for x in text.splitlines()),'comment_lines':len(comment_lines),'docstring_lines':len(doc_lines),'functions':sum(isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef)) for x in ast.walk(tree)),'lambdas':sum(isinstance(x,ast.Lambda) for x in ast.walk(tree)),'classes':sum(isinstance(x,ast.ClassDef) for x in ast.walk(tree)),'decision_count':sum(x['decisions'] for x in units),'max_complexity':max_cc,'total_scope_complexity':sum(x['complexity'] for x in units),'max_nesting':max_depth},'quality':quality,'findings':findings,'warnings':['Python syntax is analyzed without importing or executing the source. Metrics describe syntax, not runtime behavior.','Complexity follows the documented FlowScope counting policy and may differ from Radon or other tools.'],'units':units,'graph':None}

def analyze(text, kind='auto'):
    check_text(text)
    if kind not in {'auto','workflow','python'}:
        raise AnalysisError('Analysis kind must be auto, workflow or python.')
    if kind=='auto':
        kind='workflow' if text.lstrip().startswith(('[','{')) else 'python'
    try:
        result = analyze_flow(text) if kind=='workflow' else analyze_python(text)
    except RecursionError:
        raise AnalysisError('Input nesting exceeds the safe parser limit.') from None
    return dict(result,engine_version=ENGINE_VERSION,content_sha256=hashlib.sha256(text.encode()).hexdigest())
