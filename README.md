# david_peon

A [peon-ping](https://github.com/PeonPing/peon-ping) sound pack for Claude Code made of real Sir David Attenborough narration: 52 short lines from BBC natural history programmes, mapped to peon-ping's 7 events.

> “At last, a squirrel.” — now playing every time Claude Code finishes a task.

## Install

Requires [peon-ping](https://github.com/PeonPing/peon-ping).

```bash
git clone https://github.com/Maitre-Pangolin/david_peon.git
peon packs install-local david_peon/pack
peon packs use attenborough
```

Or try it for one Claude Code session only: `/peon-ping-use attenborough`.

## What's in the pack

| Event | Sounds | For example |
|---|---|---|
| `session.start` | 8 | “Here they are, Arctic wolves.” |
| `task.acknowledge` | 8 | “Very well.” |
| `task.complete` | 9 | “At last, a squirrel.” |
| `task.error` | 8 | “This magnificent creature preparing… Whoops!” |
| `input.required` | 7 | “Termites. Not easy to catch when you’re blind.” |
| `resource.limit` | 8 | “The sloth’s way of compensating for that is not to eat more, but to do less.” |
| `user.spam` | 4 | “Boo!” |

The full list, with source video and timestamps, is in [`picks.tsv`](picks.tsv).

## Audio rights

The clips are cut from official uploads on the BBC and BBC Earth YouTube channels. The audio is © BBC; this project claims no rights to it and does not license it. The clips are 1–5 seconds each and shared for fun, non-commercially. If you are a rights holder and want them removed, open an issue and they will be taken down. The code and documentation are MIT licensed; see [LICENSE](LICENSE).

Every line is a real recording. No voice cloning or synthetic speech was used.

## How it was made

Built in one Claude Code session. The pipeline is reproducible from the scripts in this repo:

| Step | Command | What it does |
|---|---|---|
| 1. Source | `yt-dlp -f bestaudio --write-info-json -o "sources/%(id)s/%(id)s.%(ext)s" <ids>` | Audio-only download of the 10 videos listed below |
| 2. Transcribe | `scripts/transcribe.sh` | mlx-whisper large-v3-turbo, word timestamps, runs locally |
| 3. Search | `scripts/search.py --short 5 --join 2` | Every sentence (or pair) of 5 s or less; regex search too |
| 4. Shortlist | `candidates.tsv` | 80 candidate lines across the 7 events |
| 5. Cut | `scripts/cut.py` | Pad, low-cut, 3:1 compression, fixed gain to −16 LUFS target, −2 dBFS limiter, fades |
| 6. Review | `python3 scripts/review.py` → http://127.0.0.1:8765 | Local page: play, keep/maybe/reject, re-assign events, nudge edges |
| 7. Level check | `scripts/levels.py` | Loudness report for the shortlisted clips |
| 8. Pack | `scripts/build_pack.py --from-review` | Writes `picks.tsv`, cuts the picks, builds `pack/` with checksums |

To rebuild the pack from `picks.tsv` (after downloading the sources): `scripts/build_pack.py`. Tools: `yt-dlp`, `ffmpeg`, Python 3, and `mlx-whisper` (Apple Silicon) for step 2.

The story of the session, as a slide deck, is in [`docs/deck/`](docs/deck/).

## Sources

| ID | Title | Length |
|---|---|---|
| leDm_-nfr2w | Sir David Attenborough being iconic for 25 minutes | 25:44 |
| f828q6MHOkY | Unforgettable Moments From Planet Earth II | 47:26 |
| hBO70igBtts | 1 Hour of Amazing Animal Moments | 1:02:05 |
| el4CQj-TCbA | Iguana vs Snakes (Full Clip), Planet Earth II | 4:27 |
| vTSVzeOdj8A | Baby ibex descends mountains to escape a fox | 1:17 |
| rn6R4ncd2OU | Amazing Clownfish Teamwork, Blue Planet II | 6:38 |
| aIovmgzyuL0 | The Deadly Portuguese Man O' War, Blue Planet II | 5:32 |
| GnMEeiY-IOo | Attenborough's Closing Speech, Blue Planet II | 3:40 |
| 2TJaNDBI87s | Bird interrupts David Attenborough | 1:24 |
| czgc56Vfz4w | The story behind Life on Earth | 3:23 |

Watch them on YouTube: `https://www.youtube.com/watch?v=<ID>`.
