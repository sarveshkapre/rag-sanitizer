# CHANGELOG

## [Unreleased]
- Scaffolded repository and MVP sanitizer CLI.
- Add configurable rules via `--rules` and `--dump-default-rules`.
- Support stdin/stdout (`--in -`, `--out -`) and CI gating via `--max-risk`.
- Add `--fail-on-flag` for flag-based CI gating.
- Include `source` and `redactions` metadata in output JSONL for transparency/debuggability.
- Add optional Markdown-aware sanitization via `--markdown` (ignore matches inside fenced code blocks).
