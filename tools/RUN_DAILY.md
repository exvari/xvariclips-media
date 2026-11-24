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
- Read `taste.md` and `decisions.csv` first. They hold every approval and rejection with reasons. Apply them.

## Steps
1. **Setup**
   - `pip install --break-system-packages -r requirements.txt`
   - Check that `ffmpeg` is installed (`apt-get install -y ffmpeg` if it's missing).
2. **Find candidates.** Any streamer is fair game (owner, 2026-11-23: "go for anyone as long as the clip is good"). The list below is a starting point, not a limit.
   - `yt-dlp --flat-playlist --playlist-end 40 -J "https://www.twitch.tv/<channel>/clips?filter=clips&range=24hr"`
   - Core channels: ishowspeed, kaicenat, lacy, caseoh_, xqc, stableronaldo, jynxzi, ludwig, jasontheween, marlon, agent00, zackrawrr, sketch, plaqueboymax, fanum.
   - Wider channels: moistcr1tikal, nickeh30, squeex, summit1g, shroud, timthetatman, vanosscrew, zoil, tfue, silky, cohhcarnage, yourragegaming, extraemily, erobb221, nmplol, hasanabi, emiru, nickmercs, dukedennis. Also any other streamer playing GTA 6 that you come across. Add a new channel here when it produces a keeper.
   - Filter to GTA 6 before downloading: `python gta6_filter.py '<dir>/*_24hr.json' all.json` (Twitch GQL gives each clip's game, VOD id and VOD offset). Skip slugs in `screened_slugs.txt` and add every slug you screen to it.
   - **Always run the `range=7d` pass too, until you have 3 keepers** (owner, 2026-11-24: "we wanna be ahead of schedule in case of any bad clips"). Don't stop at the first keeper. Go deeper than the top views: the top 7-day clips are almost all sex/nudity scenes, so sort the rest by date (newest first) and screen the next 40–60. Still zero beats weak: if only 1 clears the bar, schedule 1. The duplicate check matters even more for older clips: also check the earlier TikTok posts (yt-dlp can download `https://www.tiktok.com/@xvariclips/video/<id>`, then compare transcripts), because compilations can already contain a moment.
   - VOD context: if `context.py` / `--download-sections` stalls, fetch the 10s HLS segments directly (`yt-dlp -g -f 720p60 <vod>` gives the playlist; segment N covers VOD seconds N*10 to N*10+10; prepend `init-0.mp4`).
   - Drop titles that suggest sex or nudity (gyat, nude, shower, mandy, lucia, strip, freaky, etc.). Expect most top-viewed GTA 6 clips to be sex or nudity scenes anyway.
   - Download the top ~30 by views at ≤720p.
3. **Screen.**
   - Transcribe with `python transcribe_dir.py` (run it in the download folder).
   - Look at a 12-frame contact sheet of every candidate (`ffmpeg fps=12/dur,tile=4x3`). Do the safety check on the frames, not just the title.
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
