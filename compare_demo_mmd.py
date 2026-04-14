#!/usr/bin/env python3
"""
Compare Mermaid/text outputs in demo_input_output/ for each demo N in {1,2,3}:
  - output_demoN.mmd          vs output_demoN_base.mmd
  - output_demoN_raw.mmd      vs output_demoN_base_raw.mmd
  Missing files are skipped with [skip].

Metrics (text-oriented, no third-party deps):
  - byte_sha256_equal        exact file identity
  - char_length / line_count per file
  - levenshtein              character-level edit distance
  - normalized_edit          Levenshtein / max(len(a),len(b)) in [0, 1] (lower = more similar)
  - sequence_matcher_ratio   difflib.SequenceMatcher.ratio() in [0, 1] (higher = more similar)
  - line_diff_stats          counts from difflib.ndiff line-wise (equal / replace / +/-)
  - data-bbox                left,top,right,bottom; rel vs B: horiz |A-B|/width_B, vert |A-B|/height_B

Usage:
  python3 compare_demo_mmd.py
  python3 compare_demo_mmd.py --dir /path/to/demo_input_output
"""

import argparse
import difflib
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

# HTML / snippet: data-bbox="left,top,right,bottom" (comma-separated integers)
BBOX_PATTERN = re.compile(
    r"""data-bbox\s*=\s*["'](\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)["']""",
    re.IGNORECASE,
)


@dataclass
class BboxCompare:
    """Compare extracted data-bbox quads in document order."""

    count_a: int
    count_b: int
    tuples_identical: bool
    paired: int
    extra_in_a: int
    extra_in_b: int
    total_l1: int
    max_l1_one_bbox: int
    max_abs_coord_delta: int
    # Relative error vs baseline B: left/right use width_B; top/bottom use height_B (see compare_bboxes).
    mean_rel_coord: float
    max_rel_coord: float


@dataclass
class PairMetrics:
    name: str
    path_a: Path
    path_b: Path
    bytes_equal: bool
    sha_a: str
    sha_b: str
    len_a: int
    len_b: int
    lines_a: int
    lines_b: int
    levenshtein: int
    normalized_edit: float
    seq_ratio: float
    lines_equal: int
    lines_minus: int
    lines_plus: int
    bbox: BboxCompare


def levenshtein(a: str, b: str) -> int:
    """O(len(a)*len(b)) dynamic programming; fine for ~few MB of text."""
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i]
        for j, cb in enumerate(b, start=1):
            ins = cur[j - 1] + 1
            delete = prev[j] + 1
            sub = prev[j - 1] + (ca != cb)
            cur.append(min(ins, delete, sub))
        prev = cur
    return prev[-1]


def extract_data_bboxes(text: str) -> List[Tuple[int, int, int, int]]:
    """All data-bbox quads in left-to-right / document order."""
    out: List[Tuple[int, int, int, int]] = []
    for m in BBOX_PATTERN.finditer(text):
        out.append(tuple(int(g) for g in m.groups()))
    return out


def _bbox_width_height_baseline(
    left: int, top: int, right: int, bottom: int
) -> Tuple[float, float]:
    """From baseline B quad (left,top,right,bottom): width and height, each at least 1 px."""
    w = float(max(abs(right - left), 1))
    h = float(max(abs(bottom - top), 1))
    return w, h


