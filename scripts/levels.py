#!/usr/bin/env python3
"""Report loudness (integrated LUFS, short-term max, true peak) of kept/maybe clips.

  scripts/levels.py          # kept + maybe clips in work/candidates
  scripts/levels.py --all    # every candidate
"""
import argparse
import json
import re
import statistics
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cut  # noqa: E402


def measure(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-i", str(path),
                        "-af", "ebur128=peak=true:framelog=verbose", "-f", "null", "-"],
                       capture_output=True, text=True, check=True)
    err = r.stderr
    summary = err[err.rindex("Summary:"):]
    i = float(re.search(r"I:\s+(-?[\d.]+|-inf) LUFS", summary).group(1))
    tp = float(re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", summary).group(1))
    st = [float(x) for x in re.findall(r"S:\s*(-?[\d.]+)", err[:err.rindex("Summary:")])]
    return {"I": i, "S_max": max(st) if st else float("-inf"), "TP": tp}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    review = cut.load_review()
    rows = [r for r in cut.load_candidates()
            if args.all or review.get(r["n"], {}).get("status") in ("keep", "maybe")]
    res = []
    for r in rows:
        m = measure(cut.OUT / r["file"])
        res.append((r, m))
        print(f"{r['n']}  I {m['I']:6.1f}  Smax {m['S_max']:6.1f}  TP {m['TP']:5.1f}  {r['text'][:60]}")
    for k in ("I", "S_max"):
        v = [m[k] for _, m in res]
        print(f"\n{k}: min {min(v):.1f}  max {max(v):.1f}  spread {max(v) - min(v):.1f} dB  stdev {statistics.pstdev(v):.1f}")


if __name__ == "__main__":
    main()
