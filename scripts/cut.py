#!/usr/bin/env python3
"""Cut every row of candidates.tsv into work/candidates/<nn>_<slug>.wav.

Each clip gets a little padding (Whisper word edges run tight), then:
  low-cut 70 Hz -> gentle voice compression (3:1) -> static gain to -16 LUFS
  -> peak limiter at -2 dBFS -> 30 ms fades. Mono 44.1 kHz.
Gain is measured per clip (pass 1) and applied as a fixed volume (pass 2), so
every clip lands at the same integrated loudness without pumping.

  scripts/cut.py           # cut all (skips clips already cut)
  scripts/cut.py --force   # re-cut everything

Per-clip start/end nudges saved by the review page (work/review.json) are applied.
"""
import argparse
import csv
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANDIDATES = ROOT / "candidates.tsv"
OUT = ROOT / "work" / "candidates"
REVIEW = ROOT / "work" / "review.json"

PRE, POST, FADE = 0.12, 0.30, 0.03
TARGET_LUFS = -16.0
# threshold 0.1 = -20 dBFS; evens out loud vs quiet words within and across clips.
SHAPE = "highpass=f=70,acompressor=threshold=0.1:ratio=3:attack=5:release=120:makeup=1"
LIMIT = "alimiter=limit=0.794:attack=2:release=50:level=0"  # 0.794 = -2 dBFS


def integrated_lufs(stderr):
    summary = stderr[stderr.rindex("Summary:"):]
    return float(re.search(r"I:\s+(-?[\d.]+) LUFS", summary).group(1))


def ts(s):
    m, sec = s.split(":")
    return int(m) * 60 + float(sec)


def slug(text, n=40):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:n].rstrip("-")


def load_candidates():
    with CANDIDATES.open(newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    for i, r in enumerate(rows, 1):
        r["n"] = f"{i:02d}"
        r["file"] = f"{r['n']}_{slug(r['text'])}.wav"
        r["note"] = r.get("note") or ""
    return rows


def load_review():
    return json.loads(REVIEW.read_text()) if REVIEW.exists() else {}


def cut(row, adj_start=0.0, adj_end=0.0, out_dir=None):
    """Cut one clip into out_dir (default work/candidates); returns its output path."""
    src = ROOT / "sources" / row["source"] / f"{row['source']}.webm"
    s = max(0.0, ts(row["start"]) - PRE + adj_start)
    d = ts(row["end"]) + POST + adj_end - s
    if d <= 2 * FADE:
        raise ValueError(f"clip {row['n']} too short after nudges ({d:.2f}s)")
    fades = f"afade=t=in:d={FADE},afade=t=out:st={d - FADE:.3f}:d={FADE}"
    head = ["ffmpeg", "-hide_banner", "-nostdin", "-ss", f"{s:.3f}", "-t", f"{d:.3f}", "-i", str(src), "-ac", "1"]

    # Pass 1: loudness after shaping.
    r = subprocess.run(head + ["-af", f"{SHAPE},ebur128", "-f", "null", "-"],
                       capture_output=True, text=True, check=True)
    gain = TARGET_LUFS - integrated_lufs(r.stderr)

    # Pass 2: shape, fixed gain, limit peaks, fade edges.
    chain = f"{SHAPE},volume={gain:.2f}dB,{LIMIT},{fades}"
    out = Path(out_dir or OUT) / row["file"]
    subprocess.run(head + ["-af", chain, "-ar", "44100", "-y", str(out)], capture_output=True, check=True)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true", help="re-cut clips that already exist")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    review = load_review()
    for row in load_candidates():
        out = OUT / row["file"]
        if out.exists() and not args.force:
            continue
        rv = review.get(row["n"], {})
        cut(row, rv.get("adj_start", 0.0), rv.get("adj_end", 0.0))
        print(f"{row['n']}  {row['event']:17} {row['text']}")


if __name__ == "__main__":
    main()
