# Clip pipeline (TikTok / Reels)

One script, `clipper.py`, does: **fetch** (yt-dlp, only the needed section) → **cut** (in/out, optional dead-air tightening) → **transcribe** (faster-whisper, word timestamps) → **render** (1080×1920 H.264/AAC, loudness −14 LUFS, captioned + clean) → **QC** (format, loudness/peaks, contact sheet with platform UI zones, re-transcribes the export) → **preview** (`out/index.html` with copy buttons). Nothing is ever posted.

## Setup (once, Windows)
Double-click `setup.bat` (installs ffmpeg + yt-dlp + faster-whisper). Mac/Linux: install ffmpeg, then `pip install -r requirements.txt`.

## Every batch
1. `python clipper.py discover` → `discovered.json` (recent clips/VODs + view counts for every channel in `channels.json`, stamped with when they were observed).
2. Watch the footage. In `batch.json`, set the moment's `source_url`, `in`, `out` (source timestamps), `layout`, `header`, `header_alts`, `emphasis`, `posting`, and `status: "selected"`.
3. Double-click `run.bat` (or `python clipper.py batch`). Outputs land in `out/<id>/`.
4. Listen once and fix names/slang in `work/<id>/captions.srt`, create an empty file `work/<id>/.captions_edited`, then `python clipper.py step render <id>` and `python clipper.py step qc <id>`.

Or just ask Claude: "run the next clip batch" with this folder connected — it does steps 1–4.

## Record fields (batch.json)
| field | meaning |
|---|---|
| `in`, `out` | timestamps in the ORIGINAL broadcast/VOD (`1:02:03.5`) |
| `keep` | optional list of `[start,end]` source ranges to keep (manual dead-air removal) |
| `tighten_silence` | e.g. `1.0` → silences longer than 1 s shrink to ~0.6 s. Don't use when a pause is the joke |
| `layout.mode` | `split` (facecam top / gameplay bottom), `fill` (9:16 crop), `fit` (whole frame on blurred bg) |
| `layout.facecam`, `layout.game`, `layout.box` | `[x, y, w, h]` as fractions of the source frame |
| `layout.fill_x` | horizontal centre (0–1) for `fill` |
| `emphasis` | words to colour yellow in captions (use sparingly) |
| `source_file` | use a local video instead of downloading |
| `moment_key` | short slug; the ledger blocks the same moment being clipped twice |

`ledger.csv` records every rendered moment. Same source + overlapping time, or same streamer/date/moment_key, is skipped as a duplicate.

## Tuning
`config.json`: fonts/sizes, caption baseline, header position, split height, loudness, x264 preset, Whisper model (`small.en` default; `medium.en` is more accurate but slower), and `vocab_prompt` (names Whisper should spell right).

## Rules this workflow follows
Never label GTA V / RP / mods / trailers as GTA 6. Record broadcast date separately from upload date. Prefer original VODs over reposts. Metrics are only what was seen, with the time seen. Instagram allows max 5 hashtags (Dec 2025 change); TikTok captions are kept under 2,200 characters.

Font: Anton (SIL Open Font License, `fonts/OFL.txt`).

## Live clip radar (grab clips while streams are live)
`python clipper.py watch 5 8` polls every channel in channels.json every 5 minutes for 8 hours.
It logs every clip chat makes (views + views/minute) to radar.json, shows the hottest in radar.html
(auto-refreshes), and auto-downloads risers into sources/ (thresholds in config.json → "radar").
Then ask Claude to "make clips from sources" — it checks each one, writes the header and captions, and renders.
It only runs while that window stays open; it is not a background service.
