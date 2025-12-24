### 파일구조
ainsight-backend/
├── .claude/
│   └── settings.local.json
├── docker/
│   ├── readme.Dockerfile
│   ├── search.Dockerfile
│   └── web.Dockerfile
├── docker-compose.yml
├── docs/
│   ├── archiecture.md
│   ├── git-branch-rules.md
│   ├── git-message-rules.md
│   └── github-api-docs.md
├── env/
│   ├── ingest.env
│   ├── mongo.env
│   ├── web.env
│   └── woker.env
├── README.md
├── requirements/
│   ├── base.txt
│   ├── ingest.txt
│   ├── web.dev.txt
│   └── web.txt
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── __pycache__/
│   │   ├── main.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       └── health_router.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── __pycache__/
│   │   ├── config/
│   │   │   ├── __init__.py
│   │   │   └── settings.py
│   │   ├── containers/
│   │   │   ├── __init__.py
│   │   │   ├── __pycache__/
│   │   │   └── app_containers.py
│   │   └── logging/
│   │       ├── __init__.py
│   │       └── logger.py
│   ├── domains/
│   │   └── tmp/
│   │       ├── models.py
│   │       ├── repository.py
│   │       └── service.py
│   └── ingest/
│       ├── __init__.py
│       ├── mappers/
│       │   ├── __init__.py
│       │   └── github_repo_mapper.py
│       ├── models/
│       │   └── document.py
│       └── sources/
│           ├── __init__.py
│           ├── github/
│           │   ├── readme/
│           │   │   ├── main.py
│           │   │   ├── readme_job_generator.py
│           │   │   ├── readme_job_indexes.py
│           │   │   ├── readme_job_schema.py
│           │   │   └── readme_worker.py
│           │   ├── search/
│           │   │   ├── main.py
│           │   │   ├── search_job_generator.py
│           │   │   ├── search_job_indexes.py
│           │   │   ├── search_job_monitor.py
│           │   │   ├── search_job_schema.py
│           │   │   └── search_worker.py
│           │   └── shared/
│           │       ├── client.py
│           │       ├── fetcher.py
│           │       ├── filters.py
│           │       └── repo_indexes.py
│           └── reddit/
│               ├── __init__.py
│               ├── client.py
│               ├── fetcher.py
│               └── mapper.py
└── tests/        # (초기 스냅샷 기준, 지금도 있으면)
    ├── core/
    └── web/