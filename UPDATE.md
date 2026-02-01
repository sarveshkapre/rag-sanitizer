# Update (2026-02-01)

## Shipped
- Configurable rules: `rag-sanitize --dump-default-rules rules.json` and `rag-sanitize --rules rules.json`
- CI-friendly IO: `--in -` / `--out -`
- Risk gating for pipelines: `--max-risk 0..1` exits non-zero if any chunk meets/exceeds threshold
- Output transparency: JSONL now includes `source` and `redactions` (line-level rule hits)
- Markdown-aware mode: `--markdown` ignores matches inside fenced code blocks

## How to verify
```bash
make check
make build
```

## Notes
- Per repo policy, no PR was created/updated; changes are committed directly to `main`.
