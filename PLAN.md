# RAG Sanitizer

Sanitize retrieved chunks for RAG prompts by stripping instruction-like content, scoring risk, and enforcing citation rules.

Canonical plan lives in `docs/PLAN.md`.

## What shipped recently
- Configurable rule packs (`--rules`, `--dump-default-rules`).
- Stdin/stdout support (`--in -`, `--out -`) plus risk gating (`--max-risk`).
- Output now includes `source` + `redactions` metadata for transparency.
- Optional Markdown-aware sanitization (`--markdown`).

## What ships next
- Markdown/HTML-aware sanitization (preserve structure; strip only directive spans).
- Pluggable presets (named rulesets + directory discovery).

## Commands
See `docs/PROJECT.md` (or run `make check` for the full quality gate).
