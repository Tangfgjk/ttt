from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from html import unescape

OPTION_SEPARATOR_RE = re.compile(r"(?<!\w)([A-F])[\.\u3001\uff0e\uff0c、]\s*")
HTML_TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")
MATH_OPERATOR_SPACE_RE = re.compile(r"\s*([=+\-*/<>])\s*")


@dataclass(frozen=True)
class NormalizedQuestionText:
    normalized_stem_text: str
    normalized_answer_text: str | None
    content_hash: str
    stem_hash: str
    answer_hash: str | None


def normalize_question_text(value: str | None) -> str:
    if not value:
        return ""

    text = unescape(value)
    text = HTML_TAG_RE.sub(" ", text)
    text = unicodedata.normalize("NFKC", text)
    text = OPTION_SEPARATOR_RE.sub(r"\1. ", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = MATH_OPERATOR_SPACE_RE.sub(r"\1", text)
    text = WHITESPACE_RE.sub(" ", text)
    return text.strip()


def normalize_answer_text(value: str | None) -> str:
    text = normalize_question_text(value)
    if not text:
        return ""

    text = text.upper()
    text = re.sub(r"\s*[,;/|]\s*", "|", text)
    return text


def compute_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_question_fingerprint(
    *,
    stem_text: str | None,
    answer_text: str | None,
    subject_id: int,
    question_type_id: int | None,
) -> NormalizedQuestionText:
    normalized_stem_text = normalize_question_text(stem_text)
    normalized_answer_text = normalize_answer_text(answer_text) or None
    type_part = str(question_type_id or 0)
    content_hash = compute_sha256(
        "||".join(
            [
                normalized_stem_text,
                normalized_answer_text or "",
                str(subject_id),
                type_part,
            ]
        )
    )
    stem_hash = compute_sha256(normalized_stem_text)
    answer_hash = (
        compute_sha256(normalized_answer_text)
        if normalized_answer_text
        else None
    )
    return NormalizedQuestionText(
        normalized_stem_text=normalized_stem_text,
        normalized_answer_text=normalized_answer_text,
        content_hash=content_hash,
        stem_hash=stem_hash,
        answer_hash=answer_hash,
    )


def compute_text_similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    return SequenceMatcher(None, left, right).ratio()
