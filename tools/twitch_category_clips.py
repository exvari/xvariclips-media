import json,urllib.request,sys
H={"Client-ID":"kimne78kx3ncx6brgo4mv6wki5h1ko","Content-Type":"application/json"}
period=sys.argv[1]; pages=int(sys.argv[2]); out=[]; cur=None
for p in range(pages):
    after=f',after:{json.dumps(cur)}' if cur else ''
    q='query{game(name:"Grand Theft Auto VI"){clips(first:100%s,criteria:{period:%s,languages:[EN]}){edges{cursor node{slug title viewCount durationSeconds createdAt broadcaster{login} videoOffsetSeconds video{id}}} pageInfo{hasNextPage}}}}'%(after,period)
    r=json.load(urllib.request.urlopen(urllib.request.Request("https://gql.twitch.tv/gql",data=json.dumps({"query":q}).encode(),headers=H),timeout=30))
    if 'errors' in r: print(r['errors'][:2]); break
    c=r['data']['game']['clips']; e=c['edges']
    for x in e:
        n=x['node']; out.append(dict(slug=n['slug'],title=n['title'],views=n['viewCount'],dur=n['durationSeconds'],created=n['createdAt'],ch=(n['broadcaster'] or {}).get('login'),voff=n['videoOffsetSeconds'],vod=(n['video'] or {}).get('id')))
    if not e or not c['pageInfo']['hasNextPage']: break
    cur=e[-1]['cursor']
json.dump(out,open(f'game_{period}.json','w'))
from collections import Counter
print(len(out)); print(Counter(x['ch'] for x in out).most_common(40))
