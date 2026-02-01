from __future__ import annotations

from pathlib import Path

import typer

from rag_sanitizer.sanitizer import parse_chunk, sanitize_chunk

app = typer.Typer(no_args_is_help=True)

IN_OPT = typer.Option(..., "--in", "-i", help="Input JSONL file")
OUT_OPT = typer.Option(..., "--out", "-o", help="Output JSONL file")
ALLOW_MISSING_OPT = typer.Option(
    False,
    "--allow-missing-citations",
    help="Do not fail citation checks when citations are missing",
)


@app.command()
def run(
    input_path: Path = IN_OPT,
    output_path: Path = OUT_OPT,
    allow_missing_citations: bool = ALLOW_MISSING_OPT,
) -> None:
    if not input_path.exists():
        raise typer.BadParameter(f"Input not found: {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with (
        input_path.open("r", encoding="utf-8") as infile,
        output_path.open("w", encoding="utf-8") as outfile,
    ):
        for line in infile:
            line = line.strip()
            if not line:
                continue
            chunk = parse_chunk(line)
            sanitized = sanitize_chunk(chunk, require_citations=not allow_missing_citations)
            outfile.write(sanitized.to_json())
            outfile.write("\n")

    typer.echo(f"Wrote sanitized output to {output_path}")
