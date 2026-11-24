# Taste reference: @xvariclips (reread before every batch)

Status: PROVISIONAL. Built from feedback so far. Update after every round of feedback; never delete reasons, add to them.

## REFERENCE FORMAT (from Ivan's examples, 2026-11-22). This is the main format.
Examples: "Lacy meets a Cat in GTA VI 😹" (kicks the cat, cut to his face, B&W shocked meme faces, "What?") and "sweeet 😭" ("Random act of violence! Sweet! Sweet!" while ramming traffic).
- LENGTH: 6–10s of footage. The action lands within 1–2s. No spoken setup.
- ONE BEAT: the streamer does something messed up, dark or absurd (animal, random violence, NPC mishap), and HIS REACTION/LINE is the joke.
- FACE: facecam big and visible; the reaction is half the clip.
- TEXT: one tiny caption = his quote or a 3–6 word description + emoji (emoji goes in the post caption: the burned-in font can't draw emoji). No header band, no word-by-word captions.
- ENDING: cut right after the reaction so it loops.
- Longer story clips (like the alien, 44s) can still work when the line is great, but default to the short format.

## What a keeper needs (gate: fill all 4 or reject)
1. SETUP, in one sentence: what is happening and why it matters.
2. PAYOFF, in one sentence: the exact thing that is funny (a line, an action, a consequence).
3. A new viewer understands it with zero stream knowledge.
4. The payoff is SEEN or HEARD in the clip, not implied by the title.

## Proven to work (approved / posted)
- CaseOh "keep it pristine" (car immediately wrecked): stated intention, then instant contradiction.
- Lacy pets a dog, then gets tackled by cops: wholesome setup into an absurd consequence. Context was extended from the VOD and that made it work.
- Kai girlfriend argument / "I can explain": interpersonal conflict with clear stakes.
- Speed stick-up / scooter getaway: committed chaos with a visible ridiculous visual.
- StacksWopo is the best seller (his voice and trolling). GTA 6 only.

## Rejected, and why (specific)
- No payoff / boring: generic driving, menus, cutscene-only, "funny NPC line" with no streamer reaction (xQc time zones, YourRAGE first mission, Tim timer, Ludwig rant).
- Not GTA 6: GTA V RP / FiveM, IRL clips from gaming streamers (Ron road rage).
- Starts too late: Stacks "I'm not fighting nobody" had no lead-up; "not ready for the cutscene" cut out the cutscene itself.
- Ends early / jumps: "it's a prank" ran into an unrelated scene, then ended. xQc NPC and Lacy 7s clips ended at the good part.
- Bad source: bleeped audio or pixelation baked into YouTube edits. Use raw VODs.
- Captions not word-for-word ("gang" became "bro"). Censored caption text is fine; censored audio is not.
- Layout: no blur boxes over chat/cam; no top-cam duplication; full game frame.
- Edits (Nick Eh 30): v1 hid the action (too dark, facecam-only); v2 cropped gameplay; v3 "alright" — whole moments, full frame, game audio audible.
- Last batch (Speed NPC, Lacy driver, Nick x2, Speed Hamilton, Kai NPC, xQc heli): "unfunny / boring". Likely causes: picked by view count, payoff is an NPC line or a vague claim, no real escalation.

## Latest verdicts (2026-11-22)
- APPROVED: Speed finds alien, "KSI! It was you the whole time, you fat forehead m***!". Why it works: an absurd thing visible on screen, plus the streamer's own specific, quotable line (a roast aimed at a known person), plus loud, genuine energy. No game knowledge needed.
- REJECTED (boring): Lacy "good clip" plane crash. A plain fail with a FAILED screen; the setup was long and quiet; no funny line after.
- REJECTED (boring): CaseOh "look at that drift… never mind". Mostly driving; the payoff is a mild throwaway line.
- Lesson: "stated intention then fail" is NOT enough by itself. The payoff needs a memorable LINE or REACTION from the streamer, not just a game failure.

## Selection heuristics (current)
- Strongest pattern so far: [absurd or surprising visual] + [streamer's specific quotable line or roast] + [high energy]. Score candidates on all three; need at least 2 strong.
- Prefer: streamer causes the chaos and reacts; failed plan; sharp comeback; escalation within 30s; consequence lands on screen.
- Distrust: clip titles; view counts from tiny channels; NPC monologues; "wtf/omg/??" titled clips with no transcript payoff.
- Twitch/Kick viewer clips are often cut wrong: always pull plus or minus 30s from the VOD before deciding start/end.

## Duplicates
- The same moment gets clipped by many viewers under different URLs. Before screening, run `python dupcheck.py <clip>`: it compares the speech against every clip already made. A score of 0.25 or more = probably the same moment, so reject it.

## Honest limits of this workflow
Claude reads word-timed transcripts, audio energy and frames. It cannot hear tone or comedic delivery, so "is it funny" stays UNVERIFIED until Ivan approves. Boundaries and captions can be verified.

## TikTok-safe rule (2026-11-22, user: "how many of these would get flagged and restricted")
- HARD REJECT at screening, before sending anything: nudity or sex scenes of any kind (Lucia shower, brothel/"check every room" mission, strip club, lap dance, bed scenes, characters in underwear), sexual dialogue as the main joke, "gyatt"/thirst clips.
- Blurring does not make these OK: the scene itself gets the post restricted.
- High view counts on Twitch are often BECAUSE of this content; don't trust views as a funny signal for these.

## Sourcing lessons (2026-11-23)
- Twitch top-viewed GTA 6 clips are mostly sex/nudity scenes -> poor source for TikTok-safe content.
- Loudness-spike VOD mining picks up music/game audio; not productive without laughter/speech detection.
- Best remaining sources: Stacks raw via user's PC (YouTube blocked in cloud); TikTok clipper accounts that already post clean GTA 6 clips (need account list).

## Sourcing lessons (2026-11-23 daily run, auto)
- 24h Twitch clips from the 15 channels: 504 listed, 34 screened, 0 kept. About 1 in 4 screened were TikTok-unsafe (brothel/bed, shower, nude Mandy, sex toys, club dancers) and about 1 in 5 were not GTA (chess, IRL, Marvel trailer, music).
- New rejection pattern: a payoff that happens far away (a tiny explosion in the background) doesn't count as SEEN on a phone screen, even when the streamer's line is good (ludwig_non_lethal).
- dupcheck.py has no history in a fresh cloud clone (work/*/words.json isn't in the repo), so the moment duplicate check falls back to ledger.csv moment_keys only.
- 2026-11-23 owner verdict on ludwig_non_lethal: "lame". A near-miss is still a miss, even when the owner asks for a post: if nothing clears the bar, say so instead of posting the closest one.
- Top 7-day GTA 6 Twitch clips rechecked: 17 of 20 were sex/nudity scenes. The Twitch top-clips feed is basically used up as a TikTok-safe source.
- 2026-11-23 owner on moist_posthumous: "not bad", "double face cam is a no no". Rule: show the facecam once. Use stack with facecam:null (full frame, cam stays where the stream has it). Never add a second, enlarged cam band.
- 2026-11-23 owner follow-up: "we can use top face cam, I like that, we just have to know when to use it". Rule: top cam is fine as long as the in-stream cam is cropped out of the game band (one cam only). Use top cam when the reaction is the joke and the cam sits on an edge or in a corner. Use full frame with no top cam when the cam is already big, overlaps the action, or the joke is visual. See RUN_DAILY Layout.
- 2026-11-24 owner: tag the creator's TikTok in every caption so we're not "stealing content". See RUN_DAILY step 6 and tools/creators.csv (verified handles only; fall back to twitch.tv/<channel>).

## Sourcing lessons (2026-11-24 daily run, auto)
- Twitch GQL (`clip(slug){game{name} video{id} videoOffsetSeconds}`) gives each clip's game and VOD offset: filter to "Grand Theft Auto VI" before downloading. 24h pass: 1,038 clips listed, 651 GTA VI, 72 screened, 1 kept.
- The VOD can be pulled by fetching the 10s HLS segments directly (yt-dlp --download-sections and context.py timed out / failed to align). Segment N covers VOD seconds N*10..N*10+10.
- Nick Eh 30's "family-friendly streamer turns evil" angle produced most of today's usable material; the rest was mission dialogue, driving, or flagged content.
