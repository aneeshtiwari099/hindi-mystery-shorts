import json
import os
import sys
import time
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube"
]
TOKEN_URI = "https://oauth2.googleapis.com/token"

VIDEO_PATH = "output/short.mp4"
META_PATH = "output/meta.json"


def get_authenticated_service():
    client_id = os.environ.get("YT_CLIENT_ID")
    client_secret = os.environ.get("YT_CLIENT_SECRET")
    refresh_token = os.environ.get("YT_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        raise ValueError(
            "Missing YouTube credentials! Ensure YT_CLIENT_ID, YT_CLIENT_SECRET, "
            "and YT_REFRESH_TOKEN environment variables are set."
        )

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=TOKEN_URI,
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )

    # Refresh the access token
    creds.refresh(Request())
    return build("youtube", "v3", credentials=creds)


def upload_video(youtube):
    if not os.path.exists(VIDEO_PATH):
        raise FileNotFoundError(f"Video file not found at: {VIDEO_PATH}")
    if not os.path.exists(META_PATH):
        raise FileNotFoundError(f"Metadata file not found at: {META_PATH}")

    with open(META_PATH, "r", encoding="utf-8") as f:
        meta = json.load(f)

    title = meta.get("title", "Daily Mystery #Shorts")[:100]
    description = meta.get("description", "")
    tags = meta.get("tags", ["Shorts", "Mystery"])
    privacy = os.environ.get("YT_PRIVACY", "private").lower()
    if privacy not in ["public", "private", "unlisted"]:
        privacy = "private"

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "24",  # Entertainment
            "defaultLanguage": "hi",
            "defaultAudioLanguage": "hi",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        VIDEO_PATH,
        mimetype="video/mp4",
        chunksize=1024 * 1024 * 2,  # 2MB chunks
        resumable=True
    )

    print(f"Uploading '{title}' to YouTube ({privacy})...")
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    response = None
    retries = 0
    max_retries = 10

    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                print(f"Upload progress: {progress}%")
        except HttpError as e:
            if e.resp.status in [500, 502, 503, 504]:
                retries += 1
                if retries > max_retries:
                    raise
                wait_time = 2 ** retries
                print(f"Server error {e.resp.status}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise

    video_id = response.get("id")
    print(f"\nUpload Successful!")
    print(f"Video ID: {video_id}")
    print(f"Short URL: https://youtube.com/shorts/{video_id}")
    return video_id


if __name__ == "__main__":
    try:
        service = get_authenticated_service()
        upload_video(service)
    except Exception as e:
        print(f"Upload failed: {e}", file=sys.stderr)
        sys.exit(1)
