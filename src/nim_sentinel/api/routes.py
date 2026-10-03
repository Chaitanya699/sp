"""
NIM Sentinel API Routes

FastAPI endpoints for document ingestion and RAG queries with JWT authentication.
"""

import logging
from typing import Any, Awaitable, Callable

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from nim_sentinel.core.errors import (
    AuthenticationError,
    DocumentError,
    DocumentTooLargeError,
    UnsupportedFileTypeError,
)
from nim_sentinel.core.security import (
    TokenData,
    check_permission,
    decode_token,
    generate_correlation_id,
    sanitize_input,
    validate_file_type,
)
from nim_sentinel.db.client import get_database
from nim_sentinel.db.repositories import (
    get_chunk_repository,
    get_document_repository,
)
from nim_sentinel.rag.ingestion.pipeline import IngestionConfig, IngestionPipeline
from nim_sentinel.rag.retriever import get_hybrid_retriever
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["documents", "query"])

# Security
security = HTTPBearer(auto_error=False)

# Allowed file types for upload
ALLOWED_EXTENSIONS = ["txt", "pdf", "md", "docx", "csv", "json"]
MAX_FILE_SIZE_MB = 50


class QueryRequest(BaseModel):
    """Request model for /v1/query endpoint."""

    query: str = Field(..., min_length=1, max_length=10000, description="Query text")
    top_k: int = Field(default=10, ge=1, le=50, description="Number of results to return")
    filter: dict[str, Any] | None = Field(default=None, description="Optional metadata filters")
    include_citations: bool = Field(default=True, description="Include citations in response")


class QueryResponse(BaseModel):
    """Response model for /v1/query endpoint."""

    query: str
    results: list[dict[str, Any]]
    citations: list[dict[str, Any]] | None = None
    total_results: int
    latency_ms: float


class DocumentUploadResponse(BaseModel):
    """Response model for /v1/documents upload."""

    document_id: str
    filename: str
    status: str
    chunk_count: int
    token_count: int
    message: str


class DocumentListResponse(BaseModel):
    """Response model for /v1/documents list."""

    documents: list[dict[str, Any]]
    total: int
    skip: int
    limit: int


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: dict[str, Any]


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> TokenData:
    """Extract and validate JWT token from Authorization header."""
    if not credentials:
        raise AuthenticationError("Missing Authorization header")

    try:
        token_data = decode_token(credentials.credentials)
        return token_data
    except Exception as e:
        raise AuthenticationError(f"Invalid token: {e}") from e


def require_permission(permission: str) -> Callable[[], Awaitable[TokenData]]:
    """Dependency factory to check if user has required permission."""
    async def _check_permission(
        credentials: HTTPAuthorizationCredentials | None = Depends(security),
    ) -> TokenData:
        if not credentials:
            raise AuthenticationError("Missing Authorization header")
        try:
            user = decode_token(credentials.credentials)
        except Exception as e:
            raise AuthenticationError(f"Invalid token: {e}") from e
        if not check_permission(user.roles, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: requires '{permission}'",
            )
        return user
    return _check_permission


def get_tenant_id(user: TokenData = Depends(get_current_user)) -> str:
    """Extract tenant_id from token, raise if missing."""
    if not user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant ID required for this operation",
        )
    return user.tenant_id


@router.post(
    "/documents",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        415: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def upload_document(
    file: UploadFile = File(...),
    user: TokenData = Depends(require_permission("documents:write")),
    tenant_id: str = Depends(get_tenant_id),
) -> DocumentUploadResponse:
    """
    Upload and ingest a document.

    Supported formats: txt, pdf, md, docx, csv, json
    Max file size: 50MB
    """
    correlation_id = generate_correlation_id()
    logger.info(
        "Document upload started",
        extra={"correlation_id": correlation_id, "file_name": file.filename, "user": user.username},
    )

    # Validate file type
    if not file.filename or not validate_file_type(file.filename, ALLOWED_EXTENSIONS):
        raise UnsupportedFileTypeError(
            mime_type=file.content_type or "unknown",
            allowed=ALLOWED_EXTENSIONS,
        )

    # Read file content
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)

    if size_mb > MAX_FILE_SIZE_MB:
        raise DocumentTooLargeError(size_mb=size_mb, limit_mb=MAX_FILE_SIZE_MB)

    # Determine source type from extension
    ext = file.filename.lower().split(".")[-1] if "." in file.filename else "txt"
    source_type_map = {
        "txt": "text",
        "pdf": "pdf",
        "md": "markdown",
        "docx": "docx",
        "csv": "csv",
        "json": "json",
    }
    source_type = source_type_map.get(ext, "text")

    # Get database and repositories
    db = await get_database()
    doc_repo = get_document_repository(db, tenant_id)
    chunk_repo = get_chunk_repository(db, tenant_id)

    # Check for duplicate by content hash
    import hashlib

    content_hash = hashlib.sha256(content).hexdigest()
    existing = await doc_repo.get_by_content_hash(content_hash)
    if existing:
        logger.info(
            "Duplicate document detected",
            extra={"correlation_id": correlation_id, "document_id": str(existing["_id"])},
        )
        return DocumentUploadResponse(
            document_id=str(existing["_id"]),
            filename=file.filename,
            status="duplicate",
            chunk_count=existing.get("chunk_count", 0),
            token_count=existing.get("token_count", 0),
            message="Document already exists (duplicate content)",
        )

    # Create document record
    document_id = await doc_repo.create_document(
        filename=file.filename,
        source_type=source_type,
        content_hash=content_hash,
        metadata={"uploaded_by": user.username, "correlation_id": correlation_id},
        status="processing",
    )

    try:
        # Update status to processing
        await doc_repo.update_status(document_id, "processing")

        # Get embedding model from model registry
        from nim_sentinel.core.config import get_model_config
        embedding_config = get_model_config("embedding")

        # Run ingestion pipeline
        pipeline = IngestionPipeline(
            tenant_id=tenant_id,
            document_repo=doc_repo,
            chunk_repo=chunk_repo,
            config=IngestionConfig(
                chunk_strategy="semantic",
                embedding_model=embedding_config.primary,
            ),
        )

        result = await pipeline.ingest_bytes(
            content=content,
            filename=file.filename,
            source_type=source_type,
            document_id=document_id,
            metadata={"uploaded_by": user.username},
        )

        # Update document with final stats
        await doc_repo.update_stats(document_id, result.chunk_count, result.token_count)
        await doc_repo.update_status(document_id, "completed")

        logger.info(
            "Document upload completed",
            extra={
                "correlation_id": correlation_id,
                "document_id": document_id,
                "chunks": result.chunk_count,
                "tokens": result.token_count,
            },
        )

        return DocumentUploadResponse(
            document_id=document_id,
            filename=file.filename,
            status="completed",
            chunk_count=result.chunk_count,
            token_count=result.token_count,
            message="Document ingested successfully",
        )

    except Exception as e:
        logger.error(
            "Document ingestion failed",
            extra={"correlation_id": correlation_id, "document_id": document_id, "error": str(e)},
        )
        await doc_repo.update_status(document_id, "failed", error=str(e))
        raise DocumentError(f"Failed to ingest document: {e}") from e


