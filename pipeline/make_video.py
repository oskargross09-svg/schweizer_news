"""Story JSON -> Swiss News video (1080x1920, German VO, music).

  python3 pipeline/make_video.py stories/2026-11-01_02.json --stills   # VO + layout check + build/<name>/sheet.jpg
  python3 pipeline/make_video.py stories/2026-11-01_02.json            # full render -> build/<name>/<name>.mp4
"""
import datetime as dt, html, json, os, subprocess, sys
import numpy as np, soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, f"{ROOT}/pipeline")
import tts, images, music

FPS, LEAD, TAIL = 30, 0.22, 0.42
WEEKDAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
GRID = json.load(open(f"{ROOT}/pipeline/assets/schweiz-raster.json"))
# reference points of the raster (col,row) with their coordinates -> linear fit lon/lat -> col/row
REF = {"Genève": (6.143, 46.204), "Lausanne": (6.633, 46.520), "Bern": (7.447, 46.948), "Basel": (7.589, 47.560),
       "Luzern": (8.309, 47.050), "Zürich": (8.541, 47.377), "St. Gallen": (9.376, 47.424), "Chur": (9.532, 46.849),
       "Lugano": (8.952, 46.004), "Sion": (7.359, 46.233)}
_lon = np.polyfit([REF[k][0] for k in REF], [GRID["places"][k][0] for k in REF], 1)
_lat = np.polyfit([REF[k][1] for k in REF], [GRID["places"][k][1] for k in REF], 1)
LAND = {tuple(c) for c in GRID["cells"]}
E = html.escape


def cell_of(s):
    if s.get("place") in GRID["places"] and "lat" not in s:
        return GRID["places"][s["place"]]
    c, r = round(np.polyval(_lon, s["lon"])), round(np.polyval(_lat, s["lat"]))
    if (c, r) not in LAND:  # snap to nearest land cell
        c, r = min(LAND, key=lambda x: (x[0] - c) ** 2 + (x[1] - r) ** 2)
    return [c, r]


def map_svg(mark):
    cells = "".join(f'<rect class="cell" data-row="{r}" x="{c*24}" y="{r*24}" width="20" height="20"/>' for c, r in GRID["cells"])
    mc, mr = mark
    marks = "".join(f'<rect x="{(mc+dx)*24}" y="{(mr+dy)*24}" width="20" height="20"/>'
                    for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (mc + dx, mr + dy) in LAND or (dx, dy) == (0, 0))
    return f'<svg class="sn-map" viewBox="0 0 864 552"><g class="land">{cells}</g><g class="mark">{marks}</g></svg>'


def appear_at(n_items, offs, first_sentence=0):
    """time (s, scene-relative) at which item j appears: with the matching sentence of the VO"""
    n_s = len(offs) - first_sentence
    out = []
    for j in range(n_items):
        k = first_sentence + (j if n_s == n_items else round(j * n_s / n_items))
        out.append(0.2 if j == 0 and first_sentence == 0 else round(LEAD + offs[min(k, len(offs) - 1)] - 0.1, 2))
    return out


def bar():
    return '<div class="sn-bar anim" data-kind="bar" data-at="0.05"></div>'


def label(t, at=0.15):
    return f'<div class="sn-col sn-top"><span class="sn-label label anim" data-at="{at}">{E(t)}</span></div>' if t else ""


def source(t, at):
    return f'<div class="sn-col sn-bottom"><p class="caption sn-source anim" data-at="{at}">{E(t)}</p></div>' if t else ""


def soft(t):  # allow soft hyphens written as "|" in long compounds
    return E(t).replace("|", "&shy;")


