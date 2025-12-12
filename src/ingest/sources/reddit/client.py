import asyncpraw
from core.config.settings import settings

class RedditClient:
    """
    Low-level Reddit API wrapper.
    NOTE: Business logic should move to ingestor/service later.
    """
    def __init__(self):
        self.reddit = asyncpraw.Reddit(
            client_id=settings.REDDIT_CLIENT_ID,
            client_secret=settings.REDDIT_CLIENT_SECRET,
            user_agent=settings.APP_NAME,
        )

    async def fetch_latest_posts(self, subreddit: str, limit: int = 5):
        subreddit = await self.reddit.subreddit(subreddit)
        posts = []
        async for submission in subreddit.new(limit=limit):
            posts.append(submission)
        return posts