@router.get(
    "/documents",
    response_model=DocumentListResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def list_documents(
    status_filter: str | None = None,
    source_type: str | None = None,
    skip: int = 0,
    limit: int = 20,
    user: TokenData = Depends(require_permission("documents:read")),
    tenant_id: str = Depends(get_tenant_id),
) -> DocumentListResponse:
    """List documents for the current tenant."""
    db = await get_database()
    doc_repo = get_document_repository(db, tenant_id)

    documents = await doc_repo.list_documents(
        status=status_filter,
        source_type=source_type,
        skip=skip,
        limit=limit,
    )

    total = await doc_repo.count({})
    if status_filter:
        total = await doc_repo.count({"status": status_filter})
    if source_type:
        total = await doc_repo.count({"source_type": source_type})

    return DocumentListResponse(
        documents=documents,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/documents/{document_id}",
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def get_document(
    document_id: str,
    user: TokenData = Depends(require_permission("documents:read")),
    tenant_id: str = Depends(get_tenant_id),
) -> dict[str, Any]:
    """Get document details by ID."""
    db = await get_database()
    doc_repo = get_document_repository(db, tenant_id)

    document = await doc_repo.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return document


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def delete_document(
    document_id: str,
    user: TokenData = Depends(require_permission("documents:delete")),
    tenant_id: str = Depends(get_tenant_id),
) -> None:
    """Delete a document and its chunks."""
    db = await get_database()
    doc_repo = get_document_repository(db, tenant_id)
    chunk_repo = get_chunk_repository(db, tenant_id)

    document = await doc_repo.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete chunks first
    await chunk_repo.delete_many({"document_id": document_id})

    # Delete document
    await doc_repo.delete_one({"_id": document_id})

    logger.info("Document deleted", extra={"document_id": document_id, "user": user.username})


@router.post(
    "/query",
    response_model=QueryResponse,
    responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
async def query_documents(
    request: QueryRequest,
    user: TokenData = Depends(require_permission("chat")),
    tenant_id: str = Depends(get_tenant_id),
) -> QueryResponse:
    """
    Query documents using hybrid retrieval (vector + text + rerank).

    Returns top-k relevant chunks with optional citations.
    """
    import time

    start_time = time.perf_counter()
    correlation_id = generate_correlation_id()

    # Sanitize query
    query = sanitize_input(request.query, max_length=10000)

    logger.info(
        "Query received",
        extra={
            "correlation_id": correlation_id,
            "query": query[:100],
            "user": user.username,
            "top_k": request.top_k,
        },
    )

    # Get database and repositories
    db = await get_database()
    chunk_repo = get_chunk_repository(db, tenant_id)

    # Get embedding for query
    from nim_sentinel.rag.ingestion.embedder import get_embedding_client

    embedding_client = await get_embedding_client()
    query_embedding = await embedding_client.embed_query(query)

    # Create retriever and search
    retriever = await get_hybrid_retriever(chunk_repository=chunk_repo)

    # Apply tenant filter
    filter_query = request.filter or {}
    filter_query["tenant_id"] = tenant_id

    results = await retriever.retrieve(
        query=query,
        query_embedding=query_embedding,
        filter_query=filter_query,
    )

    # Limit results
    results = results[: request.top_k]

    # Prepare response
    response_results = []
    citations = []

    for i, result in enumerate(results):
        response_results.append(
            {
                "rank": i + 1,
                "content": result.content,
                "document_id": result.document_id,
                "chunk_index": result.chunk_index,
                "score": result.score,
                "metadata": result.metadata,
                "source": result.source,
            }
        )

        if request.include_citations:
            citations.append(result.to_citation())

    latency_ms = (time.perf_counter() - start_time) * 1000

    logger.info(
        "Query completed",
        extra={
            "correlation_id": correlation_id,
            "results_count": len(results),
            "latency_ms": latency_ms,
        },
    )

    return QueryResponse(
        query=query,
        results=response_results,
        citations=citations if request.include_citations else None,
        total_results=len(results),
        latency_ms=latency_ms,
    )


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "nim-sentinel-api"}
