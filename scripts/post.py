"""Create Buffer posts (TikTok, Instagram Reel, YouTube Short) for one video.

Usage: post.py videos/2026-10-30_01.json
The JSON holds: video (file name in videos/), caption, title, dueAt (ISO UTC) and
optional draft (true = save as draft in Buffer instead of scheduling)
or now (true = publish immediately).
"""
import json, os, sys
from buffer import gql

REPO = os.environ["GITHUB_REPOSITORY"]
BRANCH = os.environ.get("GITHUB_REF_NAME", "main")
channels = json.load(open("config/channels.json"))

MUTATION = """mutation($input: CreatePostInput!) { createPost(input: $input) {
  ... on PostActionSuccess { post { id status dueAt } }
  ... on MutationError { message } } }"""

def main(path):
    job = json.load(open(path))
    url = f"https://raw.githubusercontent.com/{REPO}/{job.get('branch', BRANCH)}/videos/{job['video']}"
    draft = bool(job.get("draft"))
    title = job["title"][:100]
    meta = {
        "tiktok": {"tiktok": {"title": title}},
        "instagram": {"instagram": {"type": "reel", "shouldShareToFeed": True}},
        "youtube": {"youtube": {"title": title, "categoryId": "25", "privacy": "public",
                                 "madeForKids": False, "notifySubscribers": True}},
    }
    results, ok = {}, True
    for service, cid in channels.items():
        inp = {"channelId": cid, "text": job["caption"], "schedulingType": "automatic",
               "needsApproval": False, "metadata": meta[service],
               "assets": [{"video": {"url": url, "metadata": {"thumbnailOffset": job.get("thumbnailOffset", 1500)}}}]}
        if draft:
            inp.update(mode="addToQueue", saveToDraft=True)
        elif job.get("now"):
            inp.update(mode="shareNow")
        else:
            inp.update(mode="customScheduled", dueAt=job["dueAt"])
        res = gql(MUTATION, {"input": inp})
        results[service] = res
        cp = ((res.get("data") or {}).get("createPost") or {})
        if "post" not in cp:
            ok = False
    print(json.dumps({"job": path, "run": job.get("run"), "url": url, "draft": draft, "ok": ok, "results": results}, indent=1))
    return ok

if __name__ == "__main__":
    good = all(main(p) for p in sys.argv[1:])
    sys.exit(0 if good else 1)
