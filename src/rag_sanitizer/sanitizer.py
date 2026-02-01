from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from re import Pattern
from typing import Any

DEFAULT_RULES: dict[str, Any] = {
    "instruction_patterns": [
        r"ignore (all|previous) (instructions|messages)",
        r"system prompt",
        r"developer message",
        r"you are (an?|the)",
        r"act as",
        r"call (the )?tool",
        r"function call",
    ],
    "secret_patterns": [
        r"api key",
        r"password",
        r"secret",
        r"token",
    ],
    "weights": {
        "instruction_like": 0.5,
        "tool_instruction": 0.2,
        "secret_like": 0.2,
        "missing_citation": 0.2,
    },
}


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    text: str
    source: str | None
    citations: list[str]


@dataclass(frozen=True)
class SanitizedChunk:
    chunk_id: str
    sanitized_text: str
    risk_score: float
    flags: list[str]
    source: str | None
    citations: list[str]
    citation_ok: bool
    redactions: list[dict[str, Any]]

    def to_json(self) -> str:
        payload = {
            "id": self.chunk_id,
            "sanitized_text": self.sanitized_text,
            "risk_score": self.risk_score,
            "flags": self.flags,
            "source": self.source,
            "citations": self.citations,
            "citation_ok": self.citation_ok,
            "redactions": self.redactions,
        }
        return json.dumps(payload, ensure_ascii=True)


@dataclass(frozen=True)
class RulePack:
    instruction_patterns: list[Pattern[str]]
    instruction_pattern_strings: list[str]
    secret_patterns: list[Pattern[str]]
    secret_pattern_strings: list[str]
    weights: dict[str, float]


def default_rule_pack() -> RulePack:
    return rule_pack_from_dict(DEFAULT_RULES)


def dump_default_rules_json() -> str:
    return json.dumps(DEFAULT_RULES, indent=2, sort_keys=True)


def load_rule_pack(path: Path) -> RulePack:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("rules must be a JSON object")
    return rule_pack_from_dict(payload)


def rule_pack_from_dict(payload: dict[str, Any]) -> RulePack:
    instruction_patterns_raw = payload.get(
        "instruction_patterns", DEFAULT_RULES["instruction_patterns"]
    )
    secret_patterns_raw = payload.get("secret_patterns", DEFAULT_RULES["secret_patterns"])
    weights_raw = payload.get("weights", DEFAULT_RULES["weights"])

    if not isinstance(instruction_patterns_raw, list) or not all(
        isinstance(item, str) for item in instruction_patterns_raw
    ):
        raise ValueError("instruction_patterns must be a list of strings")
    if not isinstance(secret_patterns_raw, list) or not all(
        isinstance(item, str) for item in secret_patterns_raw
    ):
        raise ValueError("secret_patterns must be a list of strings")
    if not isinstance(weights_raw, dict) or not all(
        isinstance(key, str) and isinstance(value, (int, float))
        for key, value in weights_raw.items()
    ):
        raise ValueError("weights must be an object mapping flag -> number")

    instruction_pattern_strings = list(instruction_patterns_raw)
    secret_pattern_strings = list(secret_patterns_raw)
    instruction_patterns = [_compile_pattern(pattern) for pattern in instruction_pattern_strings]
    secret_patterns = [_compile_pattern(pattern) for pattern in secret_pattern_strings]
    weights = {key: float(value) for key, value in weights_raw.items()}

    return RulePack(
        instruction_patterns=instruction_patterns,
        instruction_pattern_strings=instruction_pattern_strings,
        secret_patterns=secret_patterns,
        secret_pattern_strings=secret_pattern_strings,
        weights=weights,
    )


def _compile_pattern(pattern: str) -> Pattern[str]:
    return re.compile(pattern, re.IGNORECASE)


def parse_chunk(line: str) -> Chunk:
    payload = json.loads(line)
    chunk_id = str(payload.get("id", ""))
    text = str(payload.get("text", ""))
    source = payload.get("source")
    citations = payload.get("citations") or []
    if not isinstance(citations, list):
        citations = []
    normalized_citations = [str(item) for item in citations if item is not None]
    return Chunk(chunk_id=chunk_id, text=text, source=source, citations=normalized_citations)


def sanitize_chunk(
    chunk: Chunk,
    *,
    require_citations: bool = True,
    rule_pack: RulePack | None = None,
    markdown_aware: bool = False,
) -> SanitizedChunk:
    rules = rule_pack or default_rule_pack()
    flags: list[str] = []
    lines = chunk.text.splitlines()
    kept_lines: list[str] = []
    redactions: list[dict[str, Any]] = []

    instruction_like = False
    tool_like = False

    in_fenced_code_block = False
    fence_char: str | None = None
    fence_len: int | None = None

    for line_number, line in enumerate(lines, start=1):
        if markdown_aware:
            fence_match = re.match(r"^\s*([`~]{3,})", line)
            if fence_match:
                fence = fence_match.group(1)
                if not in_fenced_code_block:
                    in_fenced_code_block = True
                    fence_char = fence[0]
                    fence_len = len(fence)
                else:
                    if fence_char == fence[0] and fence_len is not None and len(fence) >= fence_len:
                        in_fenced_code_block = False
                        fence_char = None
                        fence_len = None
                kept_lines.append(line)
                continue

            if in_fenced_code_block:
                kept_lines.append(line)
                continue

        matched_patterns = [
            pattern_str
            for pattern, pattern_str in zip(
                rules.instruction_patterns, rules.instruction_pattern_strings, strict=True
            )
            if pattern.search(line)
        ]
        if matched_patterns:
            instruction_like = True
            if "tool" in line.lower() or "function" in line.lower():
                tool_like = True
            redactions.append(
                {
                    "line_number": line_number,
                    "type": "instruction_like",
                    "matched_patterns": matched_patterns,
                }
            )
            continue
        kept_lines.append(line)

    if instruction_like:
        flags.append("instruction_like")
    if tool_like:
        flags.append("tool_instruction")

    secret_like = any(pattern.search(chunk.text) for pattern in rules.secret_patterns)
    if secret_like:
        flags.append("secret_like")

    citations_present = len(chunk.citations) > 0
    citation_ok = citations_present or not require_citations
    if not citations_present and require_citations:
        flags.append("missing_citation")

    sanitized_text = "\n".join(kept_lines).strip()
    risk_score = _risk_score(flags, rules.weights)

    return SanitizedChunk(
        chunk_id=chunk.chunk_id,
        sanitized_text=sanitized_text,
        risk_score=risk_score,
        flags=flags,
        source=chunk.source,
        citations=chunk.citations,
        citation_ok=citation_ok,
        redactions=redactions,
    )


def _risk_score(flags: Iterable[str], weights: dict[str, float]) -> float:
    score = 0.0
    for flag in flags:
        score += weights.get(flag, 0.0)
    return min(score, 1.0)
