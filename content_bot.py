"""
Content Bot - pulls random interesting posts for social media inspiration
=========================================================================

WHAT IT DOES
- Hits Reddit's public JSON endpoints (no login/API key needed) across a
  mix of general-interest subreddits.
- Picks a random sample of 5-10 posts, filtered for quality (min score,
  no NSFW, no stickied/mod posts).
- Prints them nicely + saves to content_ideas.json so you can plug it
  into your site/bot later.

HOW TO RUN
    pip install requests
    python content_bot.py

CUSTOMIZE
- Edit SUBREDDITS list below to match your niche.
- Change HOW_MANY to get more/fewer picks.
- Change TIME_FILTER to 'day' / 'week' / 'month' for how "fresh" posts are.

TWITTER/X (optional, needs paid API - see bottom of file)
- Free tier does NOT allow search/trending pulls anymore.
- Basic tier (~$100/mo) unlocks recent search - code is stubbed at the
  bottom, ready to switch on once you have a key.
"""

import os
import random
import json
import time
import requests

# ---------------- CONFIG ----------------
SUBREDDITS = [
    "todayilearned",
    "interestingasfuck",
    "mildlyinteresting",
    "damnthatsinteresting",
    "UpliftingNews",
    "AskReddit",
    "Showerthoughts",
    "NoStupidQuestions",
]
TIME_FILTER = "day"      # day / week / month
HOW_MANY = 8             # how many posts you want back
MIN_SCORE = 200          # skip low-engagement posts
POSTS_PER_SUB = 10       # how many top posts to fetch per subreddit before filtering

HEADERS = {"User-Agent": "content-bot/1.0 (personal use script)"}

# Reads from environment variable DISCORD_WEBHOOK_URL (set as a GitHub Actions secret).
# For local testing you can also just paste the URL directly here instead.
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")


def fetch_subreddit_top(subreddit: str, limit: int = POSTS_PER_SUB):
    """Fetch top posts from a subreddit for the given time window."""
    url = f"https://www.reddit.com/r/{subreddit}/top.json"
    params = {"limit": limit, "t": TIME_FILTER}
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return [child["data"] for child in data["data"]["children"]]
    except Exception as e:
        print(f"  [!] Couldn't fetch r/{subreddit}: {e}")
        return []


def collect_candidates():
    """Gather posts from all subreddits, filter junk."""
    candidates = []
    for sub in SUBREDDITS:
        print(f"Fetching r/{sub} ...")
        posts = fetch_subreddit_top(sub)
        for p in posts:
            if p.get("stickied"):
                continue
            if p.get("over_18"):
                continue
            if p.get("score", 0) < MIN_SCORE:
                continue
            candidates.append({
                "subreddit": p.get("subreddit_name_prefixed"),
                "title": p.get("title"),
                "score": p.get("score"),
                "comments": p.get("num_comments"),
                "url": f"https://reddit.com{p.get('permalink')}",
                "external_link": p.get("url"),
                "is_self_text": p.get("is_self"),
            })
        time.sleep(1)  # be polite to Reddit's servers
    return candidates


def post_to_discord(picks):
    """Send the picks to a Discord channel via webhook (shows up on phone as a notification)."""
    if not DISCORD_WEBHOOK_URL:
        return
    lines = [f"**📌 Content ideas for today ({len(picks)} picks)**\n"]
    for i, post in enumerate(picks, 1):
        lines.append(
            f"**{i}. [{post['subreddit']}] {post['title']}**\n"
            f"👍 {post['score']} | 💬 {post['comments']} | {post['url']}"
        )
    message = "\n\n".join(lines)
    # Discord has a 2000 character limit per message - split if needed
    chunks = [message[i:i + 1900] for i in range(0, len(message), 1900)]
    for chunk in chunks:
        try:
            requests.post(DISCORD_WEBHOOK_URL, json={"content": chunk}, timeout=10)
        except Exception as e:
            print(f"  [!] Discord post failed: {e}")


def main():
    candidates = collect_candidates()
    if not candidates:
        print("No candidates found - try again later or loosen MIN_SCORE.")
        return

    picks = random.sample(candidates, k=min(HOW_MANY, len(candidates)))

    print("\n" + "=" * 60)
    print(f"YOUR {len(picks)} CONTENT IDEAS FOR TODAY")
    print("=" * 60)
    for i, post in enumerate(picks, 1):
        print(f"\n{i}. [{post['subreddit']}] {post['title']}")
        print(f"   👍 {post['score']} upvotes | 💬 {post['comments']} comments")
        print(f"   🔗 {post['url']}")

    with open("content_ideas.json", "w", encoding="utf-8") as f:
        json.dump(picks, f, indent=2, ensure_ascii=False)
    print("\nSaved to content_ideas.json")

    post_to_discord(picks)


if __name__ == "__main__":
    main()


# =========================================================================
# OPTIONAL: TWITTER/X SECTION (needs a paid API key - Basic tier ~$100/mo)
# =========================================================================
# X's free tier only lets YOUR OWN account post/read its own timeline -
# it can't search or pull trending tweets. To pull trending/topic tweets
# you need at least the Basic tier. Once you have a Bearer Token, this
# is the shape of the code you'd add:
#
# import tweepy
#
# BEARER_TOKEN = "your-bearer-token-here"
# client = tweepy.Client(bearer_token=BEARER_TOKEN)
#
# def fetch_trending_tweets(query="interesting", max_results=10):
#     tweets = client.search_recent_tweets(
#         query=f"{query} -is:retweet lang:en",
#         max_results=max_results,
#         tweet_fields=["public_metrics", "created_at"],
#     )
#     return tweets.data or []
#
# Then merge results into `candidates` the same way as the Reddit posts.
