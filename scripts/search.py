#!/usr/bin/env python3
"""Search the word-timestamped transcripts in work/transcripts/*.json.

  scripts/search.py "remarkable"            # regex, case-insensitive
  scripts/search.py "\\bsurviv\\w*" -c 6     # with 6 words of context each side
  scripts/search.py --short 3.5             # every sentence lasting <= 3.5 s
  scripts/search.py --short 3 "success"     # short sentences matching a regex

Times are seconds in the source file: sources/<id>/<id>.webm
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRANSCRIPTS = ROOT / "work" / "transcripts"


# Whisper hallucinates these over music-only stretches.
HALLUCINATIONS = {"i'm sorry.", "thank you.", "thanks for watching!"}


def is_hallucination(seg):
    # > 2.4 is Whisper's own threshold for repetitive (looping) output.
    return seg.get("compression_ratio", 0) > 2.4 or seg["text"].strip().lower() in HALLUCINATIONS


def load_words(path):
    data = json.loads(path.read_text())
    words = []
    for seg in data.get("segments", []):
        if is_hallucination(seg):
            continue
        for w in seg.get("words", []):
            words.append((w["word"], float(w["start"]), float(w["end"])))
    return words


def build_text(words):
    """Join words into one string, recording each word's char span."""
    text, spans = "", []
    for w, _, _ in words:
        start = len(text)
        text += w
        spans.append((start, len(text)))
    return text, spans


def word_range(spans, a, b):
    """Indices of first and last word overlapping char range [a, b)."""
    first = next(i for i, (s, e) in enumerate(spans) if e > a)
    last = max(i for i, (s, e) in enumerate(spans) if s < b)
    return first, last


def fmt(t):
    return f"{int(t // 60):02d}:{t % 60:05.2f}"


def sentences(words):
    """Split into sentences on terminal punctuation."""
    cur = []
    for i, (w, _, _) in enumerate(words):
        cur.append(i)
        if re.search(r"[.!?]\W*$", w.strip()):
            yield cur
            cur = []
    if cur:
        yield cur


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pattern", nargs="?", help="regex (case-insensitive)")
    ap.add_argument("-c", "--context", type=int, default=4, help="words of context (search mode)")
    ap.add_argument("--short", type=float, help="list sentences no longer than this many seconds")
    ap.add_argument("--join", type=int, default=1,
                    help="with --short, also list runs of up to N consecutive sentences")
    ap.add_argument("--ids",help="comma-separated source ids to restrict to")
    args = ap.parse_args()
    if not args.pattern and args.short is None:
        ap.error("give a pattern, --short, or both")

    rx = re.compile(args.pattern, re.I) if args.pattern else None
    files = sorted(TRANSCRIPTS.glob("*.json"))
    if args.ids:
        keep = set(args.ids.split(","))
        files = [f for f in files if f.stem in keep]
    if not files:
        sys.exit(f"no transcripts in {TRANSCRIPTS}")

    hits = 0
    for path in files:
        words = load_words(path)
        if not words:
            continue
        sid = path.stem

        if args.short is not None:
            sents = list(sentences(words))
            for a in range(len(sents)):
                # Single sentences, plus runs of up to --join consecutive ones.
                for k in range(1, args.join + 1):
                    if a + k > len(sents):
                        break
                    idx = [i for sent in sents[a:a + k] for i in sent]
                    s, e = words[idx[0]][1], words[idx[-1]][2]
                    if e - s > args.short:
                        break
                    line = "".join(words[i][0] for i in idx).strip()
                    if rx is None or rx.search(line):
                        tag = f"+{k}" if k > 1 else "  "
                        print(f"{sid}  {fmt(s)}-{fmt(e)}  ({e - s:4.1f}s) {tag}  {line}")
                        hits += 1
            continue

        text, spans = build_text(words)
        for m in rx.finditer(text):
            i, j = word_range(spans, m.start(), m.end())
            lo, hi = max(0, i - args.context), min(len(words), j + args.context + 1)
            before = "".join(w for w, _, _ in words[lo:i]).strip()
            match = "".join(w for w, _, _ in words[i:j + 1]).strip()
            after = "".join(w for w, _, _ in words[j + 1:hi]).strip()
            s, e = words[i][1], words[j][2]
            print(f"{sid}  {fmt(s)}-{fmt(e)}  …{before} [{match}] {after}…")
            hits += 1

    print(f"\n{hits} hit(s) in {len(files)} transcript(s)", file=sys.stderr)


if __name__ == "__main__":
    main()
