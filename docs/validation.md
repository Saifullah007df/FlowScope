# FlowScope validation record

Executed on 17 October 2026 in the development environment using Python 3.12, NetworkX 3.7, FastAPI 0.143.3 and Node.js 24.19.0. Exact resolved Python dependencies are retained in requirements.lock.

## Executed checks

- 42 pytest tests passed. Coverage includes hand-calculated graph fixtures, all three supplied workflow samples, duplicate/dangling graph rejection, metadata exclusion, wire deduplication, cyclic groups, disconnected components and entry reachability.
- Python tests cover scoped decisions, nested callables, lambdas, comprehensions, match guards, Unicode and concatenated docstrings, size limits and a file-write payload that is parsed without executing.
- API tests cover analysis, saved history, process-level store reopening, comparison, JSON/CSV/HTML exports, deletion, 200-report retention, origin/host restrictions and the HTTP body limit.
- Export tests check HTML escaping and CSV formula neutralization.
- CLI checks verify success, threshold rejection and invalid-source exit codes.
- JavaScript syntax check passed with node --check web/app.js.
- Static HTML/client checks verify unique IDs, referenced DOM elements, labelled controls and local asset paths. Shell launcher syntax was checked with bash -n.

The installed Starlette test client emitted an upstream deprecation warning recommending httpx2. The warning did not fail the suite. No deprecation migration was attempted during this delivery.

## Supplied sample results

| Sample | Nodes | Unique edges | Feedback groups | Normalized structural complexity | Condensed depth |
| --- | ---: | ---: | ---: | ---: | ---: |
| Onboarding | 10 | 12 | 1 | 5 | 5 |
| IoT monitoring | 11 | 12 | 1 | 6 | 4 |
| Order processing | 19 | 19 | 0 | 10 | 8 |

The Python payment example has 14 physical lines, 12 source lines, two functions, one class, maximum scope complexity 6 and maximum syntactic control nesting 3. These values follow the project metric contract.

## Verification limits

A browser preview capability was unavailable for this local application in the managed environment. No real browser interaction, screenshot review or responsive-layout execution is claimed. The responsive CSS and client behavior are implemented, with syntax and static integration checks only. Perform a browser acceptance pass after cloning: analyze each sample, inspect a node, open findings/score tabs, export a report, reopen it from history and compare two saved reports at desktop and mobile widths.

GitHub CI is configured for Python 3.12 and 3.13. A configured workflow is not evidence of a completed hosted run; inspect the actual run after the repository push.
