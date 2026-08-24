from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


PAUSE_MS = {"short": 250, "medium": 500, "long": 900}
TOKEN_RE = re.compile(
    r"\[pause:(short|medium|long)\]|\[emphasis\](.*?)\[/emphasis\]",
    re.IGNORECASE | re.DOTALL,
)
BOUNDARY_RE = re.compile(r"(?<=[.!?;:])(?:[\"'’”)]*)\s+|\n+")


@dataclass
class Phrase:
    index: int
    text: str
    source_start: int
    source_end: int
    pause_after_ms: int = 0


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\t ]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def speech_text(text: str) -> str:
    text = re.sub(r"\[pause:(?:short|medium|long)\]", " ", text, flags=re.I)
    text = re.sub(r"\[emphasis\](.*?)\[/emphasis\]", r"\1", text, flags=re.I | re.S)
    return re.sub(r"\s+", " ", text).strip()


def split_phrases(raw: str, minimum: int = 80, maximum: int = 250) -> list[Phrase]:
    normalized = normalize_text(raw)
    if not normalized:
        return []
    segments: list[tuple[str, int, int, int]] = []
    cursor = 0
    pending_pause = 0
    for token in TOKEN_RE.finditer(normalized):
        before = normalized[cursor:token.start()]
        if before.strip():
            start = cursor + len(before) - len(before.lstrip())
            end = token.start() - (len(before) - len(before.rstrip()))
            segments.append((before.strip(), start, end, pending_pause))
            pending_pause = 0
        if token.group(1):
            pause = PAUSE_MS[token.group(1).lower()]
            if segments:
                last = segments[-1]
                segments[-1] = (*last[:3], max(last[3], pause))
            else:
                pending_pause = pause
        else:
            emphasized = token.group(2).strip()
            if emphasized:
                content_start = token.start() + len("[emphasis]")
                content_start += len(token.group(2)) - len(token.group(2).lstrip())
                segments.append((emphasized, content_start, content_start + len(emphasized), pending_pause))
                pending_pause = 0
        cursor = token.end()
    tail = normalized[cursor:]
    if tail.strip():
        start = cursor + len(tail) - len(tail.lstrip())
        segments.append((tail.strip(), start, len(normalized), pending_pause))

    pieces: list[tuple[str, int, int, int]] = []
    for value, start, end, pause in segments:
        part_start = start
        for match in BOUNDARY_RE.finditer(value):
            part_end = start + match.start()
            piece = normalized[part_start:part_end].strip()
            if piece:
                actual_start = normalized.find(piece, part_start, part_end + 1)
                pieces.append((piece, actual_start, actual_start + len(piece), 0))
            part_start = start + match.end()
        piece = normalized[part_start:end].strip()
        if piece:
            actual_start = normalized.find(piece, part_start, end + 1)
            pieces.append((piece, actual_start, actual_start + len(piece), pause))
        elif pieces and pause:
            last = pieces[-1]
            pieces[-1] = (*last[:3], pause)

    merged: list[Phrase] = []
    buffer: list[tuple[str, int, int, int]] = []
    size = 0
    for piece in pieces:
        projected = size + len(piece[0]) + (1 if buffer else 0)
        hard_boundary = bool(buffer and buffer[-1][3])
        if buffer and (projected > maximum or (size >= minimum and hard_boundary)):
            _flush(buffer, merged)
            buffer, size = [], 0
        buffer.append(piece)
        size += len(piece[0]) + (1 if size else 0)
        if piece[3]:
            _flush(buffer, merged)
            buffer, size = [], 0
    if buffer:
        _flush(buffer, merged)
    return merged


def _flush(buffer: list[tuple[str, int, int, int]], result: list[Phrase]) -> None:
    result.append(
        Phrase(
            index=len(result),
            text=" ".join(item[0] for item in buffer),
            source_start=buffer[0][1],
            source_end=buffer[-1][2],
            pause_after_ms=buffer[-1][3],
        )
    )
