"""One-time helper: get the YouTube refresh token for ONE channel.

Run it on your own computer (not in GitHub), once per channel:

    python3 scripts/youtube_auth.py <CLIENT_ID> <CLIENT_SECRET>

A browser window opens. Sign in with the Google account that owns the channel and, if asked,
pick the right channel (brand account). The script then prints the refresh token.
Store it as GitHub secret YOUTUBE_REFRESH_TOKEN of that channel's repo.
"""
import http.server
import json
import secrets
import sys
import urllib.parse
import urllib.request
import webbrowser

PORT = 8765
REDIRECT = f"http://127.0.0.1:{PORT}"
SCOPE = "https://www.googleapis.com/auth/youtube.upload"


def main(client_id, client_secret):
    state = secrets.token_urlsafe(16)
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": client_id, "redirect_uri": REDIRECT, "response_type": "code",
        "scope": SCOPE, "access_type": "offline", "prompt": "consent", "state": state})
    got = {}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            got["code"] = (q.get("code") or [None])[0]
            got["state"] = (q.get("state") or [None])[0]
            got["error"] = (q.get("error") or [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("<h3>Fertig - du kannst dieses Fenster schliessen.</h3>".encode())

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", PORT), H)
    print("Öffne diesen Link, falls sich der Browser nicht von selbst öffnet:\n" + url + "\n")
    webbrowser.open(url)
    srv.handle_request()
    if got.get("error") or not got.get("code") or got.get("state") != state:
        sys.exit(f"Anmeldung fehlgeschlagen: {got.get('error') or 'kein Code erhalten'}")
    data = urllib.parse.urlencode({
        "code": got["code"], "client_id": client_id, "client_secret": client_secret,
        "redirect_uri": REDIRECT, "grant_type": "authorization_code"}).encode()
    with urllib.request.urlopen(urllib.request.Request("https://oauth2.googleapis.com/token", data=data)) as r:
        tok = json.load(r)
    if "refresh_token" not in tok:
        sys.exit("Kein Refresh-Token erhalten. Entziehe der App unter myaccount.google.com/permissions "
                 "den Zugriff und starte das Skript erneut.")
    print("\nYOUTUBE_REFRESH_TOKEN (als GitHub-Secret speichern, nirgends sonst teilen):\n")
    print(tok["refresh_token"])


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
