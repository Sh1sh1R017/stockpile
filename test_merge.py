import re


def parse_segments(text):
    pattern = re.compile(
        r"\[(\d+)\]\s*([\d.]+)s\s*-\s*([\d.]+)s\s*"
        r"\(dur:\s*([\d.]+)s\)"
    )
    return [
        (float(match.group(2)), float(match.group(3)))
        for line in text.splitlines()
        if (match := pattern.match(line.strip()))
    ]


def merge_segments(raw_segments, threshold=0.35):
    """Merge adjacent segments whose silence gap is below threshold."""
    merged = []
    if not raw_segments:
        return merged

    cur_st, cur_en = raw_segments[0]
    for st, en in raw_segments[1:]:
        gap = st - cur_en
        if gap < threshold:
            cur_en = en
        else:
            merged.append((cur_st, cur_en))
            cur_st, cur_en = st, en
    merged.append((cur_st, cur_en))
    return merged


def test_merge_segments_merges_short_gaps():
    raw_segments = [(0.0, 0.50), (0.70, 1.20), (1.80, 2.20)]
    assert merge_segments(raw_segments, 0.35) == [(0.0, 1.20), (1.80, 2.20)]


def test_merge_segments_keeps_long_gaps():
    raw_segments = [(0.0, 0.50), (0.90, 1.20)]
    assert merge_segments(raw_segments, 0.35) == raw_segments


def test_parse_segments_is_self_contained():
    fixture = """
    [1] 0.00s - 0.50s (dur: 0.50s)
    [2] 0.70s - 1.20s (dur: 0.50s)
    """
    assert parse_segments(fixture) == [(0.0, 0.5), (0.7, 1.2)]
