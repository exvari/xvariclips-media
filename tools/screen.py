"""
screen.py: cheap screening sheet for one candidate (no rendering).
usage: python screen.py <dir with context.json>
Writes sheet.txt (timed transcript with CLIP START/END markers + loudness) and strip.jpg (frame every 2s, timestamped).
"""
import json, subprocess, sys, os, numpy as np, soundfile as sf
d = sys.argv[1]; c = json.load(open(os.path.join(d, "context.json")))
src = c["context"] or c["clip"]
cs = c.get("clip_in_ctx") or 0.0; ce = cs + (c.get("clip_dur") or 0)
wav = os.path.join(d, "a16.wav")
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-ac", "1", "-ar", "16000", wav], check=True)
a, sr = sf.read(wav, dtype="float32")
from faster_whisper import WhisperModel
m = WhisperModel("small.en", compute_type="int8")
segs, _ = m.transcribe(a, beam_size=3, word_timestamps=True, condition_on_previous_text=False, vad_filter=True)
lines, marks = [], {"start": False, "end": False}
for s in segs:
    if c["context"] and not marks["start"] and s.start >= cs: lines.append(f"---------- CLIP START {cs:.1f} ----------"); marks["start"] = True
    if c["context"] and not marks["end"] and s.start >= ce: lines.append(f"---------- CLIP END {ce:.1f} ----------"); marks["end"] = True
    lines.append(f"[{s.start:6.1f}-{s.end:6.1f}] {s.text.strip()}")
loud = [int(20 * np.log10(np.sqrt((a[i*sr:(i+1)*sr]**2).mean()) + 1e-9)) for i in range(len(a)//sr)]
open(os.path.join(d, "sheet.txt"), "w").write("\n".join(lines) + "\n\nloudness/s: " + " ".join(map(str, loud)) + "\n")
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-vf",
    "fps=1/2,scale=200:-2,drawtext=fontfile=/home/claude/clipper/fonts/Anton-Regular.ttf:text='%{pts\\:gmtime\\:0\\:%M\\\\\\:%S}':fontsize=18:fontcolor=yellow:borderw=2:x=3:y=3,tile=10x8",
    "-frames:v", "1", os.path.join(d, "strip.jpg")], check=True)
print(open(os.path.join(d, "sheet.txt")).read()[:6000])
