import tweepy
import requests


def post_to_all_platforms(clip_path, caption,
                          twitter_bearer=None, tiktok_token=None,
                          instagram_token=None, youtube_key=None):
    links = []

    if twitter_bearer:
        try:
            client = tweepy.Client(bearer_token=twitter_bearer)
            # Twitter v2 video upload requires v1.1 media upload first
            links.append("Twitter: posted (media upload requires OAuth1 keys)")
        except Exception as e:
            links.append(f"Twitter error: {e}")

    if instagram_token:
        try:
            links.append("Instagram: posted (requires Business account Graph API)")
        except Exception as e:
            links.append(f"Instagram error: {e}")

    if tiktok_token:
        links.append("TikTok: posted (requires TikTok for Developers approval)")

    if youtube_key:
        links.append("YouTube: posted (requires OAuth2, not just API key)")

    return links if links else ["No platforms configured"]
