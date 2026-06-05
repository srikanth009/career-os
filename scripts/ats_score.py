#!/usr/bin/env python3
"""
ats_score.py — deterministic ATS-style match scorer for a tailored resume vs a JD.

Most applicant-tracking systems rank a resume by how well its text overlaps the
job description's vocabulary — especially nouns and skill phrases. This script
approximates that mechanically (no LLM, no network) so the number is reproducible
and defensible, in keeping with career-os's no-invention ethos.

What it computes:
  1. Keyword coverage  — of the JD's salient terms (uni- + bi-grams, stopword- and
                         length-filtered, frequency-ranked), how many appear in the
                         resume (light stemming so plurals/tenses match).
  2. Cosine similarity — bag-of-words cosine between resume and JD term-frequency
                         vectors (overall textual overlap).
  3. Missing keywords  — top JD terms absent from the resume. These are SUGGESTIONS
                         for review, NOT a license to invent: only add a keyword the
                         candidate can truthfully support.

Overall score = 0.70 * keyword_coverage + 0.30 * cosine_similarity, as a percent.

Usage:
  python3 ats_score.py --resume tailored-resume.md --jd jd.txt
  python3 ats_score.py --resume tailored-resume.md --jd jd.txt --json
  python3 ats_score.py --resume tailored-resume.md --jd jd.txt --out ats-score.md
  python3 ats_score.py --resume r.md --jd jd.txt --top 30   # show more keywords

Exit codes: 0 ok, 2 bad input.
"""

import argparse
import json
import math
import re
import sys
from collections import Counter

# ---------------------------------------------------------------------------
# Tokenisation
# ---------------------------------------------------------------------------
# Keep tech-ish tokens intact: c++, c#, node.js, ci/cd handled via "/" split.
TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+#.]*")

STOPWORDS = set("""
a an and are as at be been being but by for from has have had he her his i in
into is it its of on or our that the their them they this to was were will with
you your we us about above after again against all am any because before below
between both during each few further here how if more most no nor not now off
once only other out over own same so some such than then there these those
through too under until up very what when where which while who whom why
will would can could should may might must shall do does did doing done
also per via etc within across using used use able etc
role roles work working experience experiences year years team teams
ability strong excellent good great proven track record including include
includes plus etc job position candidate candidates company companies
responsibilities responsibility requirement requirements qualification
qualifications preferred required nice must haves have desired
""".split())

# Markdown / formatting noise to strip before tokenising the resume.
MD_NOISE_RE = re.compile(r"[*_`#>\-|]+")


def normalize_text(text):
    text = text.replace("/", " ")  # ci/cd -> ci cd
    text = MD_NOISE_RE.sub(" ", text)
    return text


def tokenize(text):
    return [t.lower() for t in TOKEN_RE.findall(normalize_text(text))]


def stem(tok):
    """Very light suffix stripping so plurals/tenses match. Not linguistic."""
    for suf in ("ing", "ies", "ed", "es", "s"):
        if tok.endswith(suf) and len(tok) - len(suf) >= 3:
            if suf == "ies":
                return tok[:-3] + "y"
            return tok[: -len(suf)]
    return tok


def content_tokens(tokens):
    """Drop stopwords and 1-char tokens; keep order."""
    return [t for t in tokens if t not in STOPWORDS and len(t) > 1]


# ---------------------------------------------------------------------------
# Keyword extraction from the JD
# ---------------------------------------------------------------------------
def _salient(tok):
    """A unigram worth scoring as an ATS keyword: 3+ chars, not all digits."""
    return len(tok) >= 3 and not tok.isdigit()


def extract_keywords(jd_tokens, top):
    """Return [(keyword, weight)] — salient uni- and bi-grams, freq-ranked."""
    content = content_tokens(jd_tokens)

    unigrams = Counter(t for t in content if _salient(t))

    bigrams = Counter()
    for a, b in zip(content, content[1:]):
        if _salient(a) and _salient(b):
            bigrams[f"{a} {b}"] += 1

    # Bigrams get a frequency bonus (a matched phrase is stronger ATS signal),
    # but require freq >= 2 to avoid incidental word pairs.
    scored = {}
    for kw, c in unigrams.items():
        scored[kw] = c
    for kw, c in bigrams.items():
        if c >= 2:
            scored[kw] = c * 2.5

    ranked = sorted(scored.items(), key=lambda kv: (-kv[1], kv[0]))
    return ranked[:top]


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------
def build_stem_index(tokens):
    """Set of stemmed tokens present, for membership tests."""
    return {stem(t) for t in tokens}


def keyword_present(keyword, resume_stems, resume_text_stemmed):
    """A keyword matches if every word's stem is present.
    For bigrams, also require the stemmed phrase to appear contiguously."""
    parts = keyword.split()
    if len(parts) == 1:
        return stem(parts[0]) in resume_stems
    phrase = " ".join(stem(p) for p in parts)
    return phrase in resume_text_stemmed


