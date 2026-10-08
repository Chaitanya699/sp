import asyncio
from fastapi.testclient import TestClient
from nim_sentinel.main import app
from nim_sentinel.core.security import create_dev_token
from nim_sentinel.db.client import MongoClient
from nim_sentinel.db.repositories import get_document_repository, get_chunk_repository
from nim_sentinel.rag.ingestion.pipeline import IngestionPipeline, IngestionConfig
from nim_sentinel.rag.ingestion.parsers import get_parser_registry
from nim_sentinel.rag.ingestion.cleaner import clean_text
from nim_sentinel.rag.ingestion.chunker import get_chunker
from nim_sentinel.rag.ingestion.embedder import EmbeddingClient

async def test():
    # Connect to MongoDB
    client = MongoClient()
    await client.connect()

    db = client.database
    doc_repo = get_document_repository(db, 'test_tenant')
    chunk_repo = get_chunk_repository(db, 'test_tenant')

    # Create test document
    test_content = '''
    NIM Sentinel is an enterprise multi-agent RAG system with NVIDIA NIM integration.
    It provides document ingestion, hybrid retrieval (vector + full-text search),
    and citation-backed query responses.

    The system uses MongoDB Atlas for vector storage and Atlas Search for
    both vector similarity search and full-text search capabilities.

    Key features include tenant isolation, JWT authentication with RBAC,
    and integration with NVIDIA NIM models for embeddings, reranking, and generation.
    '''

    import uuid
    unique_hash = f'test_hash_{uuid.uuid4().hex[:12]}'

    doc_id = await doc_repo.create_document(
        filename='test_nim_sentinel.txt',
        source_type='text',
        content_hash=unique_hash,
        metadata={'source': 'integration_test'}
    )

    # Run ingestion pipeline with REAL embeddings
    parser_registry = get_parser_registry()
    # get_parser expects a Path object to check file extension
    from pathlib import Path
    parser = parser_registry.get_parser(Path('test.txt'))
    chunker = get_chunker(strategy='semantic', chunk_size=256, chunk_overlap=50)
    embedding_client = EmbeddingClient(model='nvidia/nemotron-3-embed-1b')

    config = IngestionConfig(
        chunk_strategy='semantic',
        chunk_size=256,
        chunk_overlap=50,
        embedding_model='nvidia/nemotron-3-embed-1b',
    )

    pipeline = IngestionPipeline(
        tenant_id='test_tenant',
        config=config,
        document_repo=doc_repo,
        chunk_repo=chunk_repo,
        embedding_client=embedding_client,
    )

    result = await pipeline.ingest_bytes(
        content=test_content.encode('utf-8'),
        filename='test_nim_sentinel.txt',
        source_type='text',
        document_id=doc_id,
        metadata={'source': 'integration_test'}
    )

    print(f'Created {result.chunk_count} chunks with embeddings')
    print(f'Token count: {result.token_count}')
    print(f'Status: {result.status}')
    print(f'Latency: {result.latency_ms:.1f}ms')

    # Verify chunks stored with embeddings
    chunks = await chunk_repo.get_chunks_by_document(doc_id)
    for chunk in chunks:
        print(f'  Chunk {chunk["chunk_index"]}: embedding dim={len(chunk["embedding"]) if chunk.get("embedding") else 0}, model={chunk.get("embedding_model")}')

    # Now test /v1/query endpoint
    api_client = TestClient(app)
    token = create_dev_token(tenant_id='test_tenant', permissions=['read'])

    response = api_client.post(
        '/v1/query',
        headers={'Authorization': f'Bearer {token}'},
        json={'query': 'What is NIM Sentinel?', 'top_k': 5},
    )

    print(f'\nQuery response: {response.status_code}')
    data = response.json()
    print(f'Query: {data["query"]}')
    print(f'Total results: {data["total_results"]}')
    print(f'Latency: {data["latency_ms"]}ms')
    print(f'Citations: {len(data["citations"])}')
    for i, c in enumerate(data['citations']):
        print(f'  {i+1}. Score: {c["score"]:.4f}, Doc: {c["document_id"]}, Chunk: {c["chunk_index"]}')
        print(f'     Content: {c["content"][:100]}...')

    await client.disconnect()

asyncio.run(test())