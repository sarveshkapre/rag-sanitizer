# RAG Sanitizer

Sanitize retrieved chunks for RAG prompts by stripping instruction-like content, scoring risk, and enforcing citation rules.

Status: **backlog → scaffolded (in progress)**

## What it does
- Detects instruction-like text (prompt injections, role directives, tool instructions).
- Produces a sanitized version with suspicious spans removed.
- Assigns a risk score + flags and enforces citations policy.

## Quickstart
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]

rag-sanitize --in examples/chunks.jsonl --out sanitized.jsonl
```

## Rules (configurable regex packs)
Dump the built-in rules to a JSON file, edit, then re-run:
```bash
rag-sanitize --dump-default-rules rules.json
rag-sanitize --in examples/chunks.jsonl --out sanitized.jsonl --rules rules.json
```

## CI/CD-friendly usage
Read from stdin / write to stdout and fail the run if risk is too high:
```bash
cat examples/chunks.jsonl | rag-sanitize --in - --out - --max-risk 0.7 > sanitized.jsonl
```

## Input format (JSONL)
Each line is a JSON object:
```json
{"id":"chunk-1","text":"...","source":"doc.pdf","citations":["doc.pdf#page=3"]}
```

## Output format (JSONL)
```json
{"id":"chunk-1","sanitized_text":"...","risk_score":0.3,"flags":["instruction_like"],"source":"doc.pdf","citations":["doc.pdf#page=3"],"citation_ok":true,"redactions":[{"line_number":1,"type":"instruction_like","matched_patterns":["system prompt"]}]}
```

## Docker
```bash
docker build -t rag-sanitizer .
```

## Project docs
- `docs/PLAN.md`
- `docs/PROJECT.md`
- `docs/ROADMAP.md`
