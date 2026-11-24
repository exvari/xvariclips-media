"""dupcheck.py <candidate.mp4|wav> [streamer]: compares a candidate's speech against every clip we've already made
(work/*/words.json). Same moment = same words, even when a different viewer clipped it."""
import sys, json, glob, re, subprocess, soundfile as sf
from faster_whisper import WhisperModel
norm = lambda t: [w for w in re.sub(r"[^a-z0-9' ]", " ", t.lower()).split() if len(w) > 2]
def grams(ws): return {" ".join(ws[i:i+3]) for i in range(len(ws) - 2)}
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", sys.argv[1], "-ac", "1", "-ar", "16000", "/tmp/dup.wav"], check=True)
a, _ = sf.read("/tmp/dup.wav", dtype="float32")
segs, _ = WhisperModel("small.en", compute_type="int8").transcribe(a, beam_size=1, vad_filter=True)
cand = grams(norm(" ".join(s.text for s in segs)))
hits = []
for f in glob.glob("work/*/words.json"):
    past = grams(norm(" ".join(w["w"] for w in json.load(open(f)))))
    if cand and past:
        ov = len(cand & past) / min(len(cand), len(past))
        if ov >= 0.25: hits.append((round(ov, 2), f.split("/")[1]))
for ov, cid in sorted(hits, reverse=True): print(f"DUPLICATE? {cid} overlap {ov}")
if not hits: print("no match in past clips")
