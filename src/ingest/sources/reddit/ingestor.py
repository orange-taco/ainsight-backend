from ingest.sources.reddit.client import RedditClient
from ingest.sources.reddit.mapper import map_submission

class RedditIngestor:
    def __init__(self, mongo):
        self.client = RedditClient()
        self.collection = mongo["gitchat"]["documents"]

    async def run(self, subreddit: str):
        posts = await self.client.fetch_latest_posts(subreddit)
        docs = [map_submission(p) for p in posts]

        if docs:
            await self.collection.insert_many(docs, ordered=False)
