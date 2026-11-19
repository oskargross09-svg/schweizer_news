"""Lädt ein Video per YouTube Data API auf den Kanal hoch.

Benötigte Umgebungsvariablen (GitHub Secrets):
    CLIENT_ID, CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN

Beispiel:
    pip install google-api-python-client google-auth
    python3 upload_youtube.py video.mp4 --title "Titel" --description "Text" \
        --privacy public --synthetic
"""
import argparse
import os
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("video")
    p.add_argument("--title", required=True)
    p.add_argument("--description", default="")
    p.add_argument("--tags", default="", help="Komma-getrennt")
    p.add_argument("--privacy", default="public", choices=["public", "unlisted", "private"])
    p.add_argument("--category", default="25", help="25 = News & Politik")
    p.add_argument("--synthetic", action="store_true",
                   help="Inhalt als KI-generiert/verändert kennzeichnen")
    args = p.parse_args()

    creds = Credentials(
        token=None,
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["CLIENT_ID"],
        client_secret=os.environ["CLIENT_SECRET"],
        scopes=SCOPES,
    )
    creds.refresh(Request())  # schlägt mit invalid_grant fehl, wenn der Token abgelaufen ist

    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": args.title,
            "description": args.description,
            "tags": [t.strip() for t in args.tags.split(",") if t.strip()],
            "categoryId": args.category,
        },
        "status": {
            "privacyStatus": args.privacy,
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": args.synthetic,
        },
    }

    media = MediaFileUpload(args.video, chunksize=8 * 1024 * 1024, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Upload {int(status.progress() * 100)} %", file=sys.stderr)

    print(f"Fertig: https://youtu.be/{response['id']}")
    print(f"Status: {response['status']['privacyStatus']}")


if __name__ == "__main__":
    main()
