from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass

INSTRUCTION_PATTERNS = [
    re.compile(r"ignore (all|previous) (instructions|messages)", re.IGNORECASE),
    re.compile(r"system prompt", re.IGNORECASE),
    re.compile(r"developer message", re.IGNORECASE),
    re.compile(r"you are (an?|the)", re.IGNORECASE),
    re.compile(r"act as", re.IGNORECASE),
    re.compile(r"call (the )?tool", re.IGNORECASE),
    re.compile(r"function call", re.IGNORECASE),
]

SECRET_PATTERNS = [
    re.compile(r"api key", re.IGNORECASE),
    re.compile(r"password", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"token", re.IGNORECASE),
]


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
    citations: list[str]
    citation_ok: bool

    def to_json(self) -> str:
        payload = {
            "id": self.chunk_id,
            "sanitized_text": self.sanitized_text,
            "risk_score": self.risk_score,
            "flags": self.flags,
            "citations": self.citations,
            "citation_ok": self.citation_ok,
        }
        return json.dumps(payload, ensure_ascii=True)


def parse_chunk(line: str) -> Chunk:
    payload = json.loads(line)
    chunk_id = str(payload.get("id", ""))
    text = str(payload.get("text", ""))
    source = payload.get("source")
    citations = payload.get("citations") or []
    if not isinstance(citations, list):
        citations = []
    return Chunk(chunk_id=chunk_id, text=text, source=source, citations=citations)


def sanitize_chunk(chunk: Chunk, *, require_citations: bool = True) -> SanitizedChunk:
    flags: list[str] = []
    lines = chunk.text.splitlines()
    kept_lines: list[str] = []

    instruction_like = False
    tool_like = False
    for line in lines:
        if any(pattern.search(line) for pattern in INSTRUCTION_PATTERNS):
            instruction_like = True
            if "tool" in line.lower() or "function" in line.lower():
                tool_like = True
            continue
        kept_lines.append(line)

    if instruction_like:
        flags.append("instruction_like")
    if tool_like:
        flags.append("tool_instruction")

    secret_like = any(pattern.search(chunk.text) for pattern in SECRET_PATTERNS)
    if secret_like:
        flags.append("secret_like")

    citations_present = len(chunk.citations) > 0
    citation_ok = citations_present or not require_citations
    if not citations_present and require_citations:
        flags.append("missing_citation")

    sanitized_text = "\n".join(kept_lines).strip()
    risk_score = _risk_score(flags)

    return SanitizedChunk(
        chunk_id=chunk.chunk_id,
        sanitized_text=sanitized_text,
        risk_score=risk_score,
        flags=flags,
        citations=chunk.citations,
        citation_ok=citation_ok,
    )


def _risk_score(flags: Iterable[str]) -> float:
    score = 0.0
    for flag in flags:
        if flag == "instruction_like":
            score += 0.5
        elif flag == "tool_instruction":
            score += 0.2
        elif flag == "secret_like":
            score += 0.2
        elif flag == "missing_citation":
            score += 0.2
    return min(score, 1.0)
