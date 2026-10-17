import json
from pathlib import Path
import pytest
from flowscope import analyze, AnalysisError

ROOT=Path(__file__).resolve().parent.parent

def flow(nodes,edges):
    return json.dumps({'nodes':[{'id':n,'type':'trigger' if n=='a' else 'generic'} for n in nodes],'edges':[{'source':a,'target':b} for a,b in edges]})

@pytest.mark.parametrize('nodes,edges,index,depth,groups',[
    (['a'],[],1,0,0),
    (['a','b','c'],[('a','b'),('b','c')],1,2,0),
    (['a','b','c','d'],[('a','b'),('a','c'),('b','d'),('c','d')],2,2,0),
    (['a','b','c','d'],[('a','b'),('a','c'),('a','d')],3,1,0),
    (['a','b'],[('a','b'),('b','a')],2,0,1),
    (['a'],[('a','a')],2,0,1),
    (['a','b'],[],2,0,0),
])
def test_hand_calculated_graphs(nodes,edges,index,depth,groups):
    r=analyze(flow(nodes,edges))
    assert r['metrics']['normalized_complexity']==index
    assert r['metrics']['condensed_depth']==depth
    assert r['metrics']['cycle_groups']==groups
    assert r['metrics']['dag_depth'] is None if groups else r['metrics']['dag_depth']==depth

@pytest.mark.parametrize('filename,nodes,edges,cycles',[
    ('onboarding.json',10,12,1),('iot-monitoring.json',11,12,1),('order-processing.json',19,19,0)
])
def test_supplied_examples(filename,nodes,edges,cycles):
    r=analyze((ROOT/'examples'/filename).read_text())
    assert r['metrics']['nodes']==nodes
    assert r['metrics']['edges']==edges
    assert r['metrics']['cycle_groups']==cycles
    assert len(r['content_sha256'])==64

@pytest.mark.parametrize('data',[
    {'nodes':[{'id':'a'},{'id':'a'}]},
    {'nodes':[{'id':'a','next':['missing']}]},
    {'nodes':[{'type':'trigger'}]},
    {'nodes':[{'id':False}]},
    {'nodes':[{'id':'a','wires':['b']}]},
    {'nodes':[{'id':'a','type':'subflow:abc'}]},
    {'nodes':[{'id':'a','type':'link out'}]},
    {'actions':{'a':{'runAfter':[]}}},
    {'nodes':[]},
    {'nodes':[42]},
])
def test_reject_ambiguous_graphs(data):
    with pytest.raises(AnalysisError):analyze(json.dumps(data),'workflow')

def test_port_duplicates_and_metadata():
    r=analyze(json.dumps([{'id':'tab','type':'tab'},{'id':'a','type':'inject','wires':[['b'],['b']]},{'id':'b','type':'debug','wires':[]}]))
    assert r['metrics']['nodes']==2
    assert r['metrics']['edges']==1
    assert r['metrics']['connection_count']==2
    assert len(r['warnings'])>=2

def test_reachability_unknown_and_known():
    a=analyze(json.dumps({'nodes':[{'id':'x'},{'id':'y'}]}))
    assert a['metrics']['unreachable_nodes'] is None
    b=analyze(flow(['a','b'],[]))
    assert b['metrics']['unreachable_nodes']==1

def test_python_scope_and_boolean_decisions():
    text='''class Service:
    def f(self, x):
        if x and x > 1:
            for item in x:
                if item:
                    return item
        return None
    async def g(self):
        return 0
'''
    r=analyze(text,'python');m=r['metrics'];units={x['name']:x for x in r['units']}
    assert m['functions']==2 and m['classes']==1
    assert units['Service.f']['complexity']==5
    assert units['Service.f']['nesting']==3
    assert units['Service.g']['complexity']==1
    assert units['<module>']['complexity']==1
    assert m['decision_count']==4

def test_docstrings_and_assigned_multiline_strings():
    text='''"""module doc
second line"""
# comment
x = """a
b"""

def f():
    """function doc"""
    return x # inline
'''
    m=analyze(text,'python')['metrics']
    assert m['loc']==9 and m['sloc']==4
    assert m['docstring_lines']==3 and m['comment_lines']==2
    m=analyze('"doc"; x = 1\n','python')['metrics']
    assert m['sloc']==1

def test_nested_callable_not_double_counted():
    units={u['name']:u for u in analyze('def outer():\n    def inner(x):\n        if x: return 1\n    return inner\n')['units']}
    assert units['outer']['complexity']==1
    assert units['outer.inner']['complexity']==2

def test_comprehensions_match_and_lambda():
    text='''f = lambda x: 1 if x else 0
def test(x):
    result = [n for n in x if n]
    match x:
        case 1 if x:
            return 1
        case _:
            return result
'''
    r=analyze(text,'python')
    assert r['metrics']['lambdas']==1
    assert next(u for u in r['units'] if u['name']=='test')['complexity']==5

def test_never_execute_python(tmp_path):
    target=tmp_path/'executed'
    analyze(f'open({str(target)!r}, "w").write("bad")\n','python')
    assert not target.exists()

@pytest.mark.parametrize('text,kind',[('', 'auto'),('{invalid','workflow'),('def !!!','python'),('x'*1_000_001,'python')])
def test_invalid_input(text,kind):
    with pytest.raises(AnalysisError):analyze(text,kind)

def test_graph_limits():
    with pytest.raises(AnalysisError):analyze(json.dumps({'nodes':[{'id':str(i)} for i in range(1501)]}))
    with pytest.raises(AnalysisError):analyze(json.dumps({'nodes':[{'id':'a','next':['a']*6001}]}))

def test_score_deductions_are_transparent():
    r=analyze((ROOT/'examples'/'order-processing.json').read_text())
    score=r['quality']
    assert score['value']==round(100-min(100,sum(p['points'] for p in score['penalties'])),2)
    assert all(p['points']>=0 for p in score['penalties'])


def test_unicode_and_concatenated_docstrings():
    r=analyze('"café" " doc"\nx=1\n','python')
    assert r['metrics']['sloc']==1
