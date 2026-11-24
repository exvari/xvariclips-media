import json,glob,os,subprocess
import soundfile as sf
from faster_whisper import WhisperModel
m=WhisperModel("small.en",device="cpu",compute_type="int8")
for f in sorted(glob.glob("*.mp4")):
    o=f[:-4]+".words.json"
    if os.path.exists(o): continue
    w=f[:-4]+".wav"; subprocess.run(["ffmpeg","-y","-v","error","-i",f,"-ac","1","-ar","16000",w])
    a,_=sf.read(w,dtype="float32"); ws=[]
    for vad in (False,True):
        try:
            segs,_=m.transcribe(a,word_timestamps=True,vad_filter=vad)
            ws=[{"w":x.word.strip(),"s":round(x.start,2),"e":round(x.end,2)} for s in segs for x in (s.words or [])]; break
        except Exception as ex: ws=[]
    json.dump(ws,open(o,"w")); print("==",f,len(ws),flush=True)