def frame(s, i, ctx):
    k, a, offs = s["type"], f'data-s="{i}"', s["_offs"]
    if k == "intro":
        return f'''<div class="sn-frame scene" {a}><div class="sn-intro-block anim" data-kind="drop" data-at="0"><div class="sn-wordmark wordmark anim" data-at="0.25">Swiss News</div></div>
<div class="sn-col sn-intro-meta"><p class="headline anim" data-at="0.45">{ctx["edition_word"]}</p><p class="date anim" data-at="0.53">{ctx["date_long"]}</p></div></div>'''
    if k == "headline":
        return f'''<div class="sn-frame scene" {a}>{bar()}{label(s.get("label"))}
<div class="sn-col sn-headline-block"><h1 class="headline anim" data-at="0.23">{soft(s["headline"])}</h1></div>{source(s.get("source"), 0.31)}</div>'''
    if k == "place":
        return f'''<div class="sn-frame scene" {a}>{bar()}{label(s.get("label"))}
<div class="sn-col sn-place-block"><h1 class="headline anim" data-at="0.23">{soft(s["place"])}</h1><p class="explainer anim" data-at="0.31">{E(s.get("line", ""))}</p></div>
{map_svg(cell_of(s))}{source(s.get("source"), 0.39)}</div>'''
    if k == "statement":
        texts = s["text"] if isinstance(s["text"], list) else [s["text"]]
        ats = appear_at(len(texts), offs)
        ps = "".join(f'<p class="statement anim" data-at="{t}">{soft(x)}</p>' for x, t in zip(texts, ats))
        cls = "single" if len(texts) == 1 else ""
        return f'''<div class="sn-frame sn-frame--accent scene" {a}>{bar()}<div class="sn-col sn-statement-block {cls}">{ps}</div>{source(s.get("source"), 0.36)}</div>'''
    if k == "number":
        num = str(s["number"])
        cnt = f'class="number count" data-to="{num}"' if num.isdigit() else 'class="number"'
        return f'''<div class="sn-frame scene" {a}>{bar()}{label(s.get("label"))}<div class="sn-col sn-number-block"><div class="sn-number-row anim" data-at="0.15"><span {cnt}>{E(num)}</span><span class="number-unit">{E(s.get("unit", ""))}</span></div>
<div class="sn-number-rule anim" data-kind="rule" data-at="0.45"></div><p class="explainer anim" data-at="0.55">{soft(s.get("text", ""))}</p></div>{source(s.get("source"), 0.63)}</div>'''
    if k == "photo":
        pos = s.get("position", "50% 50%")
        lab = f'<span class="sn-label label anim" data-at="0.3">{E(s["label"])}</span>' if s.get("label") else ""
        return f'''<div class="sn-frame scene" {a}><div class="sn-photo anim" data-kind="drop" data-at="0"><img src="{s["_img"]}" style="object-position:{pos}"></div>{bar()}
<div class="sn-col sn-photo-text">{lab}<p class="statement anim" data-at="0.4">{soft(s["text"])}</p></div>{source(s["_credit"], 0.5)}</div>'''
    if k == "recap":
        ats = appear_at(len(s["items"]), offs, first_sentence=1 if len(offs) > len(s["items"]) else 0)
        items = "".join(f'''<div class="sn-recap-item anim" data-at="{t}"><span class="n">{j+1}</span><div class="t"><p class="k">{E(it.get("label", ""))}</p><p class="s">{soft(it["text"])}</p></div></div>'''
                        for j, (it, t) in enumerate(zip(s["items"], ats)))
        return f'''<div class="sn-frame scene" {a}>{bar()}<div class="sn-col sn-recap-block"><h1 class="headline anim" data-at="0.15">{soft(s.get("title", "Die Nacht im Überblick"))}</h1><div class="sn-recap-list">{items}</div></div>{source(s.get("source"), 0.3)}</div>'''
    if k == "outro":
        return f'''<div class="sn-frame sn-frame--brand scene" {a}>{bar()}<div class="sn-col sn-outro-block"><div class="sn-wordmark wordmark anim" data-at="0.2">Swiss News</div>
<p class="headline anim" data-at="0.3">Folgen für tägliche News</p><p class="explainer anim" data-at="0.38">Jeden Morgen und Abend die wichtigsten Nachrichten aus der Schweiz</p></div></div>'''
    raise SystemExit(f"unknown scene type: {k}")


