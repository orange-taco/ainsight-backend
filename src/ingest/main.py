import asyncio
from core.containers.app_containers import AppContainer
from ingest.sources.reddit.fetcher import RedditIngestor
from ingest.sources.github.fetcher import GitHubIngestor
from ingest.sources.github.indexes import ensure_indexes
from core.config.settings import settings

async def main():
    container = AppContainer()
    mongo = container.mongo_client()

    db = mongo[settings.MONGO_DB_NAME]

    await ensure_indexes(db)

    # 레딧 서브레딧 데이터 수집
    # reddit_ingestor = RedditIngestor(mongo)
    # for subreddit in settings.REDDIT_SUBREDDITS:
    #     await reddit_ingestor.run(subreddit)

    # 깃허브 리포지토리 데이터 수집
    github_ingestor = GitHubIngestor(mongo, settings.GITHUB_TOKEN)
    github_queries = ["ai OR llm OR agent OR ml OR neural"]
    for query in github_queries:
        await github_ingestor.run(
            query=query, 
            limit=50, 
            min_stars=20, 
            min_size=50, 
            min_pushed_at=180
            )

    # 연결 테스트
    await mongo.admin.command("ping")

if __name__ == "__main__":
    asyncio.run(main())
