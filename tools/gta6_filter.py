"""gta6_filter.py <glob of yt-dlp -J clip listings> <out.json>
Asks Twitch's public GQL for each clip's game, VOD id and VOD offset, writes them all to out.json,
and prints the game counts. Keep only game == "Grand Theft Auto VI" before downloading anything.
Skip slugs listed in screened_slugs.txt (already screened on an earlier run).
Example: python gta6_filter.py 'disc/*_24hr.json' all24.json
"""
import json, glob, urllib.request, sys
from collections import Counter

H = {"Client-ID": "kimne78kx3ncx6brgo4mv6wki5h1ko", "Content-Type": "application/json"}
clips = []
for f in sorted(glob.glob(sys.argv[1])):
    try:
        e = json.load(open(f))["entries"]
    except Exception:
        continue
    ch = f.split("/")[-1].rsplit("_", 1)[0]
    for x in e:
        clips.append(dict(ch=ch, slug=x["url"].rstrip("/").split("/")[-1], url=x["url"], title=x["title"],
                          views=x.get("view_count"), dur=x.get("duration"), ts=x.get("timestamp")))
out = []
for i in range(0, len(clips), 10):          # >10 aliases per query gets HTTP 400
    chunk = clips[i:i + 10]
    q = "query{" + " ".join(f'c{j}: clip(slug:{json.dumps(c["slug"])}){{game{{name}} createdAt videoOffsetSeconds video{{id}}}}'
                            for j, c in enumerate(chunk)) + "}"
    req = urllib.request.Request("https://gql.twitch.tv/gql", data=json.dumps({"query": q}).encode(), headers=H)
    d = (json.load(urllib.request.urlopen(req, timeout=30)).get("data") or {})
    for j, c in enumerate(chunk):
        v = d.get(f"c{j}") or {}
        c["game"] = (v.get("game") or {}).get("name"); c["created"] = v.get("createdAt")
        c["vod"] = (v.get("video") or {}).get("id"); c["voff"] = v.get("videoOffsetSeconds")
        out.append(c)
json.dump(out, open(sys.argv[2], "w"), indent=0)
print(Counter(c["game"] for c in out).most_common(15))
