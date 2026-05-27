from __future__ import annotations

from html import escape
from typing import Iterable

from app.models.question import Question
from app.repositories.question_repository import QuestionRepository


def compose_dataset2_stem(payload: dict) -> tuple[str | None, str | None]:
    base_text = _first_text(payload, "question", "stem", "content")
    subquestion_texts = _extract_subquestion_texts(payload.get("subQues"))
    if not base_text and not subquestion_texts:
        return None, None

    stem_text_parts = [part for part in [base_text, *subquestion_texts] if part]
    stem_text = "\n".join(stem_text_parts) if stem_text_parts else None

    base_html = _first_text(payload, "questionHtml", "stemHtml")
    if not base_html and base_text and _looks_like_html(base_text):
        base_html = base_text
    subquestion_html_parts = [_to_html_fragment(part) for part in subquestion_texts if part]
    stem_html = base_html
    if subquestion_html_parts:
        suffix = "<br />".join(subquestion_html_parts)
        stem_html = f"{base_html}<br />{suffix}" if base_html else suffix

    return stem_text, stem_html


def hydrate_question_contents(db, questions: Iterable[Question]) -> None:
    question_list = [question for question in questions if question.content is not None]
    if not question_list:
        return

    payload_map = QuestionRepository(db).list_source_payloads_by_question_ids(
        [question.id for question in question_list]
    )
    for question in question_list:
        payloads = payload_map.get(question.id) or []
        stem_text, stem_html = _resolve_best_dataset2_stem(payloads)
        if not stem_text:
            continue
        question.content.stem_text = stem_text
        if stem_html:
            question.content.stem_html = stem_html


def _resolve_best_dataset2_stem(payloads: list[dict]) -> tuple[str | None, str | None]:
    fallback: tuple[str | None, str | None] = (None, None)
    for payload in payloads:
        stem_text, stem_html = compose_dataset2_stem(payload)
        if not stem_text:
            continue
        if fallback == (None, None):
            fallback = (stem_text, stem_html)
        if payload.get("subQues"):
            return stem_text, stem_html
    return fallback


def _extract_subquestion_texts(value) -> list[str]:
    if not isinstance(value, list):
        return []

    def _sort_key(item) -> tuple[int, int]:
        if not isinstance(item, dict):
            return (1_000_000, 1_000_000)
        sort_index = item.get("sortIndex")
        opt_count = item.get("optCount")
        try:
            sort_index_value = int(sort_index)
        except (TypeError, ValueError):
            sort_index_value = 1_000_000
        try:
            opt_count_value = int(opt_count)
        except (TypeError, ValueError):
            opt_count_value = 1_000_000
        return (sort_index_value, opt_count_value)

    texts: list[str] = []
    for item in sorted(value, key=_sort_key):
        if not isinstance(item, dict):
            continue
        text = _first_text(item, "question", "stem", "content")
        if text:
            texts.append(text)
    return texts


def _first_text(payload: dict, *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def _looks_like_html(value: str) -> bool:
    return "<" in value and ">" in value


def _to_html_fragment(value: str) -> str:
    if _looks_like_html(value):
        return value
    return escape(value).replace("\n", "<br />")
