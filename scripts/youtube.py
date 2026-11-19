"""Upload a video straight to YouTube (YouTube Data API v3, resumable upload). stdlib only.

post.py calls upload() when the secrets YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET and
YOUTUBE_REFRESH_TOKEN are set. Without them YouTube keeps going through Buffer.

Scheduling is done by YouTube itself: the video is uploaded as private with
status.publishAt = dueAt and goes public at that time.

CLI:  python3 scripts/youtube.py --check     # only tests that the credentials work
"""
import datetime as dt
import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
SECRETS = ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")
UPLOAD_ATTEMPTS = 5


class YouTubeError(Exception):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """The resumable-upload protocol answers 308 = 'resume incomplete'; never follow it."""

    def redirect_request(self, *args, **kwargs):
        return None


_opener = urllib.request.build_opener(_NoRedirect)


def enabled():
    return all(os.environ.get(k, "").strip() for k in SECRETS)


def _read_err(e):
    try:
        body = e.read().decode("utf-8", "replace")[:1500]
    except Exception:
        body = ""
    return f"HTTP {e.code}: {body}"


def access_token():
    data = urllib.parse.urlencode({
        "client_id": os.environ["YOUTUBE_CLIENT_ID"].strip(),
        "client_secret": os.environ["YOUTUBE_CLIENT_SECRET"].strip(),
        "refresh_token": os.environ["YOUTUBE_REFRESH_TOKEN"].strip(),
        "grant_type": "refresh_token",
    }).encode()
    try:
        with _opener.open(urllib.request.Request(TOKEN_URL, data=data), timeout=60) as r:
            return json.load(r)["access_token"]
    except urllib.error.HTTPError as e:
        raise YouTubeError("token refresh failed - " + _read_err(e))
    except (urllib.error.URLError, OSError) as e:
        raise YouTubeError(f"token refresh failed - {e}")


def _parse_utc(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(dt.timezone.utc)


def build_metadata(job, now=None):
    """Snippet + status for videos.insert, from a videos/*.json job."""
    now = now or dt.datetime.now(dt.timezone.utc)
    caption = job["caption"]
    tags = []
    for w in caption.split():
        if w.startswith("#") and len(w) > 1 and w[1:] not in tags:
            tags.append(w[1:])
    snippet = {
        "title": job["title"].replace("<", "").replace(">", "")[:100],
        "description": caption[:4900],
        "categoryId": str(job.get("youtubeCategory", "25")),   # 25 = News & Politics
        "tags": tags[:15],
    }
    status = {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
    if job.get("draft"):
        status["privacyStatus"] = "private"
    elif not job.get("now") and job.get("dueAt"):
        due = _parse_utc(job["dueAt"])
        if due > now + dt.timedelta(minutes=2):
            status["privacyStatus"] = "private"
            status["publishAt"] = due.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    return {"snippet": snippet, "status": status}


def _download(url, dest):
    last = None
    for i in range(4):
        try:
            with urllib.request.urlopen(url, timeout=120) as r, open(dest, "wb") as f:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
            return
        except Exception as e:  # the media branch may need a few seconds to be readable
            last = e
            time.sleep(5 * (i + 1))
    raise YouTubeError(f"could not download {url}: {last}")


def _send(session, path, size, start):
    with open(path, "rb") as f:
        f.seek(start)
        body = f.read()
    headers = {"Content-Type": "video/mp4", "Content-Length": str(size - start)}
    if start:
        headers["Content-Range"] = f"bytes {start}-{size - 1}/{size}"
    req = urllib.request.Request(session, data=body, method="PUT", headers=headers)
    with _opener.open(req, timeout=900) as r:
        return json.load(r)


def _resume_point(session, size):
    """Ask YouTube how much of the upload it has. Returns (next_byte, finished_response)."""
    req = urllib.request.Request(session, data=b"", method="PUT",
                                 headers={"Content-Length": "0", "Content-Range": f"bytes */{size}"})
    try:
        with _opener.open(req, timeout=60) as r:
            return size, json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 308:
            rng = e.headers.get("Range")          # e.g. "bytes=0-1048575"
            return (int(rng.split("-")[1]) + 1 if rng else 0), None
        raise


def _upload(job, video_url):
    token = access_token()
    meta = build_metadata(job)
    path = os.path.join(tempfile.mkdtemp(), "video.mp4")
    _download(video_url, path)
    size = os.path.getsize(path)
    if size == 0:
        raise YouTubeError("downloaded video is empty")
    query = urllib.parse.urlencode({"uploadType": "resumable", "part": "snippet,status",
                                    "notifySubscribers": "true"})
    init = urllib.request.Request(
        f"{UPLOAD_URL}?{query}", data=json.dumps(meta).encode(), method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8",
                 "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)})
    try:
        with _opener.open(init, timeout=60) as r:
            session = r.headers["Location"]
    except urllib.error.HTTPError as e:
        raise YouTubeError("could not start upload - " + _read_err(e))

    start, res = 0, None
    for attempt in range(UPLOAD_ATTEMPTS):
        try:
            res = _send(session, path, size, start)
            break
        except urllib.error.HTTPError as e:
            if e.code < 500:
                raise YouTubeError("upload failed - " + _read_err(e))
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(min(10 * (attempt + 1), 30))
        try:
            start, done = _resume_point(session, size)
            if done:
                res = done
                break
        except Exception:
            start = 0
    if res is None or "id" not in res:
        raise YouTubeError("upload did not finish")
    return {
        "ok": True, "id": res["id"], "url": f"https://youtu.be/{res['id']}",
        "requested_privacy": meta["status"]["privacyStatus"],
        "publishAt": meta["status"].get("publishAt"),
        "reported_privacy": (res.get("status") or {}).get("privacyStatus"),
    }


def upload(job, video_url):
    """Never raises: returns a dict with "ok": True/False (and "error")."""
    try:
        return _upload(job, video_url)
    except YouTubeError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:  # keep the Buffer part of post.py alive no matter what
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


if __name__ == "__main__":
    if "--check" in sys.argv:
        if not enabled():
            print(json.dumps({"ok": False, "error": "YOUTUBE_* secrets are not all set"}))
            sys.exit(1)
        try:
            access_token()
            print(json.dumps({"ok": True, "check": "refresh token accepted"}))
        except YouTubeError as e:
            print(json.dumps({"ok": False, "error": str(e)}))
            sys.exit(1)
    else:
        print(__doc__)
