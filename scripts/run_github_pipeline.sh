#!/bin/bash
set -e

# 옵션 처리
BUILD=""
if [[ "$1" == "--build" ]]; then
    BUILD="--build"
    echo "🔨 Building images..."
fi

docker-compose up -d mongo

echo "Starting GitHub Search Ingestion..."
docker-compose up --rm search-worker-1 search-worker-2 $BUILD --abort-on-container-exit

echo "Search completed. Starting README Enrichment..."
docker-compose up --rm readme-worker-1 readme-worker-2 $BUILD --abort-on-container-exit

echo "Pipeline completed!"