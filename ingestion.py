"""Official API ingestion. Python standard library only; no scraping."""
import argparse
import json
import os
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DB = Path(__file__).with_name("research.sqlite3")

def request_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "ConsumerEngine/0.1 research"})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.load(response)

def youtube_comments(video_id, api_key, limit=100):
    """YouTube Data API v3 commentThreads.list; top-level comments only."""
    if not api_key:
        raise ValueError("YOUTUBE_API_KEY is required")
    if not video_id or len(video_id) != 11 or not all(c.isalnum() or c in "_-" for c in video_id):
        raise ValueError("Invalid YouTube video ID")
    output, page = [], None
    while len(output) < limit:
        params = {"part": "snippet", "videoId": video_id, "maxResults": min(100, limit-len(output)),
                  "textFormat": "plainText", "key": api_key}
        if page:
            params["pageToken"] = page
        data = request_json("https://www.googleapis.com/youtube/v3/commentThreads?" +
                            urllib.parse.urlencode(params))
        for item in data.get("items", []):
            snippet = item["snippet"]["topLevelComment"]["snippet"]
            output.append({"platform": "youtube", "external_id": item["id"],
                           "url": "https://www.youtube.com/watch?v=" + video_id + "&lc=" + item["id"],
                           "text": snippet.get("textDisplay", ""), "published_at": snippet.get("publishedAt", ""),
                           "context": video_id})
        page = data.get("nextPageToken")
        if not page:
            break
    return output[:limit]

def reddit_posts(subreddit, access_token, limit=100):
    """Reddit OAuth API: /r/{subreddit}/new; read-only access token required."""
    if not access_token:
        raise ValueError("REDDIT_ACCESS_TOKEN is required")
    if not subreddit or not all(c.isalnum() or c == "_" for c in subreddit):
        raise ValueError("Invalid subreddit")
    output, after = [], None
    while len(output) < limit:
        params = {"limit": min(100, limit-len(output)), "raw_json": 1}
        if after:
            params["after"] = after
        url = "https://oauth.reddit.com/r/" + subreddit + "/new?" + urllib.parse.urlencode(params)
        data = request_json(url, {"Authorization": "Bearer " + access_token,
                                  "User-Agent": os.getenv("REDDIT_USER_AGENT", "ConsumerEngine/0.1 (research; contact: repo owner)")})
        for child in data.get("data", {}).get("children", []):
            post = child["data"]
            output.append({"platform": "reddit", "external_id": post["name"],
                           "url": "https://www.reddit.com" + post.get("permalink", ""),
                           "text": (post.get("title", "") + "\n" + post.get("selftext", "")).strip(),
                           "published_at": str(post.get("created_utc", "")), "context": subreddit})
        after = data.get("data", {}).get("after")
        if not after:
            break
    return output[:limit]

def initialize(db_path=DB):
    with sqlite3.connect(db_path) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS observations (
            id INTEGER PRIMARY KEY, platform TEXT NOT NULL, external_id TEXT NOT NULL,
            url TEXT NOT NULL, text TEXT NOT NULL, published_at TEXT,
            context TEXT, collected_at INTEGER NOT NULL,
            UNIQUE(platform, external_id))""")

def store(observations, db_path=DB):
    initialize(db_path)
    inserted = 0
    with sqlite3.connect(db_path) as db:
        for item in observations:
            if not item.get("external_id") or not item.get("text") or not item.get("url"):
                continue
            cursor = db.execute("""INSERT OR IGNORE INTO observations
                (platform, external_id, url, text, published_at, context, collected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (item["platform"], item["external_id"], item["url"], item["text"],
                 item.get("published_at", ""), item.get("context", ""), int(time.time())))
            inserted += cursor.rowcount
    return inserted

def main():
    parser = argparse.ArgumentParser(description="Collect observations using official APIs")
    sub = parser.add_subparsers(dest="source", required=True)
    yt = sub.add_parser("youtube")
    yt.add_argument("--video-id", required=True)
    rd = sub.add_parser("reddit")
    rd.add_argument("--subreddit", required=True)
    for command in (yt, rd):
        command.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    if not 1 <= args.limit <= 500:
        parser.error("--limit must be between 1 and 500")
    try:
        if args.source == "youtube":
            observations = youtube_comments(args.video_id, os.getenv("YOUTUBE_API_KEY"), args.limit)
        else:
            observations = reddit_posts(args.subreddit, os.getenv("REDDIT_ACCESS_TOKEN"), args.limit)
        print(json.dumps({"fetched": len(observations), "new": store(observations)}, indent=2))
    except (ValueError, urllib.error.HTTPError, urllib.error.URLError) as error:
        parser.exit(1, "Ingestion failed: " + str(error) + "\n")

if __name__ == "__main__":
    main()
