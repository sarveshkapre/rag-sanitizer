from __future__ import annotations

import sys
from contextlib import nullcontext
from enum import Enum
from pathlib import Path

import typer

from rag_sanitizer.sanitizer import (
    dump_default_rules_json,
    load_rule_pack,
    parse_chunk,
    sanitize_chunk,
)

app = typer.Typer(no_args_is_help=True)

IN_OPT = typer.Option("-", "--in", "-i", help="Input JSONL file path, or '-' for stdin")
OUT_OPT = typer.Option("-", "--out", "-o", help="Output JSONL file path, or '-' for stdout")
ALLOW_MISSING_OPT = typer.Option(
    False,
    "--allow-missing-citations",
    help="Do not fail citation checks when citations are missing",
)

RULES_OPT = typer.Option(None, "--rules", help="JSON rules file (regex lists + weights)")
DUMP_DEFAULT_RULES_OPT = typer.Option(
    None,
    "--dump-default-rules",
    help="Write default rules JSON to a file (or '-' for stdout) and exit",
)
MAX_RISK_OPT = typer.Option(
    None,
    "--max-risk",
    min=0.0,
    max=1.0,
    help="Exit non-zero if any chunk risk_score is >= this threshold",
)
MARKDOWN_OPT = typer.Option(
    False,
    "--markdown",
    help="Enable Markdown-aware sanitization (e.g., ignore matches inside fenced code blocks)",
)
FAIL_ON_FLAG_OPT = typer.Option(
    None,
    "--fail-on-flag",
    help="Exit non-zero if any chunk contains this flag (repeatable)",
)
QUIET_OPT = typer.Option(False, "--quiet", help="Suppress summary output")


class OnError(str, Enum):
    fail = "fail"
    skip = "skip"


ON_ERROR_OPT = typer.Option(
    OnError.fail,
    "--on-error",
    case_sensitive=False,
    help="What to do with invalid JSONL lines",
)


@app.command()
def run(
    input_path: str = IN_OPT,
    output_path: str = OUT_OPT,
    allow_missing_citations: bool = ALLOW_MISSING_OPT,
    rules: Path | None = RULES_OPT,
    dump_default_rules: str | None = DUMP_DEFAULT_RULES_OPT,
    max_risk: float | None = MAX_RISK_OPT,
    markdown: bool = MARKDOWN_OPT,
    fail_on_flag: list[str] | None = FAIL_ON_FLAG_OPT,
    on_error: OnError = ON_ERROR_OPT,
    quiet: bool = QUIET_OPT,
) -> None:
    if dump_default_rules is not None:
        rules_json = dump_default_rules_json() + "\n"
        if dump_default_rules == "-":
            typer.echo(rules_json.rstrip("\n"))
            raise typer.Exit(0)
        dump_path = Path(dump_default_rules)
        dump_path.parent.mkdir(parents=True, exist_ok=True)
        dump_path.write_text(rules_json, encoding="utf-8")
        typer.echo(f"Wrote default rules to {dump_path}")
        raise typer.Exit(0)

    if not input_path:
        input_path = "-"
    if not output_path:
        output_path = "-"

    rule_pack = load_rule_pack(rules) if rules is not None else None

    if input_path != "-":
        input_file = Path(input_path)
        if not input_file.exists():
            raise typer.BadParameter(f"Input not found: {input_file}")

    if output_path != "-":
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

    processed = 0
    flagged = 0
    max_seen_risk = 0.0
    should_fail = False
    fail_on_flag_set = {flag.strip() for flag in (fail_on_flag or []) if flag.strip()}

    infile_cm = (
        nullcontext(sys.stdin)
        if input_path == "-"
        else Path(input_path).open("r", encoding="utf-8")
    )
    outfile_cm = (
        nullcontext(sys.stdout)
        if output_path == "-"
        else Path(output_path).open("w", encoding="utf-8")
    )

    with infile_cm as infile, outfile_cm as outfile:
        for line_number, raw_line in enumerate(infile, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                chunk = parse_chunk(line)
            except Exception as exc:  # noqa: BLE001 - CLI boundary
                if on_error == OnError.skip:
                    typer.echo(f"Skipping invalid JSONL line {line_number}: {exc}", err=True)
                    continue
                typer.echo(f"Invalid JSONL line {line_number}: {exc}", err=True)
                raise typer.Exit(2) from exc

            sanitized = sanitize_chunk(
                chunk,
                require_citations=not allow_missing_citations,
                rule_pack=rule_pack,
                markdown_aware=markdown,
            )
            outfile.write(sanitized.to_json())
            outfile.write("\n")

            processed += 1
            if sanitized.flags:
                flagged += 1
            if sanitized.risk_score > max_seen_risk:
                max_seen_risk = sanitized.risk_score
            if max_risk is not None and sanitized.risk_score >= max_risk:
                should_fail = True
            if fail_on_flag_set and any(flag in fail_on_flag_set for flag in sanitized.flags):
                should_fail = True

    if not quiet:
        destination = "stdout" if output_path == "-" else str(Path(output_path))
        typer.echo(
            f"Processed {processed} chunks (flagged: {flagged}, max risk: {max_seen_risk:.2f}). "
            f"Wrote output to {destination}.",
            err=True,
        )

    if should_fail:
        raise typer.Exit(2)
