import asyncio
import httpx
from nim_sentinel.main import app
from nim_sentinel.core.security import create_dev_token

async def test_chat_endpoint():
    """Test /v1/chat endpoint with real NVIDIA models."""
    # Use httpx.AsyncClient with the app directly
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as api_client:
        token = create_dev_token(tenant_id='test_tenant', permissions=['chat'])
        headers = {'Authorization': f'Bearer {token}'}

        # First, upload a document
        print("Uploading test document...")
        files = {'file': ('test_chat.txt', b'NIM Sentinel is an enterprise multi-agent RAG system with NVIDIA NIM integration. It provides document ingestion, hybrid retrieval (vector + full-text search), and citation-backed query responses. The system uses MongoDB Atlas for vector storage and Atlas Search for both vector similarity search and full-text search capabilities. Key features include tenant isolation, JWT authentication with RBAC, and integration with NVIDIA NIM models for embeddings, reranking, and generation.', 'text/plain')}

        upload_response = await api_client.post('/v1/documents', headers=headers, files=files)
        print(f"Upload response: {upload_response.status_code}")
        if upload_response.status_code == 201:
            doc_data = upload_response.json()
            print(f"Document uploaded: {doc_data['document_id']}, chunks: {doc_data['chunk_count']}")
        else:
            print(f"Upload failed: {upload_response.text}")
            return

        # Test /v1/chat endpoint
        print("\nTesting /v1/chat endpoint...")
        chat_response = await api_client.post(
            '/v1/chat',
            headers=headers,
            json={
                'query': 'What is NIM Sentinel?',
                'session_id': 'test_session_1',
                'top_k': 5,
                'include_citations': True
            }
        )

        print(f"Chat response: {chat_response.status_code}")
        if chat_response.status_code == 200:
            data = chat_response.json()
            print(f"Query: {data['query']}")
            print(f"Answer: {data['answer'][:200].encode('ascii', 'replace').decode()}...")
            print(f"Confidence: {data['confidence']:.2f}")
            print(f"Total results: {data['total_results']}")
            print(f"Latency: {data['latency_ms']:.1f}ms")
            print(f"Citations: {len(data['citations']) if data['citations'] else 0}")
            for i, c in enumerate(data['citations'] or []):
                print(f"  {i+1}. Score: {c['score']:.4f}, Doc: {c['document_id']}, Chunk: {c['chunk_index']}")
        else:
            print(f"Chat failed: {chat_response.text}")

        # Test /v1/chat/stream endpoint
        print("\nTesting /v1/chat/stream endpoint...")
        async with api_client.stream(
            'POST',
            '/v1/chat/stream',
            headers=headers,
            json={
                'query': 'What are the key features of NIM Sentinel?',
                'session_id': 'test_session_2',
                'top_k': 5,
                'include_citations': True
            }
        ) as stream_response:
            print(f"Stream response: {stream_response.status_code}")
            if stream_response.status_code == 200:
                print("Stream events:")
                async for line in stream_response.aiter_lines():
                    if line:
                        print(f"  {line}")
            else:
                print(f"Stream failed: {await stream_response.aread()}")

if __name__ == "__main__":
    asyncio.run(test_chat_endpoint())