CHECK_JS = """() => { const out = []; document.querySelectorAll('.scene').forEach((sc, i) => {
  sc.style.visibility = 'visible';
  sc.querySelectorAll('.headline,.statement,.explainer,.caption,.label,.sn-recap-item,.number-unit').forEach(el => {
    const r = el.getBoundingClientRect(); if (!r.width) return;
    const brand = sc.classList.contains('sn-frame--brand') || el.closest('.sn-intro-block');
    if (!brand && (r.right > 928 || r.bottom > 1488 || r.top < 200)) out.push(`scene ${i}: '${el.textContent.slice(0, 40)}' outside safe area (top ${r.top|0}, right ${r.right|0}, bottom ${r.bottom|0})`);
  });
  const blocks = [...sc.querySelectorAll('.sn-col')].map(e => e.getBoundingClientRect()).filter(r => r.height);
  for (let a = 0; a < blocks.length; a++) for (let b = a + 1; b < blocks.length; b++) {
    const A = blocks[a], B = blocks[b]; if (A.bottom > B.top + 1 && B.bottom > A.top + 1) out.push(`scene ${i}: text blocks overlap`); }
  const ph = sc.querySelector('.sn-photo-text'); if (ph && ph.getBoundingClientRect().bottom > 1400) out.push(`scene ${i}: photo text too long (max 3 lines)`);
  sc.style.visibility = 'hidden'; }); return out; }"""


