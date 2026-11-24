# Daily clip run for TikTok @xvariclips

Follow this from top to bottom on every scheduled run. Nobody is watching, so don't ask questions. If something blocks you, write it in the run report and keep going with whatever still works.

## Hard rules (from the owner, not negotiable)
- **GTA 6 only.** No GTA V, GTA RP or FiveM, no IRL clips, no trailers.
- **TikTok-safe only.** Reject at screening: nudity, sex scenes (the brothel / "check every room" mission, the Lucia shower, the strip club, lap dances, bed scenes, characters in underwear or bikinis), thirst or "gyatt" clips, and slur-heavy clips. Blurring does NOT make these OK.
- **Funny or nothing.** One beat: an absurd or messed-up action plus the streamer's quotable line or reaction. Include the lead-up. Never cut before the payoff. Zero clips beats weak clips.
- **Captions are word-for-word** what the streamer says. Censoring the caption text (f***) is fine. Never bleep or mute the audio.
- **Layout:** the full uncropped game frame, with the streamer's facecam left where it already is in the stream. **Never show the facecam twice** (no extra cam on top of a frame that already has it): use `"layout": {"mode": "stack", "facecam": null}` like the EXAMPLE record. Never blur chat or the cam. QC flags DOUBLE FACECAM.
- **No duplicates.** Check by moment (`python dupcheck.py`), not just by URL. Also check `ledger.csv` and the `clips/` folder.
- Read `taste.md` and `decisions.csv` first. They hold every approval and rejection with reasons. Apply them.

## Steps
1. **Setup**
   - `pip install --break-system-packages -r requirements.txt`
   - Check that `ffmpeg` is installed (`apt-get install -y ffmpeg` if it's missing).
2. **Find candidates.** Any streamer is fair game (owner, 2026-11-23: "go for anyone as long as the clip is good"). The list below is a starting point, not a limit.
   - `yt-dlp --flat-playlist --playlist-end 40 -J "https://www.twitch.tv/<channel>/clips?filter=clips&range=24hr"`
   - Core channels: ishowspeed, kaicenat, lacy, caseoh_, xqc, stableronaldo, jynxzi, ludwig, jasontheween, marlon, agent00, zackrawrr, sketch, plaqueboymax, fanum.
   - Wider channels: moistcr1tikal, nickeh30, squeex, summit1g, shroud, timthetatman, vanosscrew, zoil, tfue, silky, cohhcarnage, yourragegaming, extraemily, erobb221, nmplol, hasanabi, emiru, nickmercs, dukedennis. Also any other streamer playing GTA 6 that you come across. Add a new channel here when it produces a keeper.
   - If the 24h pass finds no keeper, repeat with `range=7d` before giving up. The duplicate check matters even more for older clips: also check the earlier TikTok posts, because compilations can already contain a moment.
   - Drop titles that suggest sex or nudity (gyat, nude, shower, mandy, lucia, strip, freaky, etc.). Expect most top-viewed GTA 6 clips to be sex or nudity scenes anyway.
   - Download the top ~30 by views at ≤720p.
3. **Screen.**
   - Transcribe with `python transcribe_dir.py` (run it in the download folder).
   - Look at a 12-frame contact sheet of every candidate (`ffmpeg fps=12/dur,tile=4x3`). Do the safety check on the frames, not just the title.
   - For each survivor, write `screen.setup` and `screen.payoff` (one sentence each).
   - Keep at most 3. Log every rejection with its reason in `decisions.csv`.
4. **Render** each keeper with `clipper.py`:
   - Add a record to `batch.json`. Copy the EXAMPLE record's shape, set `status: "selected"`, and point `source_file` at the downloaded clip.
   - Trim with `in`/`out` to 6–15s around the beat.
   - Run `python clipper.py batch`.
   - Check `out/<id>/qc.json`. If it shows problems, fix them or drop the clip.
5. **Upload.** Copy each final `*_captioned.mp4` to `clips/<id>.mp4` in this repo. Commit and push to main. Check that `https://raw.githubusercontent.com/exvari/xvariclips-media/main/clips/<id>.mp4` returns 200.
6. **Schedule** in Buffer:
   - Organization: "My organization".
   - TikTok channel: `6b03a9578541f09ecb6ef4f4`.
   - Use `create_post` with `mode: customScheduled`, `schedulingType: automatic`, the `video` asset URL, and the post caption plus 3–5 hashtags (the emoji goes in the caption, not the video).
   - Slots, Pacific time:
     - Mon–Fri: 15:30 and 18:30
     - Sat: 16:30
     - Sun: 17:00
   - Use the next free slots that are at least 3 hours away, so the owner has time to delete anything bad. Check `list_posts` first, so you never put two posts in the same slot.
7. **Record** what you did:
   - Add the new rows to `ledger.csv` and `decisions.csv` (verdict `auto-scheduled`).
   - In `ledger.csv`, fill `posted_slot_pt` (e.g. `Tue 2026-11-24 15:30`) and `buffer_post_id` (from `create_post`) for every scheduled clip.
   - **Slot tracking:** for every ledger row with a `buffer_post_id` that was posted 48h+ ago and has an empty `views_48h`, read its views with `list_posts` (`includeMetrics: true`) and fill `views_48h`. Never put two posts within 2h of each other: same-slot posts compete with each other (on 11-19, 4 posts in 3 min got 697/7/4/2 views).
   - Once 30+ rows have `views_48h`, compare median views per slot (plus `tools/slot_baseline.csv`) and write the result in `taste.md`. Change the slots only if one is clearly better.
   - `work/<id>/words.json` is committed (the rest of work/ and out/ is ignored) so `dupcheck.py` keeps its history.
   - Commit `tools/` changes with the clips.
   - End with a short report: what you scheduled, the slot times, what you rejected and why, and anything that blocked you.
