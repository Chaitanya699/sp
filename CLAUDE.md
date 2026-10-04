# NIM Sentinel - Project Rules

These rules are permanent and must be followed for every task:

1. **MongoDB**: Use only `pymongo.AsyncMongoClient`. Never use Motor (deprecated).
2. **Tests**: Every new module must come with tests. Mock NVIDIA calls in tests.
3. **Task Summary**: At the end of each task, show only: pytest coverage table, mypy result, `git log -n 5`. Then stop.
4. **Commits**: Write commit message once - title + short body. No repetition.
5. **Graphify**: Run only at phase end. Do not commit generated outputs.
6. **Verification**: Never mark as "done" without running it. Show actual run output (errors included).
7. **Secrets**: Never print or commit secrets.

---

## Current Phase: Phase 2 - MongoDB + RAG Implementation

### Completed Tasks:
- Task 1: MongoDB client & repositories with tenant isolation ✓
- Task 2: Ingestion pipeline (parsers, cleaner, chunker, embedder, pipeline) ✓
- Task 3: Hybrid retriever (vector + text + RRF + NVIDIA reranker + citations) ✓
- Task 4: API endpoints (/v1/documents upload, /v1/query with JWT auth) ✓

### Pending Tasks:
- Task 5: Golden retrieval dataset (5-10 docs) with recall@k evaluation
- Task 6: Integration testing with live MongoDB and NVIDIA API