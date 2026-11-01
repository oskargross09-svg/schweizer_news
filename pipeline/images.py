"""Freely licensed photos from Wikimedia Commons.

  python3 pipeline/images.py search "Bundeshaus Bern"      -> candidates (title, size, licence, author) + preview sheet
  python3 pipeline/images.py fetch "File:Name.jpg" out.jpg -> downloads 1600 px version + out.json with credit line

Only licences in ALLOWED are accepted. Credit is shown in the frame ("Foto: … / Wikimedia Commons, CC BY 4.0").
"""
import html, json, os, re, subprocess, sys, urllib.parse, urllib.request

API = "https://commons.wikimedia.org/w/api.php"
UA = "SwissNewsBot/1.0 (https://github.com/oskargross09-svg/schweizer_news; oskargross09@gmail.com)"
ALLOWED = re.compile(r"^(CC0|Public domain|PD.*|CC BY(-SA)? [1-4]\.0.*|CC BY(-SA)? 2\.5.*|CC BY(-SA)? 3\.0.*)$", re.I)


def get(url, tries=4):
    import time
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503) or k == tries - 1:
                raise
            wait = min(int(e.headers.get("Retry-After") or 0) or 10 * (k + 1), 45)
            print(f"  (Wikimedia {e.code}, warte {wait}s)", file=sys.stderr)
            time.sleep(wait)


def api(**p):
    p.update(format="json", formatversion="2")
    return json.loads(get(API + "?" + urllib.parse.urlencode(p)))


def clean(s):
    s = re.sub(r"<[^>]+>", "", html.unescape(s or "")).strip()
    return re.sub(r"\s+", " ", s)[:60]


def info(titles, width=1280):
    r = api(action="query", titles="|".join(titles), prop="imageinfo",
            iiprop="url|size|extmetadata|mime", iiurlwidth=width)
    out = []
    for pg in r["query"]["pages"]:
        if "imageinfo" not in pg:
            continue
        ii = pg["imageinfo"][0]
        md = ii.get("extmetadata", {})
        lic = clean(md.get("LicenseShortName", {}).get("value"))
        out.append({"title": pg["title"], "w": ii["width"], "h": ii["height"], "mime": ii["mime"],
                    "orig": ii["url"], "size": ii.get("size", 0), "thumb": ii.get("thumburl", ii["url"]).replace("//thumb.wikimedia.org/", "//upload.wikimedia.org/"), "licence": lic,
                    "author": clean(md.get("Artist", {}).get("value")) or "unbekannt",
                    "ok": bool(ALLOWED.match(lic)) and ii["mime"] in ("image/jpeg", "image/png")})
    return out


def credit(i):
    return f"Foto: {i['author']} / Wikimedia Commons, {i['licence']}"


def search(q, n=8, out_dir="build/img-search"):
    r = api(action="query", list="search", srsearch=f"{q} filetype:bitmap", srnamespace=6, srlimit=n)
    titles = [h["title"] for h in r["query"]["search"]]
    if not titles:
        print("no results"); return []
    res = info(titles, width=250)
    os.makedirs(out_dir, exist_ok=True)
    files = []
    for k, i in enumerate(res):
        flag = "OK " if i["ok"] else "-- "
        print(f"[{k}] {flag}{i['title']}  {i['w']}x{i['h']}  {i['licence']}  {i['author']}")
        if i["ok"]:
            p = f"{out_dir}/{k}.jpg"
            open(p, "wb").write(get(i["thumb"])); __import__("time").sleep(2)
            files.append((k, p))
    if files:  # contact sheet with index numbers -> look at it with the Read tool
        ins = sum([["-i", p] for _, p in files], [])
        fl = ";".join(f"[{j}]scale=320:240:force_original_aspect_ratio=increase,crop=320:240,"
                      f"drawtext=text='{k}':x=8:y=8:fontsize=40:fontcolor=white:box=1:boxcolor=black@0.6[v{j}]"
                      for j, (k, _) in enumerate(files))
        cols = 4
        rows = (len(files) + cols - 1) // cols
        layout = "|".join(f"{(j % cols) * 320}_{(j // cols) * 240}" for j in range(len(files)))
        fl += ";" + "".join(f"[v{j}]" for j in range(len(files))) + f"xstack=inputs={len(files)}:layout={layout}:fill=black"
        if len(files) == 1:
            fl = fl.split(";")[0].replace("[v0]", "")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *ins, "-filter_complex", fl, f"{out_dir}/sheet.jpg"], check=True)
        print(f"preview: {out_dir}/sheet.jpg")
    return res


def fetch(title, out):
    i = info([title])
    if not i:
        raise SystemExit(f"image not found: {title}")
    i = i[0]
    if not i["ok"]:
        raise SystemExit(f"licence not allowed ({i['licence']}): {title}")
    raw = out + ".orig"
    open(raw, "wb").write(get(i["thumb"]))
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", raw, "-vf", "scale='min(1600,iw)':-2", "-q:v", "2", out], check=True)
    os.remove(raw)
    meta = {"title": title, "licence": i["licence"], "author": i["author"], "credit": credit(i)}
    json.dump(meta, open(os.path.splitext(out)[0] + ".json", "w"), ensure_ascii=False)
    return meta


if __name__ == "__main__":
    if sys.argv[1] == "search":
        search(" ".join(sys.argv[2:]))
    elif sys.argv[1] == "fetch":
        print(fetch(sys.argv[2], sys.argv[3]))
