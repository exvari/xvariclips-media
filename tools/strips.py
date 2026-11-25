import sys,os,glob,subprocess
d=sys.argv[1]; N=int(sys.argv[2]) if len(sys.argv)>2 else 10
F="/home/claude/xvariclips-media/tools/fonts/Anton-Regular.ttf"
for f in sorted(glob.glob(os.path.join(d,'[0-9][0-9][0-9].mp4'))):
    n=os.path.basename(f)[:-4]; out=os.path.join(d,n+'.strip.jpg')
    if os.path.exists(out): continue
    dur=float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',f],capture_output=True,text=True).stdout or 0)
    tmp=[]
    for i in range(N):
        t=dur*(i+0.5)/N; p=os.path.join(d,f'_t{i}.jpg')
        subprocess.run(['ffmpeg','-y','-v','error','-ss',f'{t:.2f}','-i',f,'-frames:v','1','-vf',
          f"scale=192:108:force_original_aspect_ratio=decrease,pad=192:108,drawtext=fontfile={F}:text='{n} {int(t)}s':fontsize=14:fontcolor=yellow:borderw=2:x=3:y=3",p])
        tmp.append(p)
    subprocess.run(['ffmpeg','-y','-v','error','-i',os.path.join(d,'_t%d.jpg'),'-vf',f'tile={N}x1',out])
    for p in tmp: os.remove(p) if os.path.exists(p) else None
S=sorted(glob.glob(os.path.join(d,'[0-9][0-9][0-9].strip.jpg')))
for k in range(0,len(S),9):
    g=S[k:k+9]; args=sum([['-i',s] for s in g],[])
    subprocess.run(['ffmpeg','-y','-v','error',*args,'-filter_complex',f'vstack=inputs={len(g)}',os.path.join(d,f'sheet{k//9:02d}.jpg')] if len(g)>1 else ['cp',g[0],os.path.join(d,f'sheet{k//9:02d}.jpg')])
print(len(S))
