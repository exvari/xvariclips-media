"""
context.py: pull the real surroundings of a Twitch viewer clip from the streamer's VOD.
Viewer clips are often cut too late or too early. This grabs [clip - PRE, clip + POST]
from the VOD, finds exactly where the clip sits inside it, and writes a screening sheet:
word-timed transcript with CLIP START / CLIP END markers + 1 frame / 2s strip.

usage: python context.py <clip.mp4> <clip_info.json> <out_dir> [PRE=40] [POST=40]
"""
import json, subprocess, sys, os, numpy as np

def sh(cmd, **kw): return subprocess.run(cmd, check=True, **kw)

def load8k(p):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-ac", "1", "-ar", "8000", "-f", "s16le", "-"], capture_output=True)
    return np.frombuffer(r.stdout, np.int16).astype(np.float32)

def align(clip, ctx):
    a, b = load8k(clip), load8k(ctx)
    a = (a - a.mean()) / (a.std() + 1e-9); n = len(a)
    if len(b) <= n: return None, 0
    N = 1 << int(np.ceil(np.log2(len(b) + n)))
    c = np.fft.irfft(np.fft.rfft(b, N) * np.conj(np.fft.rfft(a, N)), N)[:len(b) - n + 1]
    cs = np.concatenate([[0], np.cumsum(b.astype(np.float64) ** 2)])
    e = np.sqrt(np.maximum(cs[n:n + len(c)] - cs[:len(c)], 0)); e = np.maximum(e, 0.2 * np.median(e) + 1e-3)
    s = c / e / np.sqrt(n); s = np.clip(s, -1, 1); i = int(np.argmax(s))
    return i / 8000, float(s[i])

def find_vod(channel, clip_ts):
    out = subprocess.run(["yt-dlp", "--flat-playlist", "--playlist-end", "15", "--print", "%(id)s|%(timestamp)s|%(duration)s",
                          f"https://www.twitch.tv/{channel}/videos?filter=archives&sort=time"], capture_output=True, text=True).stdout
    cands = []
    for line in out.splitlines()[:5]:
        vid, ts, dur = line.split("|")
        if ts == "NA":
            ts = subprocess.run(["yt-dlp", "--skip-download", "--no-warnings", "--print", "%(timestamp)s",
                                 f"https://www.twitch.tv/videos/{vid.lstrip('v')}"], capture_output=True, text=True).stdout.strip()
        if not ts.isdigit(): continue
        ts = int(ts); dur = float(dur) if dur != "NA" else 1e9
        if ts <= clip_ts <= ts + dur + 120: cands.append((vid.lstrip("v"), clip_ts - ts))
    return cands

def hms(t): t = max(0, t); return f"{int(t//3600)}:{int(t%3600//60):02d}:{t%60:06.3f}"

def main():
    clip, info, out = sys.argv[1], json.load(open(sys.argv[2])), sys.argv[3]
    PRE = float(sys.argv[4]) if len(sys.argv) > 4 else 40; POST = float(sys.argv[5]) if len(sys.argv) > 5 else 40
    os.makedirs(out, exist_ok=True)
    dur = float(info["duration"]); chan = info["webpage_url"].split("/")[3]
    cands = find_vod(chan, int(info["timestamp"]))
    vid, off = cands[0] if cands else (None, None)
    res = {"clip": clip, "vod": vid, "vod_candidates": cands}
    if not vid:
        print("no VOD found (deleted / sub-only / Kick) -> screen the clip alone"); res["context"] = None
    else:
        # 1) locate the clip with cheap audio over a wide window (clips can be made late or from VOD replays)
        W0 = max(0, off - dur - 900); W1 = off + 600
        aud = os.path.join(out, "wide_audio.m4a")
        sh(["yt-dlp", "-q", "--no-warnings", "-f", "audio_only/worstaudio/worst", "--download-sections", f"*{hms(W0)}-{hms(W1)}",
            "-o", aud, f"https://www.twitch.tv/videos/{vid}"])
        pos, score = align(clip, aud)
        print(f"VOD {vid}: align score {score:.2f}")
        if score < 0.3:
            print("could not place clip in VOD -> screen the clip alone"); res["context"] = None
        else:
            cstart = W0 + pos                      # clip start in VOD time
            a, b = cstart - PRE, cstart + dur + POST
            ctx = os.path.join(out, "context.mp4")
            sh(["yt-dlp", "-q", "--no-warnings", "-f", "best[height<=720]/best", "--download-sections", f"*{hms(a)}-{hms(b)}",
                "-o", ctx, f"https://www.twitch.tv/videos/{vid}"])
            p2, s2 = align(clip, ctx)
            res.update({"context": ctx, "ctx_vod_start": a, "clip_vod_start": cstart, "clip_in_ctx": p2, "align_score": s2, "clip_dur": dur})
            print(f"context ready: clip at {p2:.2f}s inside (score {s2:.2f})")
    json.dump(res, open(os.path.join(out, "context.json"), "w"), indent=1)

if __name__ == "__main__": main()
