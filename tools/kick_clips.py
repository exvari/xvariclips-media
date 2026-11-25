import json,urllib.request,sys,time
chs=sys.argv[1].split(','); out=[]
for ch in chs:
    cur=None
    for p in range(5):
        u=f"https://kick.com/api/v2/channels/{ch}/clips?sort=view&time=week"+(f"&cursor={cur}" if cur else "")
        try: d=json.load(urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"}),timeout=20))
        except Exception as e: print(ch,'ERR',e); break
        for c in d.get('clips',[]):
            out.append(dict(ch=ch,id=c['id'],title=c['title'],views=c['views'],dur=c['duration'],created=c['created_at'],cat=c['category']['name'],url=c['video_url'],ls=c['livestream_id']))
        cur=d.get('nextCursor')
        if not cur: break
        time.sleep(0.3)
json.dump(out,open('kick_week.json','w'))
from collections import Counter
print(len(out)); print(Counter((x['ch'],x['cat']) for x in out).most_common(40))
