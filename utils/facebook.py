import requests
import re

ACCESS_TOKEN = "YOUR_FACEBOOK_ACCESS_TOKEN_HERE"


def extract_post_id(url_or_id: str):
    """
    Supports:
    - https://www.facebook.com/{page}/posts/{POST_ID}
    - https://www.facebook.com/watch/?v={POST_ID}
    - https://www.facebook.com/{page}/videos/{POST_ID}
    """
    url_or_id = url_or_id.strip()

    if url_or_id.isdigit():
        return url_or_id

    patterns = [
        r"/posts/(\d+)",
        r"/videos/(\d+)",
        r"[?&]v=(\d+)",
    ]

    for p in patterns:
        m = re.search(p, url_or_id)
        if m:
            return m.group(1)

    return None


def get_facebook_comments(url_or_id: str, limit: int = 50):
    

    post_id = extract_post_id(url_or_id)
    if not post_id:
        return None

    graph_url = f"https://graph.facebook.com/v18.0/{post_id}/comments"

    params = {
        "access_token": ACCESS_TOKEN,
        "summary": "true",
        "filter": "toplevel",
        "limit": limit,
        "fields": "message"
    }

    try:
        resp = requests.get(graph_url, params=params)
        data = resp.json()

        if "error" in data or "data" not in data:
            print("Facebook API error:", data.get("error"))
            return None

        comments = []
        for item in data["data"]:
            msg = item.get("message")
            if msg:
                comments.append(msg)

        return comments

    except Exception as e:
        print("Exception while calling Facebook API:", e)
        return None
