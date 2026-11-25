import sys,subprocess,os
f,out=sys.argv[1],sys.argv[2]; fps=float(sys.argv[3]) if len(sys.argv)>3 else 2; t0=float(sys.argv[4]) if len(sys.argv)>4 else 0; t1=float(sys.argv[5]) if len(sys.argv)>5 else 9999
F="/home/claude/xvariclips-media/tools/fonts/Anton-Regular.ttf"
dur=float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',f],capture_output=True,text=True).stdout); t1=min(t1,dur)
n=int((t1-t0)*fps); cols=8; rows=(n+cols-1)//cols
subprocess.run(['ffmpeg','-y','-v','error','-ss',str(t0),'-t',str(t1-t0),'-i',f,'-vf',f"fps={fps},scale=240:-2,drawtext=fontfile={F}:text='%{{pts\\:hms\\:{t0}}}':fontsize=16:fontcolor=yellow:borderw=2:x=3:y=3,tile={cols}x{rows}",'-frames:v','1',out])
