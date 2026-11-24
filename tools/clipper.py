#!/usr/bin/env python3
"""
Streamer clip pipeline: fetch -> cut -> transcribe -> render (vertical 1080x1920) -> QC -> preview.

Usage (from this folder):
  python clipper.py discover                 # list recent clips/VODs from channels.json (needs network access to Twitch/YouTube)
  python clipper.py batch                    # run every record in batch.json with status "selected"
  python clipper.py batch ID [ID ...]        # run specific records
  python clipper.py step fetch|cut|transcribe|render|qc ID
  python clipper.py preview                  # rebuild out/index.html
  python clipper.py ledger                   # check batch.json against ledger.csv for duplicates

Edit captions: after "transcribe", fix work/ID/captions.srt by hand (names, slang), then run "step render ID".
Nothing is ever published by this script.
"""
import csv, json, os, re, shutil, subprocess, sys, html, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORK, OUT = ROOT / "work", ROOT / "out"
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
W, H = 1080, 1920


def run(cmd, cwd=None, capture=False):
    print("  $", " ".join(str(c) for c in cmd)[:240])
    r = subprocess.run([str(c) for c in cmd], cwd=cwd, text=True,
                       capture_output=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(r.stdout[-2000:], r.stderr[-3000:])
        raise RuntimeError(f"command failed: {cmd[0]}")
    return r.stdout + r.stderr if capture else r


def tsec(t):
    """'1:02:03.5' / '62.5' / 62.5 -> seconds"""
    if isinstance(t, (int, float)):
        return float(t)
    s = 0.0
    for part in str(t).split(":"):
        s = s * 60 + float(part)
    return s


def fmt_ts(s, srt=True):
    h, m = int(s // 3600), int(s % 3600 // 60)
    sec = s % 60
    if srt:
        return f"{h:02d}:{m:02d}:{int(sec):02d},{int(round((sec % 1) * 1000)) % 1000:03d}"
    return f"{h}:{m:02d}:{sec:05.2f}"  # ASS


def load_batch():
    return json.loads((ROOT / "batch.json").read_text(encoding="utf-8"))


def get_rec(cid):
    for r in load_batch()["clips"]:
        if r["id"] == cid:
            return r
    raise SystemExit(f"no record {cid} in batch.json")


def probe(path):
    out = run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path], capture=True)
    return json.loads(out[out.index("{"):])


# ---------------------------------------------------------------- fetch
def fetch(rec):
    d = WORK / rec["id"]; d.mkdir(parents=True, exist_ok=True)
    src = d / "source.mp4"
    if src.exists():
        print("  source exists, skipping fetch"); return src
    if rec.get("source_file"):                       # local file supplied by user
        shutil.copy(rec["source_file"], src); return src
    pad = CFG["fetch_padding_sec"]
    a, b = max(0, tsec(rec["in"]) - pad), tsec(rec["out"]) + pad
    cmd = ["yt-dlp", "-f", "bv*[height<=1080]+ba/b[height<=1080]/b", "--merge-output-format", "mp4",
           "--download-sections", f"*{a:.2f}-{b:.2f}", "--force-keyframes-at-cuts",
           "-o", str(d / "source.%(ext)s"), rec["source_url"]]
    run(cmd)
    rec_meta = {"fetched_at": now(), "section_start_in_source": a, "section_end_in_source": b}
    (d / "fetch.json").write_text(json.dumps(rec_meta, indent=2))
    return src


# ---------------------------------------------------------------- cut (trim to in/out, drop dead air)
def cut(rec):
    d = WORK / rec["id"]; src = d / "source.mp4"; dst = d / "edit.mp4"
    meta = json.loads((d / "fetch.json").read_text()) if (d / "fetch.json").exists() else {"section_start_in_source": 0}
    off = meta["section_start_in_source"]
    clip_in, clip_out = tsec(rec["in"]) - off, tsec(rec["out"]) - off
    # "keep" = list of [start,end] in ORIGINAL source time; default = whole in/out
    keeps = rec.get("keep") or [[rec["in"], rec["out"]]]
    keeps = [(tsec(a) - off, tsec(b) - off) for a, b in keeps]
    keeps = [(max(a, clip_in), min(b, clip_out)) for a, b in keeps if b > a]
    if rec.get("tighten_silence") and not rec.get("keep"):
        keeps = tighten(src, clip_in, clip_out, float(rec["tighten_silence"]))
        print(f"  tightened silences > {rec['tighten_silence']}s -> {len(keeps)} segments")
    (d / "keeps_in_fetched_file.json").write_text(json.dumps(keeps))
    parts, labels = [], []
    for i, (a, b) in enumerate(keeps):
        parts.append(f"[0:v]trim={a:.3f}:{b:.3f},setpts=PTS-STARTPTS[v{i}];"
                     f"[0:a]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS,"
                     f"afade=t=in:d=0.02,afade=t=out:st={max(0,b-a-0.03):.3f}:d=0.03[a{i}];")
        labels.append(f"[v{i}][a{i}]")
    fg = "".join(parts) + "".join(labels) + f"concat=n={len(keeps)}:v=1:a=1[v][a]"
    run(["ffmpeg", "-y", "-v", "error", "-i", src, "-filter_complex", fg, "-map", "[v]", "-map", "[a]",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-c:a", "pcm_s16le", "-ar", "48000",
         d / "edit.mov"])
    (d / "edit.mov").replace(dst.with_suffix(".mov"))
    return dst.with_suffix(".mov")


