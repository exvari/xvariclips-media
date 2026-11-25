import sys,subprocess,os,urllib.request,re,concurrent.futures as cf
vod,a,b,out=sys.argv[1],float(sys.argv[2]),float(sys.argv[3]),sys.argv[4]
q=sys.argv[5] if len(sys.argv)>5 else '720p60'
u=subprocess.run(['yt-dlp','-g','-f',f'{q}/720p30/720p/best[height<=720]',f'https://www.twitch.tv/videos/{vod}'],capture_output=True,text=True).stdout.strip().splitlines()
if not u: print('NO VOD URL'); sys.exit(1)
u=u[0]; base=u.rsplit('/',1)[0]
pl=urllib.request.urlopen(u,timeout=30).read().decode()
segs=[];t=0.0;init=None
for line in pl.splitlines():
    m=re.match(r'#EXTINF:([\d.]+)',line)
    if m: d=float(m.group(1)); continue
    mm=re.match(r'#EXT-X-MAP:URI="([^"]+)"',line)
    if mm: init=mm.group(1)
    if line and not line.startswith('#'):
        segs.append((t,t+d,line)); t+=d
need=[s for s in segs if s[1]>a and s[0]<b]
os.makedirs(out+'_seg',exist_ok=True)
def get(s):
    p=os.path.join(out+'_seg',s[2].replace('/','_'))
    if not os.path.exists(p): urllib.request.urlretrieve(base+'/'+s[2],p)
    return p
with cf.ThreadPoolExecutor(8) as ex: ps=list(ex.map(get,need))
raw=out+'_raw.ts'
with open(raw,'wb') as f:
    if init: f.write(urllib.request.urlopen(base+'/'+init).read())
    for p in ps: f.write(open(p,'rb').read())
subprocess.run(['ffmpeg','-y','-v','error','-i',raw,'-c','copy',out+'.mp4'])
print('start',need[0][0],'end',need[-1][1],'muted' if any('muted' in s[2] for s in need) else 'audio ok')
