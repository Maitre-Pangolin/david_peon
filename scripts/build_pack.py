#!/usr/bin/env python3
"""Build pack/ (openpeon.json, .checksums, sounds/*.wav) from picks.tsv.

  scripts/build_pack.py --from-review   # refresh picks.tsv from work/review.json first
  scripts/build_pack.py                 # build from picks.tsv (clips cut into work/picks/)
  peon packs install-local pack --force

picks.tsv is the tracked list of sounds in the pack: event, YouTube source id,
start/end in the source, edge nudges and the line's text. No audio is tracked.
"""
import argparse
import csv
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cut  # noqa: E402

PACK = cut.ROOT / "pack"
SOUNDS = PACK / "sounds"
PICKS = cut.ROOT / "picks.tsv"
CLIPS = cut.ROOT / "work" / "picks"
FIELDS = ["event", "source", "start", "end", "adj_start", "adj_end", "text"]
EVENTS = ["session.start", "task.acknowledge", "task.complete", "task.error",
          "input.required", "resource.limit", "user.spam"]

MANIFEST = {
    "cesp_version": "1.0",
    "name": "attenborough",
    "display_name": "Sir David Attenborough",
    "version": "1.0.0",
    "description": ("Real narration from BBC natural history programmes: squirrels at last, "
                    "quarrelsome fish and sloths in a hurry. Clips cut from official BBC "
                    "YouTube uploads; the audio is © BBC and is not licensed by this project."),
    "author": {"name": "david_peon"},
    "license": "LicenseRef-BBC-Copyright",
    "language": "en",
}


def camel(text, max_words=6):
    words = re.findall(r"[A-Za-z0-9']+", text)[:max_words]
    return "".join(w.replace("'", "").capitalize() for w in words) or "Clip"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def picks_from_review():
    """Kept clips from work/review.json, in event order, with their final event and nudges."""
    review = cut.load_review()
    rows = []
    for r in cut.load_candidates():
        rv = review.get(r["n"], {})
        if rv.get("status") == "keep":
            rows.append({"event": rv.get("event") or r["event"], "source": r["source"],
                         "start": r["start"], "end": r["end"],
                         "adj_start": f"{rv.get('adj_start', 0.0):.1f}", "adj_end": f"{rv.get('adj_end', 0.0):.1f}",
                         "text": r["text"]})
    rows.sort(key=lambda p: EVENTS.index(p["event"]))
    return rows


def load_picks():
    with PICKS.open(newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    for i, p in enumerate(rows, 1):
        if p["event"] not in EVENTS:
            sys.exit(f"picks.tsv line {i + 1}: unknown event {p['event']!r}")
        p["n"] = f"{i:02d}"
        p["file"] = f"{p['n']}_{cut.slug(p['text'])}.wav"
    return rows


def cut_picks(picks, force=False):
    CLIPS.mkdir(parents=True, exist_ok=True)
    for p in picks:
        if force or not (CLIPS / p["file"]).exists():
            cut.cut(p, float(p["adj_start"]), float(p["adj_end"]), out_dir=CLIPS)


def build(picks):
    if SOUNDS.exists():
        shutil.rmtree(SOUNDS)
    SOUNDS.mkdir(parents=True)
    categories = {ev: {"sounds": []} for ev in EVENTS}
    used, checksums = set(), []
    for p in picks:
        name = camel(p["text"])
        while name in used:
            name += "X"
        used.add(name)
        dst = SOUNDS / f"{name}.wav"
        shutil.copy2(CLIPS / p["file"], dst)
        digest = sha256(dst)
        categories[p["event"]]["sounds"].append({"file": f"sounds/{dst.name}", "label": p["text"], "sha256": digest})
        checksums.append(f"{dst.name} {digest}")

    manifest = {**MANIFEST, "categories": {k: v for k, v in categories.items() if v["sounds"]}}
    (PACK / "openpeon.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    (PACK / ".checksums").write_text("\n".join(checksums) + "\n")
    for ev in EVENTS:
        print(f"{ev:17} {len(categories[ev]['sounds']):2}")
    size = sum(f.stat().st_size for f in SOUNDS.iterdir())
    print(f"{len(picks)} sounds, {size / 1e6:.1f} MB -> {PACK}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from-review", action="store_true", help="rewrite picks.tsv from work/review.json first")
    ap.add_argument("--force", action="store_true", help="re-cut clips that already exist")
    args = ap.parse_args()

    if args.from_review:
        rows = picks_from_review()
        if not rows:
            sys.exit("no clips marked keep in work/review.json")
        with PICKS.open("w", newline="") as f:
            w = csv.DictWriter(f, FIELDS, delimiter="\t", lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        print(f"wrote {len(rows)} picks to {PICKS.name}")

    picks = load_picks()
    missing = sorted({p["source"] for p in picks if not (cut.ROOT / "sources" / p["source"] / f"{p['source']}.webm").exists()})
    if missing:
        sys.exit(f"missing source audio for {', '.join(missing)} - run scripts/rebuild.sh")
    cut_picks(picks, args.force)
    build(picks)


if __name__ == "__main__":
    main()