def tighten(src, a, b, min_gap, keep_pad=0.3):
    """Shrink silences longer than min_gap (sec) to ~2*keep_pad. Only use on talk-driven moments:
    a pause that IS the joke should be protected by giving explicit 'keep' segments instead."""
    out = run(["ffmpeg", "-hide_banner", "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", src, "-af",
               f"silencedetect=n=-35dB:d={min_gap}", "-f", "null", "-"], capture=True)
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", out)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", out)]
    keeps, cur = [], a
    for s, e in zip(starts, ends):
        s, e = a + s, a + e
        if s + keep_pad < e - keep_pad:
            keeps.append((cur, s + keep_pad)); cur = e - keep_pad
    keeps.append((cur, b))
    return [(x, y) for x, y in keeps if y - x > 0.1]


# ---------------------------------------------------------------- transcribe
def extract_wav(video, wav):
    run(["ffmpeg", "-y", "-v", "error", "-i", video, "-ac", "1", "-ar", "16000", wav])


def transcribe_words(video, work_dir):
    """Return [{'w': str, 's': float, 'e': float}] using faster-whisper if present, else sherpa-onnx whisper."""
    wav = Path(work_dir) / "audio16k.wav"; extract_wav(video, wav)
    if os.environ.get("CLIPPER_ASR") == "sherpa":
        return sherpa_words(wav)
    try:
        from faster_whisper import WhisperModel
        import soundfile as sf
        model = WhisperModel(CFG["whisper_model"], device="auto", compute_type="int8")
        audio, _ = sf.read(str(wav), dtype="float32")   # in-memory: avoids PyAV version issues
        words = None
        for vad in (False, True):   # some clips crash word alignment without VAD; retry with it
            try:
                segs, _ = model.transcribe(audio, word_timestamps=True, vad_filter=vad,
                                           initial_prompt=CFG.get("vocab_prompt", ""))
                words = [{"w": w.word.strip(), "s": w.start, "e": w.end} for s in segs for w in s.words]
                break
            except IndexError:
                continue
        if words is None: raise RuntimeError("whisper alignment failed")
        print(f"  faster-whisper: {len(words)} words"); return words
    except Exception as ex:
        print(f"  faster-whisper unavailable ({type(ex).__name__}); using sherpa-onnx fallback")
    return sherpa_words(wav)


def sherpa_words(wav):
    import sherpa_onnx, wave, numpy as np
    m = Path(CFG["sherpa_whisper_dir"]).expanduser()
    if not m.is_absolute():
        m = ROOT / m
    pre = next(m.glob("*-encoder.int8.onnx")).name.replace("-encoder.int8.onnx", "")
    rec = sherpa_onnx.OfflineRecognizer.from_whisper(
        encoder=str(m / f"{pre}-encoder.int8.onnx"), decoder=str(m / f"{pre}-decoder.int8.onnx"),
        tokens=str(m / f"{pre}-tokens.txt"), num_threads=os.cpu_count() or 2,
        enable_token_timestamps=True)
    with wave.open(str(wav)) as f:
        audio = np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    sr, words = 16000, []
    # energy-based speech regions (so proportional word timing stays local); max 25 s per region
    hop = 480; fr = np.sqrt(np.convolve(audio ** 2, np.ones(hop) / hop, "same")[::hop] + 1e-12)
    db = 20 * np.log10(fr); thr = max(np.percentile(db, 95) - 28, -50)
    voiced = db > thr; regions, i = [], 0
    while i < len(voiced):
        if voiced[i]:
            j = i
            while j < len(voiced) and (voiced[j:j + 12].any()) and (j - i) * hop < 25 * sr: j += 1
            regions.append((max(0, i * hop - 2400), min(len(audio), j * hop + 2400))); i = j
        else: i += 1
    for pos, end in regions:
        chunk = audio[pos:end]
        st = rec.create_stream(); st.accept_waveform(sr, chunk); rec.decode_stream(st)
        r = st.result; base = pos / sr; dur = len(chunk) / sr
        toks, ts = list(r.tokens), list(r.timestamps)
        if toks and len(ts) == len(toks):
            cur = None
            for i, (tk, t) in enumerate(zip(toks, ts)):
                if tk.startswith(" ") or cur is None:
                    if cur: words.append(cur)
                    cur = {"w": tk.strip(), "s": base + t, "e": base + t + 0.25}
                else:
                    cur["w"] += tk
                if i + 1 < len(ts):
                    cur["e"] = base + ts[i + 1]
            if cur:
                cur["e"] = min(cur["e"], base + dur); words.append(cur)
        elif r.text.strip():   # no timestamps: spread proportionally by length
            ws = r.text.split(); tot = sum(len(w) + 1 for w in ws); t = base
            for w in ws:
                d = dur * (len(w) + 1) / tot; words.append({"w": w, "s": t, "e": t + d}); t += d
    words = [w for w in words if w["w"] and not re.fullmatch(r"\W*", w["w"]) or w["w"] in "?!"]
    for a, b in zip(words, words[1:]):           # tidy overlaps / long tails
        a["e"] = min(a["e"], b["s"], a["s"] + 1.2)
    print(f"  sherpa-onnx whisper: {len(words)} words")
    return words


WEAK = {"the","a","an","to","is","of","and","my","your","i'm","in","on","for","at","that","this","be","was","are"}


