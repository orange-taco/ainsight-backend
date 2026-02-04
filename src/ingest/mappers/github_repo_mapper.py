from datetime import datetime

def map_repo(repo, query: str, bucket: str, pipeline_version: str) -> dict:
    now = datetime.utcnow()

    return {
        # --------------------
        # Identity (절대 변하지 않음)
        # --------------------
        "source": "github",
        "repo_id": repo.id,                 # unique key
        "full_name": repo.full_name,            # owner/name
        "name": repo.name,
        "owner": repo.owner.login,
        "url": repo.html_url,

        # --------------------
        # Signals (cheap, mutable)
        # --------------------
        "signals": {
            "stars": repo.stargazers_count,
            "forks": repo.forks_count,
            "language": repo.language,
            "is_fork": repo.fork,
            "has_topics": bool(repo.topics),
        },

        # --------------------
        # Activity (time-based facts)
        # --------------------
        "activity": {
            "created_at": repo.created_at,
            "updated_at": repo.updated_at,
            "pushed_at": repo.pushed_at,
        },

        # --------------------
        # Raw snapshot (reproducibility)
        # --------------------
        "raw": {
            "search_snapshot": {
                "id": repo.id,
                "full_name": repo.full_name,
                "name": repo.name,
                "owner": repo.owner.login,
                "html_url": repo.html_url,
                "description": repo.description,
                "topics": repo.topics,
                "language": repo.language,
                "stargazers_count": repo.stargazers_count,
                "forks_count": repo.forks_count,
                "created_at": repo.created_at,
                "updated_at": repo.updated_at,
                "pushed_at": repo.pushed_at,
                "fork": repo.fork,
                "archived": repo.archived,
            }
        },
        # --------------------
        # Ingest meta (pipeline trace)
        # --------------------
        "ingest_meta": {
            "bucket": bucket,
            "query": query,
            "ingested_at": now,
            "pipeline_version": pipeline_version,
        },

        # --------------------
        # Enrichment state machine
        # --------------------
        "enrichment": {
            "readme_fetched": False,
            "ai_classified": False,
        },
    }
