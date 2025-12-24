Phase 1: Search API → 기본 repo 정보 수집 (66,000개)
Phase 2: Core API  → README 콘텐츠 수집

### search api - core api 분리 이유 
1. API 특성 차이: Search API(30 req/min) vs Core API(5000 req/hour)
2. 데이터 크기: Search는 메타데이터, Core는 대용량 텍스트
3. 실패 격리: Search 실패가 README 수집에 영향 없음
4. 재실행 용이: README만 다시 수집 가능