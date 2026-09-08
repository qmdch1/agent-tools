# Generated tools

- This repository is separate from `qmdch1/agent-foundry`; store source in `tools/<name>`.
- Python entry point: `run(input_data: dict) -> dict`; CLI reads JSON stdin and emits exactly one JSON object on stdout. Diagnostics go to stderr.
- Every tool requires manifest, JSON input/output schemas, examples with expected outputs, tests and version. Include only necessary dependencies/files.
- Never commit secrets, production data, caches or virtual environments. Never require root or unrestricted host execution.
- Registry activation requires successful isolated tests, sample/schema checks and a pushed immutable commit. Runtime/dependency policy is owned by Agent Foundry.
- Database definitions use declarative additive tables and ordinary indexes only; never key constraints or destructive SQL.