def compare_bboxes(
    a: List[Tuple[int, int, int, int]], b: List[Tuple[int, int, int, int]]
) -> BboxCompare:
    na, nb = len(a), len(b)
    paired = min(na, nb)
    tuples_identical = na == nb and a == b
    extra_a = max(0, na - nb)
    extra_b = max(0, nb - na)
    if paired == 0:
        return BboxCompare(
            count_a=na,
            count_b=nb,
            tuples_identical=(na == nb == 0),
            paired=0,
            extra_in_a=extra_a,
            extra_in_b=extra_b,
            total_l1=0,
            max_l1_one_bbox=0,
            max_abs_coord_delta=0,
            mean_rel_coord=0.0,
            max_rel_coord=0.0,
        )
    l1_each: List[int] = []
    max_coord = 0
    rel_each: List[float] = []
    for i in range(paired):
        ta, tb = a[i], b[i]
        # Baseline B: horizontal coords (left, right) -> denom = width; vertical (top, bottom) -> height
        width_b, height_b = _bbox_width_height_baseline(tb[0], tb[1], tb[2], tb[3])
        l1 = 0
        for j in range(4):
            va, vb = ta[j], tb[j]
            d = abs(va - vb)
            l1 += d
            if d > max_coord:
                max_coord = d
            if j in (0, 2):
                denom = width_b
            else:
                denom = height_b
            rel_each.append(d / denom)
        l1_each.append(l1)
    mean_rel = sum(rel_each) / float(len(rel_each))
    max_rel = max(rel_each)
    return BboxCompare(
        count_a=na,
        count_b=nb,
        tuples_identical=tuples_identical,
        paired=paired,
        extra_in_a=extra_a,
        extra_in_b=extra_b,
        total_l1=sum(l1_each),
        max_l1_one_bbox=max(l1_each),
        max_abs_coord_delta=max_coord,
        mean_rel_coord=mean_rel,
        max_rel_coord=max_rel,
    )


def line_diff_stats(a_lines: List[str], b_lines: List[str]) -> Tuple[int, int, int]:
    """Use ndiff: count equal lines vs lines only in A (-) vs only in B (+)."""
    equal = minus = plus = 0
    for line in difflib.ndiff(a_lines, b_lines):
        if line.startswith("  "):
            equal += 1
        elif line.startswith("- "):
            minus += 1
        elif line.startswith("+ "):
            plus += 1
        elif line.startswith("? "):
            continue
    return equal, minus, plus


def compare_pair(name: str, path_a: Path, path_b: Path) -> PairMetrics:
    raw_a = path_a.read_bytes()
    raw_b = path_b.read_bytes()
    bytes_equal = raw_a == raw_b
    sha_a = hashlib.sha256(raw_a).hexdigest()
    sha_b = hashlib.sha256(raw_b).hexdigest()

    # Decode as UTF-8 (common for .mmd); replace errors for robustness
    text_a = raw_a.decode("utf-8", errors="replace")
    text_b = raw_b.decode("utf-8", errors="replace")

    len_a, len_b = len(text_a), len(text_b)
    lines_a = text_a.splitlines()
    lines_b = text_b.splitlines()

    lev = levenshtein(text_a, text_b)
    max_len = max(len_a, len_b, 1)
    norm_ed = lev / max_len

    seq_ratio = difflib.SequenceMatcher(None, text_a, text_b).ratio()

    eq, minus, plus = line_diff_stats(lines_a, lines_b)

    bxa = extract_data_bboxes(text_a)
    bxb = extract_data_bboxes(text_b)
    bbox_cmp = compare_bboxes(bxa, bxb)

    return PairMetrics(
        name=name,
        path_a=path_a,
        path_b=path_b,
        bytes_equal=bytes_equal,
        sha_a=sha_a,
        sha_b=sha_b,
        len_a=len_a,
        len_b=len_b,
        lines_a=len(lines_a),
        lines_b=len(lines_b),
        levenshtein=lev,
        normalized_edit=norm_ed,
        seq_ratio=seq_ratio,
        lines_equal=eq,
        lines_minus=minus,
        lines_plus=plus,
        bbox=bbox_cmp,
    )


