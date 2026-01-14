import requests
import re


API_KEY = "AIzaSyCzlLINvJjmDims_aUiMKT02M_22k5Bnxk"


def extract_video_id(video_url: str):
    """
    Supports:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID?si=xxxx
    - https://www.youtube.com/shorts/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    """
    if not video_url:
        return None

    cleaned_url = video_url.strip()

    # Query params 
    cleaned_url = cleaned_url.split("?")[0]

    patterns = [
        r"v=([a-zA-Z0-9_-]{11})",
        r"youtu\.be/([a-zA-Z0-9_-]{11})",
        r"youtube\.com/embed/([a-zA-Z0-9_-]{11})",
        r"shorts/([a-zA-Z0-9_-]{11})"
    ]

    for p in patterns:
        m = re.search(p, cleaned_url)
        if m:
            return m.group(1)

    # fallback:
    last_part = cleaned_url.split("/")[-1]
    if len(last_part) == 11:
        return last_part

    return None


def get_youtube_comments_and_title(video_url: str, max_comments: int = 50):
    """
     YouTube URL
    - video title
    - top-level comments

    return: (title, comments_list)  (None, None)
    """
    video_id = extract_video_id(video_url)
    if not video_id:
        return None, None

    # 1) Video title 
    video_api = "https://www.googleapis.com/youtube/v3/videos"
    v_params = {
        "part": "snippet",
        "id": video_id,
        "key": API_KEY
    }

    v_resp = requests.get(video_api, params=v_params).json()
    if "items" in v_resp and len(v_resp["items"]) > 0:
        title = v_resp["items"][0]["snippet"]["title"]
    else:
        title = "Unknown Video Title"

    # 2) Comments 
    comments_api = "https://www.googleapis.com/youtube/v3/commentThreads"
    params = {
        "part": "snippet",
        "videoId": video_id,
        "key": API_KEY,
        "maxResults": 50,
        "textFormat": "plainText",
        "order": "relevance"
    }

    response = requests.get(comments_api, params=params).json()

    if "items" not in response:
        return title, []

    comments = []
    for item in response["items"]:
        comment = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
        comments.append(comment)
        if len(comments) >= max_comments:
            break

    return title, comments
