# FlowScope

A local software size and complexity workbench for **Python source** and **visual workflow JSON**. Inspect graphs, feedback loops, source scopes and explainable review scores without executing submitted code.

## Run

Requires Python 3.12+ and a browser. No Node.js build is required.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt -c requirements.lock
python -m uvicorn flowscope.api:create_app --factory --host 127.0.0.1 --port 8000
```

Alternatively run `bash run.sh` for setup and launch.

Open **http://127.0.0.1:8000**. Choose a bundled sample, select **Analyze structure**, and inspect Structure, Findings and Score breakdown. A separate terminal can run:

```bash
source .venv/bin/activate
python -m flowscope examples/order-processing.json
python -m flowscope examples/payment-service.py --kind python --output report.json
python -m flowscope examples/order-processing.json --fail-score-below 70
```

CLI exit codes: 0 success, 1 score below the requested threshold, 2 invalid/unreadable input. The CLI never writes history. Workflow scores are structural review heuristics, not validated software quality ratings.

## Capabilities

- Node-RED wiring or explicit custom JSON graphs with IDs and next/wires/edges.
- Python AST and token-based LOC, SLOC, function/class counts, decisions, complexity and syntactic nesting.
- Deterministic SCC-based feedback detection and condensed graph depth; multiple entry/exit normalization.
- Interactive SVG topology with pan, zoom, node search and keyboard-accessible node inspection.
- Source scope tables, structural findings and score deduction explanations.
- Local SQLite report history, project/title filtering, same-kind comparisons and graph deltas.
- JSON, CSV and printable HTML exports. Print HTML from your browser for PDF.
- Input validation, resource limits and escaped output. Submitted code and workflow integrations are never executed.

## Input examples

```json
{"nodes": [
  {"id":"start", "type":"trigger", "next":["end"]},
  {"id":"end", "type":"end"}
]}
```

Or use a nodes array with Node-RED `wires: [["target-id"]]`. See [metric contract](docs/metric-contract.md) for exact schemas and rules.

**Not supported:** native Zapier/Power Automate exports, Node-RED implicit link/subflow expansion, C/C++/Java/C# parsing or runtime bug detection. JSON exports must model explicit connectivity. Arbitrary dictionary guessing from the prototype is deliberately removed.

## Architecture and documentation

[System design](docs/system-design.md) · [Metric contract](docs/metric-contract.md) · [Validation record](docs/validation.md)

`flowscope/` holds the shared engine, API, storage, export and CLI modules. `web/` contains a self-contained console with no CDN dependencies. `examples/` preserves the three supplied workflow fixtures plus a Python fixture.

## Test

```bash
python -m pip install -r requirements-dev.txt -c requirements.lock
python -m pytest -q
node --check web/app.js  # optional syntax check if Node is installed
```

GitHub Actions runs pytest on Python 3.12 and 3.13. Tests include graph hand calculations, cycles, disconnected nodes, malformed input, real API persistence/restart, comparison and export safety.

## Privacy and limits

Bind to 127.0.0.1. This is a single-user local workbench without accounts, not an authenticated public service. Host and same-origin mutation checks are enabled. Default database: `runtime/history.sqlite3`; change it with `FLOWSCOPE_DB`.

Only computed reports and input hashes are retained, not raw source. Reports can still contain sensitive workflow labels and Python scope names. History retains the most recent 200 reports and deletes older ones. Use Delete to remove individual reports; this cannot be undone through the app. Keep runtime state outside Git.

Limits: 1 MB input, 1500 workflow records, 6000 connections, 100000 Python AST nodes. Graph drawing shows at most 300 nodes with an explicit notice. All accepted nodes are included in computed metrics and JSON exports.

## Original material

This is a redesign of the supplied Streamlit visual-flow analyzer, informed by the supplied software-size and complexity presentation and help document. The original three workflow samples are retained under descriptive names. No external workflow APIs are invoked. See the design document for changes and remaining extensions.
