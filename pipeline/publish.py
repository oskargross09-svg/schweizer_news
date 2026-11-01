"""Render a story and hand it to the GitHub -> Buffer publish workflow.

Usage: python3 pipeline/publish.py stories/2026-10-30_01.json [--draft] [--now] [--no-render]

1. renders build/<name>/<name>.mp4 (unless --no-render)
2. pushes the MP4 to the `media` branch (keeps main small)
3. writes videos/<name>.json (caption, title, dueAt) and pushes main -> GitHub Action creates the Buffer posts
4. waits for the Action's result (bot-logs branch) and prints OK / FAILED
"""
import base64, datetime as dt, json, os, subprocess, sys, time
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def _repo():
    url = subprocess.run("git remote get-url origin", cwd=ROOT, shell=True, text=True, capture_output=True).stdout.strip()
    return url.rstrip("/").removesuffix(".git").split("github.com")[-1].lstrip("/:")


REPO = _repo()


def sh(cmd, cwd=ROOT, check=True):
    r = subprocess.run(cmd, cwd=cwd, shell=True, text=True, capture_output=True)
    if check and r.returncode:
        raise SystemExit(f"command failed: {cmd}\n{r.stdout}\n{r.stderr}")
    return r.stdout.strip()


def due_at(date, edition):
    hm = "06:30" if edition == "morgen" else "18:30"
    local = dt.datetime.fromisoformat(f"{date}T{hm}").replace(tzinfo=ZoneInfo("Europe/Zurich"))
    return local.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def caption(st):
    tags = " ".join("#" + t.lstrip("#") for t in st.get("hashtags", []))
    return (st["caption"].strip() + "\n\nJeden Morgen der Überblick, jeden Abend das wichtigste Thema erklärt. Folge Swiss News.\n\n" + tags).strip()


def push_media(mp4, name):
    wt = "/tmp/sn-media"
    sh(f"rm -rf {wt}")
    exists = sh("git ls-remote --heads origin media")
    if exists:
        sh("git fetch -q --depth 1 origin media")
        sh(f"git worktree add -f {wt} FETCH_HEAD -B media-local")
    else:
        sh(f"git worktree add -f --detach {wt}")
        sh("git checkout -q --orphan media-local && git rm -rqf . && git clean -fdq", cwd=wt)
    os.makedirs(f"{wt}/videos", exist_ok=True)
    sh(f"cp {mp4} {wt}/videos/{name}.mp4")
    sh(f"git add videos/{name}.mp4 && git -c user.name=swiss-news-bot -c user.email=bot@users.noreply.github.com "
       f"commit -qm 'media {name}' && git push -q origin HEAD:media", cwd=wt)
    sh(f"git worktree remove --force {wt}")


def wait_result(name, since, timeout=300):
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(15)
        r = subprocess.run(["gh", "api", f"repos/{REPO}/contents/logs/{name}.txt?ref=bot-logs"], capture_output=True, text=True)
        if r.returncode == 0:
            info = json.loads(r.stdout)
            body = base64.b64decode(info["content"]).decode()
            if f'"job": "videos/{name}.json"' in body and since in body:
                return body
    return None


def main(path, draft=False, now=False, render=True):
    st = json.load(open(path))
    name = os.path.splitext(os.path.basename(path))[0]
    mp4 = f"{ROOT}/build/{name}/{name}.mp4"
    if render:
        sh(f"python3 pipeline/make_video.py {path}", check=True)
    if not os.path.exists(mp4):
        raise SystemExit(f"missing {mp4}")
    T = json.load(open(f"{ROOT}/build/{name}/timing.json"))
    head = next(s for s in T["scenes"] if s["type"] not in ("intro",))
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S")
    sh("git pull -q --rebase origin main")
    push_media(mp4, name)
    job = {"video": f"{name}.mp4", "branch": "media", "title": st["title"][:100], "caption": caption(st),
           "thumbnailOffset": int((head["start"] + 1.5) * 1000), "run": stamp}
    if draft:
        job["draft"] = True
    elif now:
        job["now"] = True
    else:
        job["dueAt"] = due_at(st["date"], st["edition"])
    os.makedirs(f"{ROOT}/videos", exist_ok=True)
    json.dump(job, open(f"{ROOT}/videos/{name}.json", "w"), indent=1, ensure_ascii=False)
    sh(f"git add {path} videos/{name}.json && git -c user.name=swiss-news-bot -c user.email=bot@users.noreply.github.com "
       f"commit -qm 'Edition {name}' && git push -q origin HEAD:main")
    print(f"pushed {name}; scheduled for {job.get('dueAt', 'draft' if draft else 'now')}. Waiting for Buffer...")
    res = wait_result(name, stamp)
    if res is None:
        print("RESULT: UNKNOWN (no answer from the GitHub Action within 5 minutes)")
        sys.exit(3)
    ok = '"ok": true' in res
    print("RESULT:", "OK" if ok else "FAILED")
    if not ok:
        print(res[:4000])
        sys.exit(1)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], draft="--draft" in a, now="--now" in a, render="--no-render" not in a)
