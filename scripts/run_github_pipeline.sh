#!/bin/bash
set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_DIR="./logs/${TIMESTAMP}"
mkdir -p "${LOG_DIR}"

BUILD=""
if [[ "$1" == "--build" ]]; then
    BUILD="--build --no-cache"
    echo "🔨 Building images..."
fi

docker-compose up -d mongo

echo "Starting GitHub Search Ingestion..."
echo "Logs: ${LOG_DIR}"

# 백그라운드 실행 + 개별 로그 + 터미널 출력
docker-compose up $BUILD search-worker-1 2>&1 | tee "${LOG_DIR}/search-worker-1.log" &
docker-compose up $BUILD search-worker-2 2>&1 | tee "${LOG_DIR}/search-worker-2.log" &
wait

docker-compose rm -f search-worker-1 search-worker-2

echo "Starting README Enrichment..."
docker-compose up $BUILD readme-worker-1 2>&1 | tee "${LOG_DIR}/readme-worker-1.log" &
docker-compose up $BUILD readme-worker-2 2>&1 | tee "${LOG_DIR}/readme-worker-2.log" &
wait

docker-compose rm -f readme-worker-1 readme-worker-2

echo "Pipeline completed!"
echo "Logs saved to: ${LOG_DIR}"
ls -lh "${LOG_DIR}"