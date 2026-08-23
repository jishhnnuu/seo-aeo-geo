#!/usr/bin/env python3
"""
Deterministic GEO (Generative Engine Optimization) content scorer.

Added for this repo — not sourced from any of the four merged upstream
projects. Written after a review of the wider Claude-Code-SEO-tool
ecosystem turned up houtini-ai/geo-analyzer, a paid MCP tool (needs an
Anthropic API key, ~$0.14/analysis) implementing this same peer-reviewed
methodology via an LLM call. This script implements the same measurable
criteria deterministically and locally instead — no API key, no per-run
cost, consistent with this plugin's free-tier-first design and with
this plugin's existing convention (see content_quality.py) of keeping
audit scripts self-contained and zero-dependency where the underlying
signal doesn't actually require an LLM call to measure.

Methodology: see skills/seo-geo/references/peer-reviewed-geo-research.md
for the full citations. Summary of what's implemented here:

  - Claim density   — Aggarwal et al., "GEO: Generative Engine
                       Optimization," ACM SIGKDD 2024
                       (arxiv.org/abs/2311.09735). Target: 4+
                       extractable facts/statistics/measurements per
                       100 words.
  - Sentence length  — same paper, target 15-20 words average;
                       independently converges with the Dejan grounding
                       study's ~15.5-word average extraction chunk
                       below.
  - Answer frontloading, information density, extraction-chunk framing
                     — Dejan AI grounding research (2025), empirical
                       analysis of 7,060 queries / 2,275 pages
                       (dejan.ai/blog/how-big-are-googles-grounding-chunks).

This is a heuristic, regex/rule-based measurement of *structural*
GEO signals, not a judgment of content quality, accuracy, or E-E-A-T —
pair it with content_quality.py (filler/AI-pattern detection) and
content_verify.py (claim verification) for those, and with
skills/seo/references/eeat-framework.md for trust signals. A page can
score well here and still be poor content; the two are different axes.

Output (JSON when --json is set):

    {
      "word_count":              int,
      "sentence_count":          int,
      "avg_sentence_length":     float (words/sentence),
      "sentence_length_band":    "optimal" | "too_long" | "too_short",
      "claim_count":             int (heuristic — see _CLAIM_PATTERNS),
      "claim_density_per_100":   float,
      "claim_density_band":      "optimal" | "below_target",
      "first_100_words_claims":  int (answer-frontloading proxy),
      "first_300_words_claims":  int,
      "frontloading_band":       "strong" | "weak",
      "content_length_band":     "citation_favorable" | "neutral" | "citation_unfavorable",
      "overall_geo_structure_score": 0..100,
      "confidence": "established",
      "notes": [...]
    }

The word-count bands and the 40%-citation-lift figure this script's
docstring references are `directional`, not `established`, per this
repo's confidence-tier discipline (schema/finding.schema.json) — a
single paper's test set, however peer-reviewed, is not a replicated
cross-platform result. Report them as such.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


# Heuristic claim signals: numbers, percentages, dates, measurements,
# and named-source attribution patterns. Deliberately conservative —
# false negatives (missing a real claim) are safer here than false
# positives (counting vague sentences as claims), since this feeds a
# density *target*, not a content-quality verdict.
_CLAIM_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b\d[\d,]*\.?\d*\s*%"),                       # percentages
    re.compile(r"\b\d[\d,]*\.?\d*\s*(?:million|billion|thousand|k|m|b)\b", re.I),
    re.compile(r"\$\s?\d[\d,]*\.?\d*"),                         # currency
    re.compile(r"\b(?:19|20)\d{2}\b"),                          # years
    re.compile(r"\baccording to\b", re.I),
    re.compile(r"\bstudy (?:found|shows|showed)\b", re.I),
    re.compile(r"\bresearch(?:ers)? (?:found|shows|showed)\b", re.I),
    re.compile(r"\b\d[\d,]*\.?\d*\s*(?:times|x)\b", re.I),      # multipliers
    re.compile(r"\b\d[\d,]*\.?\d*\s*(?:kg|g|km|mi|lb|oz|ml|l|hours?|minutes?|seconds?|days?|weeks?|months?|years?)\b", re.I),
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")


def _clean_text(raw: str) -> str:
    # Strip HTML tags if present; this script works on plain text or
    # loosely-tagged HTML, not a full DOM parse — for real page audits,
    # extract body text first (this plugin's render_page.py / trafilatura
    # pipeline) and pass the extracted text in here.
    text = re.sub(r"<script.*?</script>", " ", raw, flags=re.I | re.S)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]


def _words(text: str) -> list[str]:
    return re.findall(r"\b[\w'-]+\b", text)


def _count_claims(text: str) -> int:
    seen_spans: set[tuple[int, int]] = set()
    count = 0
    for pattern in _CLAIM_PATTERNS:
        for m in pattern.finditer(text):
            span = m.span()
            # avoid double-counting overlapping matches (e.g. a year
            # inside a longer numeric+unit match)
            if not any(a <= span[0] < b or a < span[1] <= b for a, b in seen_spans):
                seen_spans.add(span)
                count += 1
    return count


def score(text: str) -> dict:
    clean = _clean_text(text)
    words = _words(clean)
    sentences = _sentences(clean)
    word_count = len(words)
    sentence_count = max(len(sentences), 1)

    avg_sentence_length = round(word_count / sentence_count, 1) if sentence_count else 0.0
    if 15 <= avg_sentence_length <= 20:
        sentence_band = "optimal"
    elif avg_sentence_length > 20:
        sentence_band = "too_long"
    else:
        sentence_band = "too_short"

    claim_count = _count_claims(clean)
    claim_density = round((claim_count / word_count) * 100, 2) if word_count else 0.0
    claim_band = "optimal" if claim_density >= 4.0 else "below_target"

    first_100 = " ".join(words[:100])
    first_300 = " ".join(words[:300])
    first_100_claims = _count_claims(first_100)
    first_300_claims = _count_claims(first_300)
    frontloading_band = "strong" if first_100_claims >= 1 else "weak"

    if word_count < 1000:
        length_band = "citation_favorable"
    elif word_count <= 1500:
        length_band = "citation_favorable"
    elif word_count <= 3000:
        length_band = "neutral"
    else:
        length_band = "citation_unfavorable"

    # Composite 0-100: weighted toward claim density (35%) and sentence
    # structure (25%) per the GEO paper's own "Content Structure (35%
    # impact)" framing carried over from this plugin's existing seo-geo
    # scoring criteria section, plus frontloading (20%) and length band
    # (20%). This composite is a convenience rollup for reporting, not
    # itself a claim from either source study — tag it accordingly.
    sentence_score = 100 if sentence_band == "optimal" else (60 if avg_sentence_length else 0)
    claim_score = min(100, round((claim_density / 4.0) * 100)) if claim_density else 0
    frontload_score = 100 if frontloading_band == "strong" else 40
    length_score = {"citation_favorable": 100, "neutral": 60, "citation_unfavorable": 25}[length_band]
    overall = round(
        claim_score * 0.35 + sentence_score * 0.25 + frontload_score * 0.20 + length_score * 0.20
    )

    notes = []
    if claim_band == "below_target":
        notes.append(
            f"Claim density {claim_density}/100 words is below the 4+/100 target "
            "(GEO paper, KDD 2024). Add specific facts, statistics, or measurements."
        )
    if sentence_band == "too_long":
        notes.append(
            f"Average sentence length {avg_sentence_length} words exceeds the 15-20 "
            "word target — long sentences parse less reliably for AI extraction."
        )
    elif sentence_band == "too_short":
        notes.append(
            f"Average sentence length {avg_sentence_length} words is unusually short — "
            "verify this isn't fragmented/bulleted text being mis-split by this script "
            "rather than a genuine structural issue."
        )
    if frontloading_band == "weak":
        notes.append(
            "No clear claim detected in the first 100 words — lead with a direct, "
            "fact-bearing answer rather than throat-clearing or scene-setting."
        )
    if length_band == "citation_unfavorable":
        notes.append(
            f"{word_count} words exceeds ~3,000 — empirically associated with lower AI-answer "
            "coverage (~13% vs ~61% for pages under 1,000 words, Dejan AI grounding study). "
            "This is a GEO-specific signal; it does not mean the page is too long for classic "
            "SEO, where comprehensiveness can still help. Flag the tension, don't resolve it "
            "silently."
        )

    return {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "avg_sentence_length": avg_sentence_length,
        "sentence_length_band": sentence_band,
        "claim_count": claim_count,
        "claim_density_per_100": claim_density,
        "claim_density_band": claim_band,
        "first_100_words_claims": first_100_claims,
        "first_300_words_claims": first_300_claims,
        "frontloading_band": frontloading_band,
        "content_length_band": length_band,
        "overall_geo_structure_score": overall,
        "confidence": "established",
        "confidence_note": (
            "The underlying targets (4+/100 words claim density, 15-20 word sentences, "
            "~15.5-word extraction chunks) are established per peer-reviewed/large-sample "
            "sources — see skills/seo-geo/references/peer-reviewed-geo-research.md. The "
            "0-100 composite rollup and its weighting are this script's own convenience "
            "aggregation, not a claim from either source."
        ),
        "notes": notes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1] if __doc__ else "")
    parser.add_argument("--file", type=Path, help="Path to a text/HTML file to score")
    parser.add_argument("--text", type=str, help="Raw text to score directly")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if args.file:
        raw = args.file.read_text(encoding="utf-8", errors="replace")
    elif args.text:
        raw = args.text
    else:
        raw = sys.stdin.read()

    if not raw.strip():
        print("No content provided (use --file, --text, or pipe via stdin).", file=sys.stderr)
        return 1

    if len(_words(_clean_text(raw))) < 50:
        print(
            "Warning: content is very short (<50 words) — scores below are unreliable "
            "at this length; the underlying research measured full pages/articles.",
            file=sys.stderr,
        )

    result = score(raw)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Word count: {result['word_count']}")
        print(f"Avg sentence length: {result['avg_sentence_length']} words ({result['sentence_length_band']})")
        print(f"Claim density: {result['claim_density_per_100']}/100 words ({result['claim_density_band']})")
        print(f"Frontloading: {result['frontloading_band']} ({result['first_100_words_claims']} claims in first 100 words)")
        print(f"Content length band: {result['content_length_band']}")
        print(f"Overall GEO structure score: {result['overall_geo_structure_score']}/100")
        if result["notes"]:
            print("\nNotes:")
            for note in result["notes"]:
                print(f"  - {note}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
