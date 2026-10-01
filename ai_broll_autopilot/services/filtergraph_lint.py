"""Static validation for FFmpeg filtergraph labels."""

from __future__ import annotations

import re
from collections import Counter
from typing import Iterable, List, Set, Tuple


_LEADING_LABELS = re.compile(r"^(?:\s*\[([^\]]+)\])+")
_TRAILING_LABELS = re.compile(r"(?:\s*\[([^\]]+)\])+\s*$")


def _extract_leading_labels(segment: str) -> List[str]:
    labels: List[str] = []
    cursor = 0
    while cursor < len(segment) and segment[cursor].isspace():
        cursor += 1
    while cursor < len(segment) and segment[cursor] == "[":
        end = segment.find("]", cursor + 1)
        if end < 0:
            break
        labels.append(segment[cursor + 1 : end])
        cursor = end + 1
        while cursor < len(segment) and segment[cursor].isspace():
            cursor += 1
    return labels


def _extract_trailing_labels(segment: str) -> List[str]:
    labels: List[str] = []
    cursor = len(segment)
    while cursor > 0:
        while cursor > 0 and segment[cursor - 1].isspace():
            cursor -= 1
        if cursor <= 0 or segment[cursor - 1] != "]":
            break
        start = segment.rfind("[", 0, cursor)
        if start < 0:
            break
        labels.append(segment[start + 1 : cursor - 1])
        cursor = start
    labels.reverse()
    return labels


def validate_filtergraph_labels(
    filtergraph: str,
    final_labels: Iterable[str] = (),
) -> List[str]:
    """Return static label errors for duplicate producers and dangling outputs."""
    producers: List[Tuple[str, int]] = []
    consumers: Counter[str] = Counter()

    for index, raw_segment in enumerate(filtergraph.split(";")):
        segment = raw_segment.strip()
        if not segment:
            continue
        inputs = _extract_leading_labels(segment)
        outputs = _extract_trailing_labels(segment)

        for label in inputs:
            consumers[label] += 1
        for label in outputs:
            producers.append((label, index))

    errors: List[str] = []
    producer_counts = Counter(label for label, _ in producers)
    for label, count in producer_counts.items():
        if count > 1:
            errors.append(f"label '{label}' has {count} producers")

    finals: Set[str] = set(final_labels)
    for label, segment_index in producers:
        if label in finals:
            continue
        if consumers.get(label, 0) == 0:
            errors.append(
                f"label '{label}' produced by filter segment {segment_index} has no consumer"
            )

    return errors


def assert_filtergraph_labels(filtergraph: str, final_labels: Iterable[str] = ()) -> None:
    errors = validate_filtergraph_labels(filtergraph, final_labels)
    assert not errors, "Filtergraph label violations:\n" + "\n".join(errors)
