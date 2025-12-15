import asyncio
from core.containers.app_containers import AppContainer
from ingest.sources.reddit.ingestor import RedditIngestor
from core.config.settings import settings

async def main():
    container = AppContainer()
    mongo = container.mongo_client()

    # 레딧 서브레딧 데이터 수집
    ingestor = RedditIngestor(mongo)
    for subreddit in settings.REDDIT_SUBREDDITS:
        await ingestor.run(subreddit)

    
    
    # 연결 테스트
    await mongo.admin.command("ping")

if __name__ == "__main__":
    asyncio.run(main())
