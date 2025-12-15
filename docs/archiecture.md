### 파일구조 
ainsight-backend/
├── docker/
│   ├── ingest.Dockerfile
│   └── web.Dockerfile
├── docker-compose.yml
├── docs/
│   ├── git-branch-rules.md
│   └── git-message-rules.md
├── env/
│   ├── ingest.env
│   ├── mongo.env
│   ├── web.env
│   └── web.dev.env
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
│   │   └── db/
│   │       ├── __init__.py
│   │       └── mongo.py
│   ├── domains/
│   │   └── tmp/
│   │       ├── models.py
│   │       ├── repository.py
│   │       └── service.py
│   └── ingest/
│       ├── __init__.py
│       ├── main.py
│       ├── models/
│       │   └── document.py
│       └── sources/
│           ├── __init__.py
│           ├── github/
│           │   ├── client.py
│           │   └── fetcher.py
│           │   └── filter.py
│           │   └── db_indexes.js
│           └── reddit/
│               ├── __init__.py
│               ├── client.py
│               ├── fetcher.py
│               └── mapper.py
└── tests/        # (초기 스냅샷 기준, 지금도 있으면)
    ├── core/
    └── web/