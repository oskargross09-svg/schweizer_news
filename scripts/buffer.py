"""Small Buffer GraphQL client (stdlib only)."""
import json, os, sys, urllib.request

API = "https://api.buffer.com"

def gql(query, variables=None):
    key = os.environ.get("BUFFER_API_KEY", "").strip()
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(API, data=body, headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json",
        "User-Agent": "swiss-news-bot"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"http_error": e.code, "body": e.read().decode()[:2000]}