def group_captions(words):
    c = CFG["captions"]; chunks, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        text = " ".join(x["w"] for x in cur)
        nxt = words[i + 1] if i + 1 < len(words) else None
        gap = (nxt["s"] - w["e"]) if nxt else 9
        weak = w["w"].lower().strip(",") in WEAK and gap < 0.45 and len(cur) < c["max_words"] + 2 and nxt
        if weak: continue
        if (len(cur) >= c["max_words"] or len(text) >= c["max_chars"] or gap > 0.45
                or re.search(r"[.?!]$", w["w"]) or (cur[-1]["e"] - cur[0]["s"]) > 2.2 or not nxt):
            chunks.append({"s": cur[0]["s"], "e": cur[-1]["e"], "text": text}); cur = []
    for a, b in zip(chunks, chunks[1:]):          # hold caption until next one if gap is short
        if b["s"] - a["e"] < 0.35: a["e"] = b["s"]
    return chunks


def censor(text):
    """Mask slurs and swears in burned-in captions / SRT (audio is untouched). Also fixes ASR spacing glitches."""
    text = re.sub(r"(\w) '(\w)", r"\1'\2", text)      # y 'all -> y'all
    text = re.sub(r"(\w) -(\w)", r"\1-\2", text)      # slow -ass -> slow-ass
    for pat, rep in CFG.get("censor", {}).items():
        text = re.sub(pat, lambda m: m.group(0)[0] + rep, text, flags=re.I)
    return text


def write_srt(chunks, path):
    with open(path, "w", encoding="utf-8") as f:
        for i, c in enumerate(chunks, 1):
            f.write(f"{i}\n{fmt_ts(c['s'])} --> {fmt_ts(c['e'])}\n{censor(c['text'])}\n\n")


def read_srt(path):
    out = []
    for block in re.split(r"\n\s*\n", Path(path).read_text(encoding="utf-8").strip()):
        lines = block.strip().splitlines()
        if len(lines) < 3: continue
        a, b = [tsec(x.replace(",", ".")) for x in lines[1].split(" --> ")]
        out.append({"s": a, "e": b, "text": " ".join(lines[2:])})
    return out


def transcribe(rec):
    d = WORK / rec["id"]
    words = transcribe_words(d / "edit.mov", d)
    (d / "words.json").write_text(json.dumps(words, indent=1))
    srt = d / "captions.srt"
    if srt.exists() and (d / ".captions_edited").exists():
        print("  captions.srt was hand-edited; keeping it (delete .captions_edited to regenerate)")
    else:
        write_srt(group_captions(words), srt)
    return srt


# ---------------------------------------------------------------- render
def fit_box(box, sw, sh, aspect):
    """box = [x,y,w,h] as fractions of source; grow/shrink around centre to target aspect (w/h), clamp to frame."""
    x, y, w, h = box[0] * sw, box[1] * sh, box[2] * sw, box[3] * sh
    cx, cy = x + w / 2, y + h / 2
    if w / h > aspect: w = h * aspect
    else: h = w / aspect
    w, h = min(w, sw), min(h, sh)
    if w / h > aspect: w = h * aspect
    else: h = w / aspect
    x = min(max(0, cx - w / 2), sw - w); y = min(max(0, cy - h / 2), sh - h)
    ev = lambda v: int(v) // 2 * 2
    return ev(w), ev(h), ev(x), ev(y)