def main(path, stills=False):
    st = json.load(open(path))
    name = os.path.splitext(os.path.basename(path))[0]
    B = f"{ROOT}/build/{name}"
    os.makedirs(B, exist_ok=True)
    d = dt.date.fromisoformat(st["date"])
    morgen = st["edition"] == "morgen"
    ctx = {"edition_word": "Morgen" if morgen else "Abend",
           "date_long": f"{WEEKDAYS[d.weekday()]}, {d.day}. {MONTHS[d.month - 1]} {d.year}"}
    intro_vo = "Swiss News am Morgen." if morgen else "Swiss News am Abend."
    outro_vo = st.get("outro_vo") or ("Heute Abend erklären wir das wichtigste Thema des Tages. Folge Swiss News." if morgen
                                      else "Morgen früh gibt es den Überblick über die Nacht. Folge Swiss News.")
    scenes = [{"type": "intro", "vo": intro_vo}] + st["scenes"] + [{"type": "outro", "vo": outro_vo}]
    warn = []

    # 1) voice + timing
    t, vo_parts = 0.0, []
    for i, s in enumerate(scenes):
        a, sr, offs = tts.synth(s["vo"], st.get("say"))
        p = f"{B}/vo_{i}.wav"; sf.write(p, a, sr)
        vd = len(a) / sr
        dur = LEAD + vd + (1.1 if s["type"] == "outro" else TAIL)
        if s["type"] == "intro": dur = max(dur, 1.9)
        s.update(_offs=offs, start=round(t, 3), dur=round(dur, 3), vo_at=round(t + LEAD, 3))
        vo_parts.append((p, t + LEAD))
        if s["type"] not in ("intro", "outro") and vd > 16:
            warn.append(f"WARNING scene {i} ({s['type']}): VO {vd:.1f}s – split into two scenes, no frame should stand > 16 s")
        t += dur
    total = round(t, 3)

    # 2) photos
    for i, s in enumerate(scenes):
        if s["type"] == "photo":
            if s["image"].startswith("File:"):
                meta = images.fetch(s["image"], f"{B}/img_{i}.jpg")
            else:  # local file (own photos); credit must be given in the story
                subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", s["image"], "-vf", "scale=1600:-2", f"{B}/img_{i}.jpg"], check=True)
                meta = {"credit": s.get("credit", "Foto: Swiss News")}
            s["_img"], s["_credit"] = f"img_{i}.jpg", s.get("credit") or meta["credit"]

    # 3) page
    tl = [{k: v for k, v in s.items() if not k.startswith("_")} for s in scenes]
    css = open(f"{ROOT}/pipeline/style.css").read()
    page = f'''<!doctype html><html lang="de"><head><meta charset="utf-8"><style>{css}</style></head>
<body data-theme="{st['edition']}"><div id="stage">{"".join(frame(s, i, ctx) for i, s in enumerate(scenes))}<div class="sn-wipe-x"></div></div>
<script>const TL={json.dumps(tl, ensure_ascii=False)};const TOTAL={total};</script>
<script>{open(f"{ROOT}/pipeline/engine.js").read()}</script></body></html>'''
    open(f"{B}/index.html", "w").write(page)
    json.dump({"total": total, "scenes": [{"id": s.get("id", s["type"]), "type": s["type"], "start": s["start"], "dur": s["dur"]} for s in scenes]},
              open(f"{B}/timing.json", "w"), indent=1)
    if total > 95: warn.append(f"WARNING total {total:.0f}s – too long, shorten the VO")

    # 4) render
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(); pg = br.new_page(viewport={"width": 1080, "height": 1920})
        pg.goto(f"file://{B}/index.html"); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(400)
        pg.evaluate("render(TOTAL - 0.05)")
        warn += [f"ERROR {w}" for w in pg.evaluate(CHECK_JS)]
        shots = []
        for i, s in enumerate(scenes):
            pg.evaluate(f"render({s['start'] + s['dur'] - 0.3})")
            pp = f"{B}/still_{i}.png"; pg.screenshot(path=pp); shots.append(pp)
        if stills:
            br.close()
        else:
            ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "image2pipe", "-framerate", str(FPS), "-i", "-",
                                   "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", f"{B}/video.mp4"], stdin=subprocess.PIPE)
            for f in range(int(round(total * FPS))):
                pg.evaluate(f"render({f / FPS})")
                ff.stdin.write(pg.screenshot(type="jpeg", quality=93))
            ff.stdin.close(); ff.wait(); br.close()
    ins = sum([["-i", p] for p in shots], [])
    n = len(shots)
    fc = ";".join(f"[{j}]scale=270:480[s{j}]" for j in range(n)) + ";" + "".join(f"[s{j}]" for j in range(n)) + \
         f"xstack=inputs={n}:layout=" + "|".join(f"{(j % 6) * 270}_{(j // 6) * 480}" for j in range(n)) + ":fill=gray"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *ins, "-filter_complex", fc, f"{B}/sheet.jpg"], check=True)
    for w in warn: print(w)
    print(f"total {total:.1f}s · sheet: {B}/sheet.jpg")
    if stills: return

    # 5) audio mix
    SR = 48000
    mus = music.bed(total, seed=sum(map(ord, name)), morning=morgen)
    sf.write(f"{B}/music.wav", mus, SR)
    run = lambda a: subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *a], check=True)
    ins, parts = [], []
    for j, (p, at) in enumerate(vo_parts):
        ins += ["-i", p]; ms = int(at * 1000)
        parts.append(f"[{j}:a]aresample={SR},adelay={ms}|{ms}[v{j}]")
    fc = ";".join(parts) + ";" + "".join(f"[v{j}]" for j in range(len(vo_parts))) + \
         f"amix=inputs={len(vo_parts)}:normalize=0,apad=whole_dur={total},atrim=0:{total},loudnorm=I=-15:TP=-1.5:LRA=11[out]"
    run([*ins, "-filter_complex", fc, "-map", "[out]", "-ar", str(SR), "-ac", "1", f"{B}/voice.wav"])
    run(["-i", f"{B}/music.wav", "-af", f"afade=t=in:d=0.4,afade=t=out:st={total-1.5}:d=1.5,loudnorm=I=-29:TP=-3", "-ar", str(SR), f"{B}/music_bed.wav"])
    run(["-i", f"{B}/video.mp4", "-i", f"{B}/voice.wav", "-i", f"{B}/music_bed.wav", "-filter_complex",
         "[1:a]pan=stereo|c0=c0|c1=c0[v];[2:a]pan=stereo|c0=c0|c1=c0[m];[v][m]amix=inputs=2:normalize=0,volume=0.7,alimiter=limit=0.89[a]",
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", f"{B}/{name}.mp4"])
    print(f"video: {B}/{name}.mp4")


if __name__ == "__main__":
    main(sys.argv[1], stills="--stills" in sys.argv)
