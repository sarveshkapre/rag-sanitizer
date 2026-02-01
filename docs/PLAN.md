# PLAN

## Goal
Ship a local-first RAG sanitizer that strips instruction-like text, scores risk, and enforces citations for retrieved chunks.

## Scope (MVP)
- JSONL input/output with chunk metadata.
- Instruction-like detection with transparent flags.
- Deterministic sanitization and risk scoring.
- Citation enforcement policy (requires citations to pass).

## Non-goals (MVP)
- Online scanning or proprietary threat feeds.
- Multilingual NLP classifiers.
- Deep semantic rewriting of content.

## Architecture
- CLI reads JSONL → sanitizer pipeline → JSONL output.
- Core sanitizer is pure and deterministic.
- Policy: flag/strip instruction-like content; compute risk score.

## Stack
- Python 3.11, Typer CLI.
- Ruff for lint/format, mypy for types, pytest for tests.

## Milestones
1. Scaffold repo + CLI + example input/output.
2. Implement sanitizer core + policies.
3. Tests, CI, docs polish.

## Risks
- Over-stripping useful content. Mitigation: expose flags and keep rules simple.
- Under-detecting injections. Mitigation: expand rules in ROADMAP.