def build_video_filter(rec, sw, sh):
    L = rec.get("layout", {"mode": "fill"}); mode = L.get("mode", "fill")
    if mode == "split":
        top_h = CFG["layout"]["split_top_h"]; bot_h = H - top_h
        fw, fh, fx, fy = fit_box(L["facecam"], sw, sh, W / top_h)
        gw, gh, gx, gy = fit_box(L.get("game", [0, 0, 1, 1]), sw, sh, W / bot_h)
        return (f"[0:v]split=2[c][g];[c]crop={fw}:{fh}:{fx}:{fy},scale={W}:{top_h}[ct];"
                f"[g]crop={gw}:{gh}:{gx}:{gy},scale={W}:{bot_h}[gb];[ct][gb]vstack[base]")
    if mode == "stack":  # facecam on top, wide gameplay band in the middle, blurred fill behind
        if not L.get("facecam"):   # no facecam: bigger gameplay band
            S = {**CFG["layout"]["stack_nocam"], **L.get("band", {})}
            gw, gh, gx, gy = fit_box(L.get("game", [0, 0, 1, 1]), sw, sh, W / S["game_h"])
            return (f"[0:v]split=2[bg][g];[bg]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                    f"boxblur=25:2,eq=brightness=-0.25[b];[g]crop={gw}:{gh}:{gx}:{gy},scale={W}:{S['game_h']}[gs];"
                    f"[b][gs]overlay=0:{S['game_y']}[base]")
        S = CFG["layout"]["stack"]; fc = L["facecam"]
        fw, fh, fx, fy = fit_box(fc, sw, sh, (fc[2] * sw) / (fc[3] * sh))
        cam_w = min(W, int(S["cam_h"] * fw / fh) // 2 * 2)
        gw, gh, gx, gy = fit_box(L.get("game", [0, 0, 1, 1]), sw, sh, W / S["game_h"])
        # blur the streamer's own facecam (already shown above) + any extra boxes (chat, nudity) inside the game view
        blurs = ([{"box": fc}] if L.get("blur_cam", True) else []) + L.get("blur", [])
        chain, prev = "", "[g]"
        for i, b in enumerate(blurs):
            x, y, w_, h_ = b["box"]
            bx, by = int(x * sw) // 2 * 2, int(y * sh) // 2 * 2
            bw, bh = max(16, int(w_ * sw) // 2 * 2), max(16, int(h_ * sh) // 2 * 2)
            bw, bh = min(bw, sw - bx), min(bh, sh - by)
            en = f":enable='between(t,{b['t'][0]},{b['t'][1]})'" if b.get("t") else ""
            rad = max(2, min(28, min(bw, bh) // 4 - 1))
            chain += (f"{prev}split[ga{i}][gb{i}];[gb{i}]crop={bw}:{bh}:{bx}:{by},boxblur={rad}:4[gbb{i}];"
                      f"[ga{i}][gbb{i}]overlay={bx}:{by}{en}[gx{i}];")
            prev = f"[gx{i}]"
        return (f"[0:v]split=3[bg][c][g];[bg]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                f"boxblur=25:2,eq=brightness=-0.25[b];[c]crop={fw}:{fh}:{fx}:{fy},scale={cam_w}:{S['cam_h']}[cs];"
                f"{chain}{prev}crop={gw}:{gh}:{gx}:{gy},scale={W}:{S['game_h']}[gs];"
                f"[b][cs]overlay=({W}-w)/2:{S['cam_y']}[t];[t][gs]overlay=0:{S['game_y']}[base]")
    if mode == "fit":   # whole 16:9 frame centred, blurred fill behind
        return (f"[0:v]split=2[bg][fg];[bg]scale={W}:{H}:force_original_aspect_ratio=increase,"
                f"crop={W}:{H},boxblur=30:2,eq=brightness=-0.15[b];"
                f"[fg]scale={W}:-2[f];[b][f]overlay=(W-w)/2:(H-h)/2[base]")
    # fill: crop a 9:16 window; x centre = fill_x (fraction), optional zoom box
    box = L.get("box") or [L.get("fill_x", 0.5) - 0.25, 0, 0.5, 1]
    cw, ch, cx, cy = fit_box(box, sw, sh, W / H)
    return f"[0:v]crop={cw}:{ch}:{cx}:{cy},scale={W}:{H}[base]"


def ass_escape(t):
    return t.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", "\\N")


def wrap(text, maxc):
    """Greedy wrap, then rebalance 2-line results so lines are similar length."""
    if len(text) > maxc and len(text) <= maxc * 2:
        ws = text.split(); best = None
        for i in range(1, len(ws)):
            a, b = " ".join(ws[:i]), " ".join(ws[i:])
            if len(a) <= maxc and len(b) <= maxc:
                sc = abs(len(a) - len(b))
                if best is None or sc < best[0]: best = (sc, [a, b])
        if best: return best[1]
    words, lines, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > maxc:
            lines.append(cur); cur = w
        else:
            cur = (cur + " " + w).strip()
    lines.append(cur)
    if len(lines) == 2 and len(lines[1]) < 4 and len(text) <= maxc + 4:
        return [text]
    return lines


def build_ass(rec, chunks, dur, path):
    c, hcfg = CFG["captions"], CFG["header"]
    mode = rec.get("layout", {}).get("mode", "fill")
    halign = 5 if mode in ("split", "stack") else 8
    cap_y = c["baseline_y"]
    if mode == "stack":   # text lives in its own bands: never over gameplay or facecam
        S = {**CFG["layout"]["stack" if rec.get("layout", {}).get("facecam") else "stack_nocam"],
             **rec.get("layout", {}).get("band", {})}
        hy, cap_y = S["header_y"], S["caption_y"]
    else:
        hy = CFG["layout"]["split_top_h"] if mode == "split" else hcfg["y_fill"]
    yellow = "&H0000E5FF&"
    emph = {e.lower().strip(".,!?") for e in rec.get("emphasis", [])}
    lines = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 2",
             "ScaledBorderAndShadow: yes", "", "[V4+ Styles]",
             "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
             f"Style: Header,{hcfg['font']},{hcfg['size']},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,1,0,3,{hcfg['box_pad']},0,{halign},150,150,0,1",
             f"Style: Cap,{c['font']},{c['size']},&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,0,0,0,0,100,100,1,0,1,{c['outline']},3,2,150,150,0,1",
             "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    header = rec.get("header", "").upper()
    if header:
        hl = "\\N".join(ass_escape(l) for l in wrap(header, hcfg["max_chars_per_line"]))
        hend = min(dur, float(rec.get("header_until", dur)))   # hide header before a payoff it would cover
        lines.append(f"Dialogue: 1,{fmt_ts(0,False)},{fmt_ts(hend,False)},Header,,0,0,0,,{{\\pos({W//2},{hy})}}{hl}")
    split_chunks = []
    for ch in chunks:
        pieces = wrap(censor(ch["text"]), c["max_chars_per_line"])
        tot = sum(len(p) for p in pieces) or 1; t = ch["s"]
        for p in pieces:
            d = (ch["e"] - ch["s"]) * len(p) / tot
            split_chunks.append({"s": t, "e": t + d, "text": p}); t += d
    for ch in split_chunks:
        parts = []
        for ln in [ch["text"]]:
            ws = []
            for w in ln.split():
                ew = ass_escape(w.upper() if c.get("uppercase") else w)
                ws.append(f"{{\\c{yellow}}}{ew}{{\\c&H00FFFFFF&}}" if w.lower().strip(".,!?\"'") in emph else ew)
            parts.append(" ".join(ws))
        txt = "\\N".join(parts)
        pop = "{\\fscx92\\fscy92\\t(0,80,\\fscx100\\fscy100)}" if c.get("pop") else ""
        lines.append(f"Dialogue: 0,{fmt_ts(ch['s'],False)},{fmt_ts(min(ch['e'],dur),False)},Cap,,0,0,0,,"
                     f"{{\\pos({W//2},{cap_y})}}{pop}{txt}")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


_LN = {}


def loudnorm_filter(inp, cwd):
    """Two-pass loudnorm: measure first so short/quiet clips actually reach the target."""
    a = CFG["audio"]; key = (str(cwd), str(inp))
    if key not in _LN:
        m = run(["ffmpeg", "-hide_banner", "-i", inp, "-af",
                 f"loudnorm=I={a['lufs']}:TP={a['true_peak']}:LRA=11:print_format=json", "-f", "null", "-"],
                cwd=cwd, capture=True)
        j = json.loads(m[m.rindex("{"):m.rindex("}") + 1])
        _LN[key] = (f"loudnorm=I={a['lufs']}:TP={a['true_peak']}:LRA=11:measured_I={j['input_i']}:"
                    f"measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:"
                    f"offset={j['target_offset']}:linear=true,alimiter=limit=0.74:level=false,aresample=48000")
    return _LN[key]


def encode(inp, vf, out, cwd):
    af = loudnorm_filter(inp, cwd)
    run(["ffmpeg", "-y", "-v", "error", "-i", inp, "-filter_complex", vf + f";[0:a]{af}[aout]",
         "-map", "[vout]", "-map", "[aout]", "-r", "30", "-c:v", "libx264", "-preset", CFG["x264_preset"],
         "-crf", str(CFG["crf"]), "-profile:v", "high", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out], cwd=cwd)


def render(rec):
    d = WORK / rec["id"]; o = OUT / rec["id"]; o.mkdir(parents=True, exist_ok=True)
    src = d / "edit.mov"; info = probe(src)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    sw, sh, dur = int(v["width"]), int(v["height"]), float(info["format"]["duration"])
    base = build_video_filter(rec, sw, sh)
    chunks = read_srt(d / "captions.srt")
    build_ass(rec, chunks, dur, d / "overlay.ass")
    fonts = os.path.relpath(ROOT / "fonts", d).replace("\\", "/")
    encode("edit.mov", base + ";[base]null[vout]", os.path.relpath(o / f"{rec['id']}_clean.mp4", d), d)
    encode("edit.mov", base + f";[base]ass=overlay.ass:fontsdir={fonts}[vout]",
           os.path.relpath(o / f"{rec['id']}_captioned.mp4", d), d)
    shutil.copy(d / "captions.srt", o / f"{rec['id']}.srt")
    write_posting(rec, o)


def write_posting(rec, o):
    p = rec.get("posting", {})
    txt = [f"HEADER (used): {rec.get('header','')}",
           *[f"HEADER alt {i}: {h}" for i, h in enumerate(rec.get("header_alts", []), 1)],
           f"COVER TEXT: {p.get('cover_text','')}", "",
           "TIKTOK CAPTION:", p.get("tiktok", ""), " ".join(p.get("hashtags_tiktok", [])), "",
           "INSTAGRAM CAPTION:", p.get("instagram", ""), " ".join(p.get("hashtags_instagram", [])), "",
           f"HOOK: {p.get('hook_reason','')}", "",
           f"SOURCE: {rec.get('source_url','')}", f"IN/OUT: {rec.get('in')} -> {rec.get('out')}",
           f"KEEP SEGMENTS: {rec.get('keep')}",
           f"STREAMER: {rec.get('streamer')}  GAME: {rec.get('game')}  BROADCAST: {rec.get('broadcast_date')}  UPLOAD: {rec.get('upload_date')}"]
    warn = posting_warnings(rec)
    if warn: txt += ["", "WARNINGS:"] + warn; print("  posting warnings:", warn)
    (o / "posting.txt").write_text("\n".join(txt), encoding="utf-8")


def posting_warnings(rec):
    """Limits checked Nov 2026: Instagram hard cap 5 hashtags per post/Reel (since Dec 2025).
    TikTok caption: sources disagree (2,200 vs 4,000 chars) -> we enforce the safer 2,200. 3-5 tags each by our own rule."""
    p, w = rec.get("posting", {}), []
    for plat, cap in (("tiktok", 5), ("instagram", 5)):
        n = len(p.get(f"hashtags_{plat}", []))
        if not 3 <= n <= cap: w.append(f"{plat}: {n} hashtags (want 3-5)")
    if len(p.get("tiktok", "") + " " + " ".join(p.get("hashtags_tiktok", []))) > 2200: w.append("tiktok caption > 2200 chars")
    if len(p.get("instagram", "") + " " + " ".join(p.get("hashtags_instagram", []))) > 2200: w.append("instagram caption > 2200 chars")
    if not 4 <= len(rec.get("header", "").split()) <= 9: w.append("header not 4-9 words")
    return w


# ---------------------------------------------------------------- QC
def qc(rec):
    d = WORK / rec["id"]; o = OUT / rec["id"]; qd = o / "qc"; qd.mkdir(exist_ok=True)
    res, problems = {"checked_at": now()}, []
    for kind in ("captioned", "clean"):
        f = o / f"{rec['id']}_{kind}.mp4"; info = probe(f)
        v = next(s for s in info["streams"] if s["codec_type"] == "video")
        a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
        res[kind] = {"w": v["width"], "h": v["height"], "vcodec": v["codec_name"],
                     "acodec": a and a["codec_name"], "duration": round(float(info["format"]["duration"]), 2)}
        if (v["width"], v["height"], v["codec_name"]) != (W, H, "h264") or not a or a["codec_name"] != "aac":
            problems.append(f"{kind}: wrong format {res[kind]}")
    cap = o / f"{rec['id']}_captioned.mp4"
    m = run(["ffmpeg", "-hide_banner", "-i", cap, "-af", "loudnorm=print_format=json", "-f", "null", "-"], capture=True)
    j = json.loads(m[m.rindex("{"):m.rindex("}") + 1])
    res["loudness_lufs"], res["true_peak_db"] = float(j["input_i"]), float(j["input_tp"])
    if res["true_peak_db"] > -0.5: problems.append(f"audio peak too hot ({res['true_peak_db']} dBTP)")
    if not -17 <= res["loudness_lufs"] <= -11: problems.append(f"loudness off ({res['loudness_lufs']} LUFS)")
    dur = res["captioned"]["duration"]
    if dur < 8: problems.append("very short")
    # contact sheet with platform UI danger zones overlaid (red)
    times = [0.2, dur * 0.25, dur * 0.5, dur * 0.75, max(0, dur - 0.4)]
    for i, t in enumerate(times):
        run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", cap, "-frames:v", "1", "-vf",
             "drawbox=0:0:1080:" + str(CFG["safe"]["top"]) + ":red@0.35:fill,"
             f"drawbox=0:{H-CFG['safe']['bottom']}:1080:{CFG['safe']['bottom']}:red@0.35:fill,"
             f"drawbox={W-CFG['safe']['right']}:0:{CFG['safe']['right']}:{H}:red@0.35:fill,scale=360:640",
             qd / f"f{i}.png"])
    run(["ffmpeg", "-y", "-v", "error", "-i", qd / "f%d.png", "-vf", "tile=5x1:padding=6", qd / "contact.png"])
    # re-listen: transcribe rendered audio and compare against captions
    heard = " ".join(w["w"] for w in transcribe_words(cap, qd)).lower()
    said = " ".join(c["text"] for c in read_srt(d / "captions.srt")).lower()
    norm = lambda s: [w for w in re.sub(r"[^a-z0-9' ]", " ", s).split() if w]
    hw, sw_ = set(norm(heard)), norm(said)
    overlap = sum(1 for w in sw_ if w in hw) / max(1, len(sw_))
    res["caption_vs_rerender_word_overlap"] = round(overlap, 2)
    res["heard_in_render"] = heard
    if overlap < 0.75: problems.append(f"captions differ from rendered audio (overlap {overlap:.0%}) - listen and fix captions.srt")
    first = read_srt(d / "captions.srt")[:1]
    if first and first[0]["s"] > 1.5: problems.append("first caption starts late - opening may be dead air")
    # boundary checks (taste.md: never start mid-sentence, never cut mid-word / before the reaction)
    wj = d / "words.json"
    if wj.exists():
        ws = json.loads(wj.read_text())
        if ws:
            if ws[0]["s"] < 0.15: problems.append(f"STARTS MID-SPEECH: first word '{ws[0]['w']}' at {ws[0]['s']:.2f}s - check the lead-in")
            if dur - ws[-1]["e"] < 0.35: problems.append(f"ENDS MID-SPEECH: last word '{ws[-1]['w']}' ends {dur - ws[-1]['e']:.2f}s before the end")
        res["first_words"] = " ".join(w["w"] for w in ws[:8]); res["last_words"] = " ".join(w["w"] for w in ws[-10:])
    if not rec.get("screen", {}).get("setup") or not rec.get("screen", {}).get("payoff"):
        problems.append("NO SCREEN CARD: setup/payoff not written down - should not have been rendered")
    res["problems"], res["auto_pass"] = problems, not problems
    res["note"] = "Automated checks only. Look at qc/contact.png and watch the export before posting."
    (o / "qc.json").write_text(json.dumps(res, indent=2))
    print("  QC:", "PASS" if not problems else problems)
    return res


# ---------------------------------------------------------------- ledger / discovery / preview
def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def canon(url):
    return re.sub(r"[?#].*$", "", (url or "").lower().replace("www.", "").rstrip("/"))


def ledger_rows():
    p = ROOT / "ledger.csv"
    return list(csv.DictReader(open(p, encoding="utf-8"))) if p.exists() else []


def ledger_check(rec):
    for r in ledger_rows():
        if r["id"] == rec["id"]: continue
        same_src = canon(r["source_url"]) == canon(rec.get("source_url"))
        same_day = r["streamer"].lower() == rec.get("streamer", "").lower() and r["broadcast_date"] == rec.get("broadcast_date")
        if same_src and r.get("in") and rec.get("in"):
            if tsec(r["in"]) < tsec(rec["out"]) and tsec(rec["in"]) < tsec(r["out"]):
                return f"DUPLICATE of {r['id']} (overlapping time in same source)"
        if same_day and r.get("moment_key") and r["moment_key"] == rec.get("moment_key"):
            return f"DUPLICATE of {r['id']} (same moment_key)"
    return None


def ledger_add(rec, status):
    p = ROOT / "ledger.csv"; old = {r["id"]: r for r in ledger_rows()}
    rows = [r for r in old.values() if r["id"] != rec["id"]]
    rows.append({**old.get(rec["id"], {}), "id": rec["id"], "streamer": rec.get("streamer", ""), "broadcast_date": rec.get("broadcast_date", ""),
                 "moment_key": rec.get("moment_key", ""), "source_url": rec.get("source_url", ""),
                 "in": rec.get("in", ""), "out": rec.get("out", ""), "status": status, "updated": now()})
    with open(p, "w", newline="", encoding="utf-8") as f:
        fields = list(dict.fromkeys(k for r in rows for k in r))   # keep extra columns (posted_slot_pt, views_48h, ...)
        w = csv.DictWriter(f, fieldnames=fields, restval=""); w.writeheader(); w.writerows(rows)


def discover():
    ch = json.loads((ROOT / "channels.json").read_text())
    found = []
    for s in ch["streamers"]:
        for url in s["urls"]:
            try:
                out = run(["yt-dlp", "--flat-playlist", "--playlist-end", "15", "-J", url], capture=True)
                data = json.loads(out[out.index("{"):])
                for e in data.get("entries") or []:
                    found.append({"streamer": s["name"], "title": e.get("title"), "url": e.get("url") or e.get("webpage_url"),
                                  "views": e.get("view_count"), "duration": e.get("duration"),
                                  "upload": e.get("upload_date") or e.get("timestamp"), "observed_at": now(), "from": url})
            except Exception as ex:
                print(f"  ! {url}: {ex}")
    (ROOT / "discovered.json").write_text(json.dumps(found, indent=1))
    print(f"{len(found)} items -> discovered.json (titles/metrics only: footage must still be watched before selecting)")


def watch(argv):
    """Live clip radar: poll channels' newest clips, track view velocity, auto-grab risers.
    python clipper.py watch [minutes_between_polls=5] [hours_to_run=8]
    Writes radar.json (every clip seen + view history) and radar.html (hot list). Only runs while this window stays open."""
    import time
    every = float(argv[0]) if argv else 5; hours = float(argv[1]) if len(argv) > 1 else 8
    R = CFG.get("radar", {"min_views": 300, "min_views_per_min": 15, "max_downloads_per_poll": 3})
    path = ROOT / "radar.json"; radar = json.loads(path.read_text()) if path.exists() else {}
    srcdir = ROOT / "sources"; srcdir.mkdir(exist_ok=True)
    ch = json.loads((ROOT / "channels.json").read_text())
    urls = [(s["name"], u) for s in ch["streamers"] for u in s["urls"] if "youtube.com" not in u]
    end = time.time() + hours * 3600
    while time.time() < end:
        t = time.time(); got = 0
        for name, url in urls:
            try:
                out = subprocess.run(["yt-dlp", "--flat-playlist", "--playlist-end", "20", "-J", url],
                                     capture_output=True, text=True, timeout=120).stdout
                entries = json.loads(out).get("entries") or []
            except Exception as ex:
                print("  !", name, ex); continue
            for e in entries:
                u = e.get("url") or e.get("webpage_url"); v = e.get("view_count") or 0
                r = radar.setdefault(u, {"streamer": name, "title": e.get("title"), "duration": e.get("duration"),
                                         "first_seen": t, "history": []})
                r["history"].append([round(t), v])
                mins = max(1.0, (t - r["first_seen"]) / 60)
                first_v = r["history"][0][1]
                r["views"] = v; r["velocity"] = round((v - first_v) / mins, 1) if len(r["history"]) > 1 else None
                hot = v >= R["min_views"] and (r["velocity"] is None or r["velocity"] >= R["min_views_per_min"])
                if hot and not r.get("downloaded") and got < R["max_downloads_per_poll"] and not ledger_has_url(u):
                    safe = re.sub(r"\W+", "_", f"{name}_{e.get('title') or 'clip'}")[:60]
                    f = srcdir / f"{safe}.mp4"
                    try:
                        subprocess.run(["yt-dlp", "-q", "--no-warnings", "-f", "best[height<=1080]/best", "-o", str(f), u],
                                       timeout=300, check=True)
                        r["downloaded"] = str(f); got += 1
                        print(f"  HOT {name}: {r['title']!r} {v} views -> {f.name}")
                    except Exception as ex:
                        print("  ! download", u, ex)
        path.write_text(json.dumps(radar, indent=1))
        rows = sorted((r for r in radar.values() if r.get("views")), key=lambda r: (-(r.get("velocity") or 0), -r["views"]))[:40]
        (ROOT / "radar.html").write_text("<meta charset=utf-8><meta http-equiv=refresh content=60><title>Clip radar</title>"
            "<style>body{font:14px system-ui;background:#111;color:#eee}td{padding:4px 8px}a{color:#8cf}</style><h2>Clip radar — "
            + now() + "</h2><table><tr><th>views</th><th>views/min</th><th>streamer</th><th>title</th><th>grabbed</th></tr>"
            + "".join(f"<tr><td>{r['views']}</td><td>{r.get('velocity') or ''}</td><td>{html.escape(r['streamer'])}</td>"
                      f"<td>{html.escape(str(r['title']))}</td><td>{'yes' if r.get('downloaded') else ''}</td></tr>" for r in rows)
            + "</table>", encoding="utf-8")
        print(f"[{now()}] polled {len(urls)} channels, {len(radar)} clips tracked, {got} grabbed; next poll in {every} min")
        time.sleep(max(0, every * 60 - (time.time() - t)))


def ledger_has_url(u):
    return any(canon(r["source_url"]) == canon(u) for r in ledger_rows())


def preview():
    b = load_batch(); cards = []
    for r in b["clips"]:
        o = OUT / r["id"]; p = r.get("posting", {})
        qcj = json.loads((o / "qc.json").read_text()) if (o / "qc.json").exists() else None
        has = (o / f"{r['id']}_captioned.mp4").exists()
        esc = lambda s: html.escape(str(s or ""))
        def copybox(label, text):
            return (f"<div class=cb><div class=lbl>{label}<button onclick=\"navigator.clipboard.writeText("
                    f"this.parentNode.nextElementSibling.innerText)\">Copy</button></div><pre>{esc(text)}</pre></div>")
        vid = (f"<video src='{r['id']}/{r['id']}_captioned.mp4' controls playsinline preload=metadata></video>"
               if has else "<div class=novid>Not rendered yet</div>")
        q = ("<span class=ok>auto-QC pass</span>" if qcj and qcj["auto_pass"] else
             f"<span class=bad>QC: {esc('; '.join(qcj['problems']))}</span>" if qcj else "<span>no QC yet</span>")
        cards.append(f"""<section><div class=v>{vid}</div><div class=t>
<h2>{esc(r.get('header'))}</h2><p class=meta>{esc(r.get('streamer'))} · {esc(r.get('game'))} · broadcast {esc(r.get('broadcast_date'))} · status <b>{esc(r.get('status'))}</b> · {q}</p>
<p>Alt headers: {esc(' / '.join(r.get('header_alts', [])))}</p><p>Cover: <b>{esc(p.get('cover_text'))}</b> · Hook: {esc(p.get('hook_reason'))}</p>
{copybox('TikTok', (p.get('tiktok','') + chr(10) + ' '.join(p.get('hashtags_tiktok', []))).strip())}
{copybox('Instagram', (p.get('instagram','') + chr(10) + ' '.join(p.get('hashtags_instagram', []))).strip())}
<p class=meta>Source: <a href="{esc(r.get('source_url'))}">{esc(r.get('source_url'))}</a> [{esc(r.get('in'))} → {esc(r.get('out'))}]
{' · <a href="'+r['id']+'/'+r['id']+'_clean.mp4">clean MP4</a> · <a href="'+r['id']+'/'+r['id']+'.srt">SRT</a>' if has else ''}</p></div></section>""")
    page = f"""<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Clip batch preview</title><style>body{{font:15px system-ui;background:#111;color:#eee;margin:0;padding:20px}}
section{{display:flex;gap:20px;flex-wrap:wrap;background:#1c1c1c;border-radius:12px;padding:16px;margin:0 0 18px}}
video{{width:270px;height:480px;background:#000;border-radius:8px}}.novid{{width:270px;height:480px;display:grid;place-items:center;background:#000;color:#777;border-radius:8px}}
.t{{flex:1;min-width:280px}}h2{{margin:0 0 6px}}.meta{{color:#aaa;font-size:13px}}a{{color:#8cf}}
.cb pre{{white-space:pre-wrap;background:#0b0b0b;padding:10px;border-radius:6px;margin:4px 0 10px}}.lbl{{font-weight:600}}
button{{margin-left:8px;font-size:12px}}.ok{{color:#6d6}}.bad{{color:#f77}}</style>
<h1>Clip batch — {esc_now()}</h1><p class=meta>Nothing here is posted automatically.</p>{''.join(cards)}"""
    OUT.mkdir(exist_ok=True); (OUT / "index.html").write_text(page, encoding="utf-8")
    print("  preview ->", OUT / "index.html")


def esc_now():
    return now()


STEPS = {"fetch": fetch, "cut": cut, "transcribe": transcribe, "render": render, "qc": qc}


def run_clip(rec):
    print(f"\n=== {rec['id']} ===")
    dup = ledger_check(rec)
    if dup and not rec.get("allow_duplicate"):
        print("  SKIP:", dup); return
    for name in ("fetch", "cut", "transcribe", "render", "qc"):
        print(f"- {name}"); STEPS[name](rec)
    ledger_add(rec, "rendered")


def main(argv):
    if not argv: print(__doc__); return
    cmd = argv[0]
    if cmd == "batch":
        recs = load_batch()["clips"]
        ids = argv[1:] or [r["id"] for r in recs if r.get("status") == "selected"]
        for r in recs:
            if r["id"] in ids:
                try: run_clip(r)
                except Exception as ex: print(f"  FAILED {r['id']}: {ex}  (try the next candidate)")
        preview()
    elif cmd == "step":
        STEPS[argv[1]](get_rec(argv[2]))
    elif cmd == "preview": preview()
    elif cmd == "discover": discover()
    elif cmd == "watch": watch(argv[1:])
    elif cmd == "ledger":
        for r in load_batch()["clips"]: print(r["id"], "->", ledger_check(r) or "ok")
    else: print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
