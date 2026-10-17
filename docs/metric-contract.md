# FlowScope metric reference
Engine version 1.0.0. Static analysis never imports, evaluates or executes submitted code or workflow actions. Numbers describe supported structure; they do not prove correctness, security or actual runtime behavior.

## Supported inputs
Python source is parsed by the Python interpreter's AST and tokenizer. Use Python 3.12 or later. Grammar support follows the interpreter version.

Auto mode treats input starting with { or [ as a workflow and other input as Python. Choose Python explicitly for a source file beginning with a dictionary or list literal.

Workflow input is a Node-RED node array, or a custom object containing a nodes array. Nodes require unique string or integer IDs; labels use name or label; type uses type or action. Node-RED wires are arrays of output-port target-ID arrays. Custom next is one target ID or an array. Custom edges are objects with source and target IDs. Both endpoints must exist.

Tabs, comments and groups are metadata and excluded. Node-RED subflows and link nodes are explicitly rejected because this version cannot safely expand their implicit connectivity. Native Zapier and Power Automate exports, C, C++, Java and C# are not supported. Convert workflows to an explicit flattened graph first; do not rename a native export and assume it is supported.

## Workflow metrics
N is the number of executable nodes. E is the number of unique directed endpoint pairs. P is the number of weakly connected components. Repeated wires between the same endpoints are counted once for topology metrics. Exported connection_count preserves the original wire count. Different output-port semantics and branch feasibility are not modeled.

Graph cycle rank = E − N + P. This is the independent cycle rank of the underlying topology, not the number of directed elementary cycles or the number of test cases.

Normalized structural complexity = E − N + S + T. S and T are source and sink strongly connected components, respectively. For each weak component, add a virtual entry connected to each source group and a virtual exit connected from each sink group. Apply E' − N' + 2 to that component and sum. This normalizes multiple starts and exits. It is a graph index, not a claim of McCabe complexity for arbitrary low-code execution semantics. A simple chain scores 1, a diamond 2, a three-way terminal branch 3 and an isolated directed cycle 2.

Feedback groups are strongly connected components with more than one node, or a self-loop. They locate feedback without expensive enumeration of every possible cycle. A group can contain multiple overlapping cycles.

Condensed depth is the longest path in transitions after strongly connected components have been collapsed into a DAG. It is not conditional nesting depth. DAG path depth is available only when the original graph is acyclic; otherwise it is null. An isolated node has depth 0.

Fan-out and fan-in count unique outgoing and incoming targets. Four or more triggers a review finding. Parallel dispatch and conditional branching are not distinguished automatically.

Entry reachability recognizes types inject, start, trigger, http in, mqtt in and trigger_ prefixes. Nodes not reachable from any recognized entry are flagged. With no recognized entry, reachability is unavailable (null), not zero. Unreachable findings can reflect unsupported trigger classification.

## Python size and scope metrics
LOC counts physical lines using splitlines. Blank lines contain only whitespace. Comment lines contain a tokenizer COMMENT token, including inline comments. Categories can overlap and do not add up to LOC.

SLOC counts physical lines containing non-comment tokens, excluding actual module, class and function docstring tokens. Multiline strings assigned to variables remain code. SLOC is source-bearing physical lines, not a count of executable statements. No AST-based static measure can prove that a line will execute.

Functions include sync and async function definitions, methods and nested functions. Lambdas are counted separately. Classes include nested classes. A report lists the module and every callable, including lambdas, with source line spans. Nested callable decisions do not increase their enclosing callable's complexity.

Per-scope complexity = 1 + decision increments. One increment is counted for each if (including elif), for, async for, while, conditional expression, except handler and assert; each and/or operator; each comprehension generator and filter; each non-wildcard match case and each case guard. Unconditional else, finally and with add no complexity. Match pattern alternatives are not separately counted. This is a documented project policy, not guaranteed byte-for-byte equivalence with Radon or another analyzer.

Maximum complexity is the maximum over the module and callable scopes. Total scope complexity is their sum and includes one base path per scope. Module decisions include class-body statements but skip callable definitions, annotations, defaults and decorators. Callable decisions analyze bodies only; definition-time expressions are outside this counting policy.

Decision count is the sum of policy increments across scopes. Nesting counts syntactically nested if, loops, try, with and match blocks per scope. Elif is represented as nested If in the AST and increases this syntactic measure. Comprehensions and conditional expressions contribute complexity but are excluded from control-block nesting.

## Review score policy
Scores start at 100 and subtract visible nonnegative penalties. Each penalty and the summed deduction are capped at 100. The score is an unvalidated heuristic for prioritizing review, not an empirical maintainability index, defect probability or estimate of engineering effort. Grades: A ≥ 85, B ≥ 70, C ≥ 50, D < 50.

Workflow deductions: 3 points for each outgoing target above two per node; 8 per feedback group; 2 per condensed transition above five; 3 per unreachable node when entry analysis is available; 4 per disconnected component above one. Legitimate parallelism and independent flows may incur deductions. Size alone is not penalized.

Python deductions: 4 points per maximum complexity point above five; 5 per control nesting level above three; 0.1 per callable source-span line above fifty, summed across callables. Callable spans include comments and whitespace. Scores from different analysis modes are not directly comparable.

## Limits and interpretation
Inputs are limited to 1 MB of UTF-8, 1500 workflow records, 6000 exported connections and 100000 Python AST nodes. Deeply nested invalid inputs are rejected. The topology drawing displays at most the first 300 nodes; all accepted nodes remain in metrics and JSON exports. Parser and rendering limits are deliberate, not silent omissions.

Reports include engine version and SHA256 of the input. Same-kind comparison gives after-minus-before metric deltas and workflow node/edge changes. It does not align renamed IDs, compare source text or prove behavioral equivalence. Re-run under the same engine policy before interpreting a trend.

## References
Python AST documentation: https://docs.python.org/3/library/ast.html
Python tokenize documentation: https://docs.python.org/3/library/tokenize.html
NetworkX condensation: https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.components.condensation.html
NetworkX DAG longest path length: https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.dag.dag_longest_path_length.html
Radon metric definitions for comparison: https://radon.readthedocs.io/en/latest/intro.html
