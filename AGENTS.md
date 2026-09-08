# Generated tools

- This repository is separate from `qmdch1/agent-foundry`; store source in `tools/<name>`.
- Python entry point: `run(input_data: dict) -> dict`; CLI reads JSON stdin and emits exactly one JSON object on stdout. Diagnostics go to stderr.
- Every tool requires manifest, JSON input/output schemas, examples with expected outputs, tests and version. Include only necessary dependencies/files.
- Never commit secrets, production data, caches or virtual environments. Never require root or unrestricted host execution.
- Registry activation requires successful isolated tests, sample/schema checks and a pushed immutable commit. Runtime/dependency policy is owned by Agent Foundry.
- The `tools/<name>/manifest.json` files on the pushed main branch form the shared catalog. Other Agent Foundry installations discover them without sharing a Registry DB, pin the published commit, validate locally, and install through their separate Worker. Keep the folder name and manifest name identical and never publish credentials or local usage data.
- Database definitions use declarative additive tables and ordinary indexes only; never key constraints or destructive SQL.