def print_report(m: PairMetrics) -> None:
    print(f"=== {m.name} ===")
    print(f"  A: {m.path_a}")
    print(f"  B: {m.path_b}")
    print(f"  byte_identical (raw bytes):     {m.bytes_equal}")
    print(f"  sha256 A: {m.sha_a[:16]}…")
    print(f"  sha256 B: {m.sha_b[:16]}…")
    print(f"  UTF-8 chars:  A={m.len_a}  B={m.len_b}  |Δ|={abs(m.len_a - m.len_b)}")
    print(f"  lines:        A={m.lines_a}  B={m.lines_b}  |Δ|={abs(m.lines_a - m.lines_b)}")
    print(f"  Levenshtein (char edits):     {m.levenshtein}")
    print(f"  normalized_edit (lev/maxlen): {m.normalized_edit:.6f}   (0 = identical)")
    print(f"  SequenceMatcher.ratio:         {m.seq_ratio:.6f}   (1 = identical)")
    print(
        "  line_ndiff:  equal_lines=%d  lines_only_in_A(-)=%d  lines_only_in_B(+)=%d"
        % (m.lines_equal, m.lines_minus, m.lines_plus)
    )
    bb = m.bbox
    print("  data-bbox (four integers per attribute, document order):")
    print("    count:  A=%d  B=%d  paired=%d  extra_A=%d  extra_B=%d" % (bb.count_a, bb.count_b, bb.paired, bb.extra_in_a, bb.extra_in_b))
    print("    all_tuples_identical:        %s" % bb.tuples_identical)
    print("    sum_L1_over_paired_bboxes:   %d   (Manhattan distance per quad, summed)" % bb.total_l1)
    print("    max_L1_single_bbox:          %d" % bb.max_l1_one_bbox)
    print("    max_abs_delta_single_coord:   %d   (max |Δ| among the four numbers)" % bb.max_abs_coord_delta)
    print(
        "    mean_rel_coord:              %.6f   (mean of |A-B|/W_B for left&right, |A-B|/H_B for top&bottom; %d values)"
        % (bb.mean_rel_coord, bb.paired * 4)
    )
    print(
        "    max_rel_coord:               %.6f   (max of those; W_B=|right-left|, H_B=|bottom-top| on B)"
        % bb.max_rel_coord
    )
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare demo .mmd output pairs.")
    parser.add_argument(
        "--dir",
        type=Path,
        default=None,
        help="Directory containing output_demo*.mmd (default: demo_input_output next to this script)",
    )
    args = parser.parse_args()
    base = args.dir
    if base is None:
        base = Path(__file__).resolve().parent / "demo_input_output"

    pairs = []
    for n in (1, 2, 3):
        pairs.append(
            (
                "output_demo%d vs output_demo%d_base" % (n, n),
                base / ("output_demo%d.mmd" % n),
                base / ("output_demo%d_base.mmd" % n),
            )
        )
        pairs.append(
            (
                "output_demo%d_raw vs output_demo%d_base_raw" % (n, n),
                base / ("output_demo%d_raw.mmd" % n),
                base / ("output_demo%d_base_raw.mmd" % n),
            )
        )

    for label, pa, pb in pairs:
        if not pa.is_file():
            print(f"[skip] missing: {pa}")
            continue
        if not pb.is_file():
            print(f"[skip] missing: {pb}")
            continue
        m = compare_pair(label, pa, pb)
        print_report(m)

    print(
        "Notes:\n"
        "  • normalized_edit: single-number rough dissimilarity (char-level).\n"
        "  • SequenceMatcher.ratio: difflib similarity on full strings (good for prose).\n"
        "  • line_ndiff: coarse line presence; small line edits count as -/+ pairs.\n"
        "  • data-bbox: quads parsed from data-bbox=\"…\"; compared in extraction order.\n"
        "    sum_L1 / max_L1 / max_abs_delta apply only to the first min(count) pairs.\n"
        "    Relative error vs B: quad is left,top,right,bottom; left/right use W_B=|right-left|;\n"
        "      top/bottom use H_B=|bottom-top|; denominators from B, min 1 px. A=first file, B=second.\n"
    )


if __name__ == "__main__":
    main()
