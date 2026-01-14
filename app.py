from flask import Flask, render_template, request
from textblob import TextBlob
from utils.youtube import get_youtube_comments_and_title
from utils.instagram_scraper import scrape_instagram_comments
from utils.twitter_scraper import scrape_twitter_replies
import os
import csv

app = Flask(__name__)

# Upload folder for CSV, scraped output, etc.
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# -------------------- HOME PAGE --------------------
@app.route('/')
def home():
    return render_template('index.html')


# -------------------- SENTIMENT FUNCTION --------------------
def analyze_sentiment(comment: str) -> str:
    comment = comment.strip()
    if not comment:
        return "Neutral"

    blob = TextBlob(comment)
    polarity = blob.sentiment.polarity

    if polarity > 0.1:
        return "Positive"
    elif polarity < -0.1:
        return "Negative"
    else:
        return "Neutral"


# -------------------- DASHBOARD --------------------
@app.route('/dashboard', methods=['POST'])
def dashboard_page():
    platform = request.form.get('platform', '').lower()
    url = request.form.get('video_url', '').strip()  # YouTube/Instagram/Twitter URL (optional for CSV platforms)

    comments = []
    video_title = None   # for YouTube

    # ---------- YOUTUBE (DIRECT API) ----------
    if platform == "youtube":
        video_title, comments = get_youtube_comments_and_title(url)
        if comments is None or len(comments) == 0:
            return "Invalid YouTube URL or no comments found."

    # ---------- INSTAGRAM ----------
    elif platform == "instagram":
        # If user provided a URL, try scraping automatically
        if url:
            try:
                csv_path = scrape_instagram_comments(url, output_file="insta_comments.csv", max_comments=200, headless=False, timeout=40, debug=True)


            except Exception as e:
                return f"Instagram scraping error: {e}"

            # read scraped csv
            try:
                with open(csv_path, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if row and row[0].strip():
                            comments.append(row[0].strip())
            except Exception as e:
                return f"Error reading scraped Instagram CSV: {e}"

            if len(comments) == 0:
                return "No comments found by Instagram scraper."

        else:
            # fallback: accept uploaded CSV
            comments_file = request.files.get('comments_file')
            if not comments_file or comments_file.filename == '':
                return "Please provide Instagram URL or upload a comments CSV."
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], comments_file.filename)
            comments_file.save(filepath)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if row and row[0].strip():
                            comments.append(row[0].strip())
            except Exception as e:
                return f"Error reading uploaded CSV: {e}"

    # ---------- TWITTER ----------
    elif platform == "twitter":
        # If user provided a Tweet URL, try scraping automatically
        if url:
            try:
                csv_path = scrape_twitter_replies(url, output_file="twitter_comments.csv", max_comments=400, headless=True)
            except Exception as e:
                return f"Twitter scraping error: {e}"

            # read scraped csv
            try:
                with open(csv_path, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if row and row[0].strip():
                            comments.append(row[0].strip())
            except Exception as e:
                return f"Error reading scraped Twitter CSV: {e}"

            if len(comments) == 0:
                return "No replies/comments found by Twitter scraper."

        else:
            # fallback: accept uploaded CSV
            comments_file = request.files.get('comments_file')
            if not comments_file or comments_file.filename == '':
                return "Please provide Tweet URL or upload a comments CSV."
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], comments_file.filename)
            comments_file.save(filepath)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if row and row[0].strip():
                            comments.append(row[0].strip())
            except Exception as e:
                return f"Error reading uploaded CSV: {e}"

    # ---------- FACEBOOK (CSV only for safety/legal reasons) ----------
    elif platform == "facebook":
        comments_file = request.files.get('comments_file')
        if not comments_file or comments_file.filename == '':
            return "Please upload Facebook comments CSV file."
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], comments_file.filename)
        comments_file.save(filepath)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reader:
                    if row and row[0].strip():
                        comments.append(row[0].strip())
        except Exception as e:
            return f"Error reading Facebook CSV: {e}"

    else:
        return "Currently only YouTube, Facebook, Instagram and Twitter are supported."

    # ---------- if still no comments ----------
    if not comments:
        return "No comments available for analysis."

    # ---------- SENTIMENT ANALYSIS ----------
    positive_count = negative_count = neutral_count = 0
    positive_comments = []
    negative_comments = []
    neutral_comments = []

    for c in comments:
        sentiment = analyze_sentiment(c)

        if sentiment == "Positive":
            positive_count += 1
            positive_comments.append(c)
        elif sentiment == "Negative":
            negative_count += 1
            negative_comments.append(c)
        else:
            neutral_count += 1
            neutral_comments.append(c)

    total_comments = len(comments)

    # ---------- RENDER DASHBOARD ----------
    return render_template(
        'dashboard.html',
        platform=platform,
        url=url,
        video_title=video_title,
        total=total_comments,
        positive=positive_count,
        negative=negative_count,
        neutral=neutral_count,
        pos_list=positive_comments,
        neg_list=negative_comments,
        neu_list=neutral_comments
    )


if __name__ == '__main__':
    app.run(debug=True)
