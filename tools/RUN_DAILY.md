# Daily clip run for TikTok @xvariclips

Follow this from top to bottom on every scheduled run. Nobody is watching, so don't ask questions. If something blocks you, write it in the run report and keep going with whatever still works.

## Hard rules (from the owner, not negotiable)
- **GTA 6 only.** No GTA V, GTA RP or FiveM, no IRL clips, no trailers.
- **TikTok-safe only.** Reject at screening: nudity, sex scenes (the brothel / "check every room" mission, the Lucia shower, the strip club, lap dances, bed scenes, characters in underwear or bikinis), thirst or "gyatt" clips, and slur-heavy clips. Blurring does NOT make these OK.
- **Funny or nothing.** One beat: an absurd or messed-up action plus the streamer's quotable line or reaction. Include the lead-up. Never cut before the payoff. Zero clips beats weak clips.
- **Captions are word-for-word** what the streamer says. Censoring the caption text (f***) is fine. Never bleep or mute the audio.
- **Layout: the facecam appears exactly once.** Never blur chat or the cam. QC flags DOUBLE FACECAM. Pick one of two layouts per clip:
  - **Top cam** (owner likes it): an enlarged cam above the gameplay, with the in-stream cam cropped out of the game band via `layout.game`. Example: cam on the left edge, so `"facecam": [0,0.53,0.222,0.22], "game": [0.222,0,0.778,1]`. Use it when the streamer's face/reaction is a big part of the joke AND the in-stream cam sits on an edge or in a corner, so cropping it out removes ≤ ~25% of the frame and none of the action.
  - **No top cam**: the full uncropped frame with the cam left where it is (`"facecam": null`, like the EXAMPLE). Use it when the in-stream cam is already big and readable, when cropping it out would cut the action, or when the joke is mostly the visual.
- **No duplicates.** Check by moment (`python dupcheck.py`), not just by URL. Also check `ledger.csv` and the `clips/` folder.
- Read `taste.md` and `decisions.csv` first. They hold every approval and rejection with reasons. Apply them. The 2026-11-24 recalibration section of `taste.md` holds the current gate and overrides the narrower one above it.

## Steps
1. **Setup**
   - `pip install --break-system-packages -r requirements.txt`
   - Check that `ffmpeg` is installed (`apt-get install -y ffmpeg` if it's missing).
2. **Find candidates — start with the GAME, not the channel list.** (Owner, 2026-11-24: a fixed list of big entertainer channels is why two runs found almost nothing — their top clips are mostly sex scenes.)
   - **Category first:** `python twitch_category_clips.py LAST_DAY 5` and `LAST_WEEK 10` — Twitch GQL, every channel playing GTA VI, 100 clips a page.
   - **Then channels**, as a second pass, not the main one: `yt-dlp --flat-playlist --playlist-end 100 -J "https://www.twitch.tv/<channel>/clips?filter=clips&range=7d"`, then `python gta6_filter.py '<dir>/*_7d.json' all.json` to get each clip's game, VOD id and VOD offset. Skip slugs already in `screened_slugs.txt`, and append every slug you screen.
   - Channels that have produced candidates: ohnepixel, lirik, missmikkaa, joe_bartolozzi, distortion2, avoidingthepuddle, theburntpeanut, 2xrakai, ramez05, symfuhny, vinesauce, clix, dansgaming, pokelawls, nickeh30, caseoh_, kaicenat, ishowspeed, lacy, moistcr1tikal. Mid-size streamers out-produce the big ones for us. Add new ones here when they land.
   - **Kick:** `python kick_clips.py <comma-separated channels>` (xqc, adinross, n3on, iceposeidon, kaysan, konvy, cuffem, westcol, stevewilldoit). Filter `cat == "Grand Theft Auto VI (GTA)"`.
   - YouTube is blocked from the cloud (bot check). Use compilation titles only as a signal of which moments are circulating, then find the original Twitch/Kick clip.
   - **Rank by promise, not by views.** Views correlate with sexual content. Prefer titles about animals, physics, bugs, NPCs, discoveries, chases, escapes, timing, karma.
   - **Always run the `range=7d` pass too, until you have 3 keepers** (owner, 2026-11-24: "we wanna be ahead of schedule in case of any bad clips"). Don't stop at the first keeper. Go deeper than the top views: the top 7-day clips are almost all sex/nudity scenes, so sort the rest by date (newest first) and screen the next 40–60. Still zero beats weak: if only 1 clears the bar, schedule 1. The duplicate check matters even more for older clips: also check the earlier TikTok posts (yt-dlp can download `https://www.tiktok.com/@xvariclips/video/<id>`, then compare transcripts), because compilations can already contain a moment.
   - VOD context: if `context.py` / `--download-sections` stalls, fetch the 10s HLS segments directly (`yt-dlp -g -f 720p60 <vod>` gives the playlist; segment N covers VOD seconds N*10 to N*10+10; prepend `init-0.mp4`).
   - Drop titles that suggest sex or nudity (gyat, nude, shower, mandy, lucia, strip, freaky, etc.). Expect most top-viewed GTA 6 clips to be sex or nudity scenes anyway.
   - Download the top ~30 by views at ≤720p.
3. **Screen in three passes, and say which pass each clip reached.** Titles, views and transcripts are discovery signals only — visual comedy never shows up in a transcript. Report access failures separately from quality rejections, and never claim you watched something you couldn't open.
   - **screened:** `python transcribe_dir.py` in the download folder, then `python strips.py <dir>` — a 10-frame labelled strip per clip, stacked 9 to a sheet. Safety check happens here, on frames.
   - **watched:** for anything still alive, `python dense.py <clip.mp4> <out.jpg> 2` — 2 frames per second across the whole clip, read alongside the word-timed transcript.
   - **verified in context:** for every finalist, `python vod_window.py <vod_id> <start_s> <end_s> <out>` (pulls the HLS segments directly; `context.py`'s download often stalls), then align and transcribe. Viewer clips routinely cut the payoff off — on 2026-11-24 the best line was 50s after the clip ended.
   - For each survivor, write `screen.setup` and `screen.payoff` (one sentence each).
   - Keep at most 3 per run (schedule them on separate slots, next free ones first). Log every rejection with its reason in `decisions.csv`.
4. **Render** each keeper with `clipper.py`:
   - Add a record to `batch.json`. Copy the EXAMPLE record's shape, set `status: "selected"`, and point `source_file` at the downloaded clip.
   - Trim with `in`/`out` to 6–15s around the beat.
   - Run `python clipper.py batch`.
   - Check `out/<id>/qc.json`. If it shows problems, fix them or drop the clip.
5. **Upload.** Copy each final `*_captioned.mp4` to `clips/<id>.mp4` in this repo. Commit and push to main. Check that `https://raw.githubusercontent.com/exvari/xvariclips-media/main/clips/<id>.mp4` returns 200.
6. **Schedule** in Buffer:
   - Organization: "My organization".
   - TikTok channel: `6b03a9578541f09ecb6ef4f4`.
   - **Credit the creator in every caption** (owner rule 2026-11-24). Look the streamer up in `tools/creators.csv`. If `status` is `verified` or `likely`, end the caption with `🎥 @<tiktok_handle>` (exact username, no spaces: TikTok's API turns a matching @username into a link to their account). Otherwise end it with `🎥 twitch.tv/<channel>`. Never tag a handle you haven't verified: a wrong @ tags a random account. When you verify a new handle (the account's name matches and the content is clearly theirs, not a clip account), add it to creators.csv with the evidence.
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
