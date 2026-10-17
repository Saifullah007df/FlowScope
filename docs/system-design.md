# FlowScope system design

## Goal and scope
Combine the supplied visual-flow prototype and software-size presentation into a reproducible local analysis workbench. Preserve the three workflow examples. Deliver trustworthy Python source metrics and visual graph metrics through independent adapters; avoid unsupported multi-language or multi-platform claims.

## Architecture
Browser console → validated FastAPI API → static analysis service → workflow normalizer / Python AST parser → normalized report → SQLite history and report exporters.

The browser handles file selection and graph drawing. The server never executes submitted code, calls workflow integrations or retrieves submitted URLs. A CLI uses the same analysis service without history or the server. The frontend uses bundled vanilla JavaScript, CSS and SVG: no CDN, framework build or online font dependency.

## Modules
- analysis.py validates bounded input and computes a versioned report contract.
- storage.py stores computed reports with UTC timestamps and retention of the latest 200 records.
- reports.py compares same-kind reports and exports JSON, spreadsheet-safe CSV and escaped printable HTML.
- api.py serves loopback web assets, examples, report CRUD and analysis.
- web/ implements input, topology inspection, scope tables, explainable scoring, report history and comparisons.
- tests/ covers mathematical fixtures, parser edge cases, input validation, persistence, exports and HTTP restrictions.

## Analysis lifecycle
1. Upload or paste input; choose auto, workflow or Python.
2. Enforce byte, schema and graph-size limits before graph algorithms.
3. Parse without execution; fail with a readable error when interpretation is unsupported.
4. Compute structural metrics and evidence-linked findings under the documented contract.
5. Save only the report and input hash, then render results.
6. Compare, export or explicitly delete a report.

## Improvements over the supplied prototype
- Reject duplicate IDs and dangling edges instead of inventing anonymous graph nodes.
- Exclude Node-RED metadata and reject unsupported implicit subflow/link wiring.
- Replace arbitrary cycle-count-times-five depth with SCC condensation depth.
- Normalize graph entry/exit structure and label the result as a graph index.
- Preserve exported wire count while documenting topology deduplication.
- Separate deterministic measurements from a transparent configurable-in-code scoring policy.
- Add real Python source parsing, history, comparisons, CLI and export support.
- Use DOM text nodes and HTML escaping for untrusted labels; remove raw HTML interpolation of uploaded names.

## Data and privacy
A report contains metadata, graph labels and connections or Python scope names/line spans, metrics, findings, score deductions, engine version and input hash. It does not retain the raw JSON or Python source. Graph labels and identifiers may still be sensitive. History is local and unencrypted; protect the host account and database backups. Do not commit runtime/.

## Deployment boundary
Designed for one trusted user on 127.0.0.1. No account management or multi-tenant authorization is provided. Host-header checks, same-origin mutation checks and a request-body cap reduce local browser abuse. This is not an Internet-ready server; use an authenticated deployment design with request deadlines and process isolation before network exposure. No authentication claims are made.

## Delivery phases
1. Define adapters and metric contracts.
2. Implement deterministic analysis and validation.
3. Add persistent report API and comparisons/exports.
4. Build accessible responsive analysis console and graph inspector.
5. Verify algorithm fixtures, API workflows and UI resources.
6. Package reproducible installation, tests, CI and GitHub source delivery.

## Future work
Native Power Automate and Zapier adapters need representative schemas and fixtures. Additional source languages require parsers and language-specific counting contracts. Calibrate review-score weights against independently labelled maintenance outcomes before claiming prediction quality. Add authenticated shared workspaces only with a new identity and storage model.