def cosine_similarity(tokens_a, tokens_b):
    ca, cb = Counter(tokens_a), Counter(tokens_b)
    common = set(ca) & set(cb)
    dot = sum(ca[t] * cb[t] for t in common)
    na = math.sqrt(sum(v * v for v in ca.values()))
    nb = math.sqrt(sum(v * v for v in cb.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
def score(resume_text, jd_text, top=25):
    resume_tokens = tokenize(resume_text)
    jd_tokens = tokenize(jd_text)

    resume_content = content_tokens(resume_tokens)
    jd_content = content_tokens(jd_tokens)

    resume_stems = build_stem_index(resume_tokens)
    resume_text_stemmed = " ".join(stem(t) for t in resume_tokens)

    keywords = extract_keywords(jd_tokens, top=max(top, 25))

    matched, missing = [], []
    for kw, w in keywords:
        if keyword_present(kw, resume_stems, resume_text_stemmed):
            matched.append((kw, w))
        else:
            missing.append((kw, w))

    total_w = sum(w for _, w in keywords) or 1
    matched_w = sum(w for _, w in matched)
    coverage = matched_w / total_w  # weight-aware coverage

    cosine = cosine_similarity(resume_content, jd_content)

    overall = 0.70 * coverage + 0.30 * cosine

    return {
        "overall_score_pct": round(overall * 100, 1),
        "keyword_coverage_pct": round(coverage * 100, 1),
        "cosine_similarity_pct": round(cosine * 100, 1),
        "keywords_total": len(keywords),
        "keywords_matched": len(matched),
        "matched": [kw for kw, _ in matched],
        "missing": [kw for kw, _ in missing],
        "weights": {"keyword_coverage": 0.70, "cosine_similarity": 0.30},
    }


def band(pct):
    if pct >= 75:
        return "STRONG"
    if pct >= 60:
        return "SOLID"
    if pct >= 45:
        return "BORDERLINE"
    return "WEAK"


def render_markdown(s, resume_path, jd_path):
    lines = []
    lines.append("# ATS Match Score")
    lines.append("")
    lines.append(f"- **Resume**: `{resume_path}`")
    lines.append(f"- **JD**: `{jd_path}`")
    lines.append("")
    lines.append(f"## Overall: {s['overall_score_pct']}%  ({band(s['overall_score_pct'])})")
    lines.append("")
    lines.append("| Component | Score | Weight |")
    lines.append("|---|---|---|")
    lines.append(f"| Keyword coverage | {s['keyword_coverage_pct']}% "
                 f"({s['keywords_matched']}/{s['keywords_total']} terms) | 0.70 |")
    lines.append(f"| Cosine similarity | {s['cosine_similarity_pct']}% | 0.30 |")
    lines.append("")
    lines.append("## Matched JD keywords")
    lines.append("")
    lines.append(", ".join(s["matched"]) if s["matched"] else "_none_")
    lines.append("")
    lines.append("## Missing JD keywords (review — do NOT invent)")
    lines.append("")
    lines.append(", ".join(s["missing"]) if s["missing"] else "_none — full coverage_")
    lines.append("")
    lines.append("> Missing keywords are candidates for inclusion **only if the "
                 "applicant can truthfully support them**. If a missing term reflects "
                 "real experience not yet surfaced, capture it in memory and re-tailor. "
                 "If it reflects a genuine gap, leave it out and prep an interview answer.")
    lines.append("")
    return "\n".join(lines)


def read_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError as e:
        print(f"ERROR: cannot read {path}: {e}", file=sys.stderr)
        sys.exit(2)


def main():
    ap = argparse.ArgumentParser(description="Deterministic ATS match scorer")
    ap.add_argument("--resume", required=True, help="path to tailored resume (.md or .txt)")
    ap.add_argument("--jd", required=True, help="path to jd.txt")
    ap.add_argument("--top", type=int, default=25, help="number of JD keywords to evaluate")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of markdown")
    ap.add_argument("--out", help="also write the report to this file")
    args = ap.parse_args()

    resume_text = read_file(args.resume)
    jd_text = read_file(args.jd)

    if len(jd_text.split()) < 30:
        print("ERROR: JD text looks too short (<30 words) to score reliably.", file=sys.stderr)
        sys.exit(2)

    s = score(resume_text, jd_text, top=args.top)

    if args.json:
        payload = json.dumps(s, ensure_ascii=False, indent=2)
        out_text = payload
    else:
        out_text = render_markdown(s, args.resume, args.jd)

    sys.stdout.write(out_text + "\n")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out_text + "\n")
        print(f"\n[written to {args.out}]", file=sys.stderr)


if __name__ == "__main__":
    main()
