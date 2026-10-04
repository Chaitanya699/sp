#!/usr/bin/env python3
"""
Validate MongoDB Atlas Vector Search and Full-Text Search indexes.

Validates embedding dimension from models.yaml matches index definition.
Fail-fast on dimension mismatch.
For Atlas: checks index status via listSearchIndexes (does NOT create).
For local MongoDB: creates regular indexes (tenant_id, document_id, text index).
"""

import json
import sys
from pathlib import Path

import yaml
from pymongo import ASCENDING, MongoClient, TEXT
from pymongo.errors import OperationFailure

from nim_sentinel.core.config import get_settings


def load_models_config() -> dict:
    """Load models.yaml configuration."""
    config_path = Path("configs/models.yaml")
    if not config_path.exists():
        raise FileNotFoundError(f"Models config not found: {config_path}")
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_embedding_dimension(models_config: dict) -> int:
    """Get embedding dimension from models.yaml."""
    # Primary embedding model
    embedding_config = models_config.get("model_registry", {}).get("embedding", {})
    primary_model = embedding_config.get("primary", "")

    # Known model dimensions
    model_dimensions = {
        "nvidia/nv-embedqa-e5-v5": 1024,
        "nvidia/llama-3.2-nv-embedqa-1b-v2": 1024,
        "nvidia/nv-embed-v1": 1024,
        "baai/bge-m3": 1024,
        "nvidia/nemotron-3-embed-1b": 2048,
        "nvidia/llama-nemotron-embed-1b-v2": 1024,
        "nvidia/llama-3.2-nv-embedqa-1b-v1": 1024,
        "snowflake/arctic-embed-l": 1024,
    }

    dimension = model_dimensions.get(primary_model)
    if dimension is None:
        # Try fallback
        fallback_model = embedding_config.get("fallback", "")
        dimension = model_dimensions.get(fallback_model)

    if dimension is None:
        raise ValueError(f"Unknown embedding model dimension for: {primary_model}")

    return dimension


def load_index_definitions() -> dict:
    """Load index definitions from JSON."""
    index_path = Path("configs/mongo_indexes/chunks_indexes.json")
    if not index_path.exists():
        raise FileNotFoundError(f"Index definitions not found: {index_path}")
    with open(index_path, encoding="utf-8") as f:
        return json.load(f)


def validate_dimension(index_def: dict, expected_dim: int) -> None:
    """Validate vector index dimension matches expected."""
    vector_fields = [
        f for f in index_def.get("definition", {}).get("fields", [])
        if f.get("type") == "vector"
    ]
    if not vector_fields:
        raise ValueError("No vector field found in index definition")

    actual_dim = vector_fields[0].get("numDimensions")
    if actual_dim != expected_dim:
        raise ValueError(
            f"Dimension mismatch: index defines {actual_dim} dimensions, "
            f"but models.yaml specifies {expected_dim} for embedding model. "
            f"Update configs/mongo_indexes/chunks_indexes.json or configs/models.yaml"
        )
    print(f"[OK] Dimension validated: {actual_dim} dimensions")


def is_atlas_deployment(client: MongoClient) -> bool:
    """Check if connected to MongoDB Atlas."""
    try:
        # Atlas clusters have a specific server version format
        server_info = client.server_info()
        version = server_info.get("version", "")
        # Atlas versions often contain "atlas" or specific patterns
        # Also check for Atlas-specific commands
        return "atlas" in version.lower()
    except Exception:
        return False


def print_manual_instructions(index_defs: dict) -> None:
    """Print manual index creation instructions for Atlas UI."""
    print("\n" + "=" * 60)
    print("MANUAL INDEX CREATION REQUIRED (Atlas UI)")
    print("=" * 60)
    print("Local MongoDB does not support Atlas Search indexes.")
    print("Create these indexes in MongoDB Atlas UI:")
    print("  1. Go to your Atlas cluster -> Search tab -> Create Search Index")
    print("  2. Select 'JSON Editor' and paste each definition below")
    print("  3. Set database: nim_sentinel, collection: chunks")
    print("=" * 60)
    for idx in index_defs["indexes"]:
        print(f"\n--- Index: {idx['name']} ({idx['type']}) ---")
        print(json.dumps(idx["definition"], indent=2))
    print("\n" + "=" * 60)


def check_index_status(db, index_name: str) -> dict | None:
    """Check status of a search index using listSearchIndexes."""
    try:
        # Use listSearchIndexes command to get index status
        result = db.command("listSearchIndexes", "chunks", name=index_name)
        indexes = result.get("cursor", {}).get("firstBatch", [])
        if indexes:
            return indexes[0]
        return None
    except OperationFailure as e:
        if "not found" in str(e).lower() or "does not exist" in str(e).lower():
            return None
        raise


def create_local_indexes(db) -> bool:
    """Create regular MongoDB indexes for local development."""
    print("[INFO] Creating local MongoDB indexes...")

    chunks = db["chunks"]

    # Create compound index for tenant_id + document_id (for chunk retrieval)
    try:
        chunks.create_index([("tenant_id", ASCENDING), ("document_id", ASCENDING)])
        print("[OK] Created index: tenant_id + document_id")
    except Exception as e:
        print(f"[WARN] tenant_id + document_id index: {e}")

    # Create compound index for tenant_id + document_id + chunk_index (ordered chunks)
    try:
        chunks.create_index([("tenant_id", ASCENDING), ("document_id", ASCENDING), ("chunk_index", ASCENDING)])
        print("[OK] Created index: tenant_id + document_id + chunk_index")
    except Exception as e:
        print(f"[WARN] tenant_id + document_id + chunk_index index: {e}")

    # Create index for tenant_id + embedding_model
    try:
        chunks.create_index([("tenant_id", ASCENDING), ("embedding_model", ASCENDING)])
        print("[OK] Created index: tenant_id + embedding_model")
    except Exception as e:
        print(f"[WARN] tenant_id + embedding_model index: {e}")

    # Create text index for content (for regex/text search fallback)
    try:
        chunks.create_index([("content", TEXT)], name="content_text_index")
        print("[OK] Created text index: content")
    except Exception as e:
        print(f"[WARN] content text index: {e}")

    # Create indexes for documents collection
    docs = db["documents"]
    try:
        docs.create_index([("tenant_id", ASCENDING), ("status", ASCENDING)])
        docs.create_index([("tenant_id", ASCENDING), ("created_at", -1)])
        docs.create_index([("tenant_id", ASCENDING), ("source_type", ASCENDING)])
        docs.create_index([("content_hash", ASCENDING)], unique=True, sparse=True)
        print("[OK] Created document indexes")
    except Exception as e:
        print(f"[WARN] document indexes: {e}")

    # Create indexes for sessions collection
    sessions = db["sessions"]
    try:
        sessions.create_index([("tenant_id", ASCENDING), ("user_id", ASCENDING), ("updated_at", -1)])
        sessions.create_index([("tenant_id", ASCENDING), ("status", ASCENDING)])
        sessions.create_index([("thread_id", ASCENDING)], unique=True)
        print("[OK] Created session indexes")
    except Exception as e:
        print(f"[WARN] session indexes: {e}")

    return True


async def validate_indexes() -> int:
    """Validate MongoDB Atlas Search indexes exist and are READY.

    Returns:
        0 on success (all indexes exist and READY), 1 on failure
    """
    settings = get_settings()

    # Load configurations
    models_config = load_models_config()
    expected_dim = get_embedding_dimension(models_config)
    index_defs = load_index_definitions()

    print(f"Embedding dimension from models.yaml: {expected_dim}")

    # Validate dimensions
    for idx in index_defs["indexes"]:
        if idx["type"] == "vectorSearch":
            validate_dimension(idx, expected_dim)

    # Connect to MongoDB
    uri = settings.effective_mongodb_uri
    if not uri:
        raise ValueError("No MongoDB URI configured")

    client = MongoClient(uri)
    db = client[settings.mongodb_database]

    # Check if we're on Atlas
    on_atlas = is_atlas_deployment(client)
    print(f"Connected to: {'Atlas' if on_atlas else 'Local MongoDB'}")

    if not on_atlas:
        print("[INFO] Local MongoDB detected - creating regular indexes")
        create_local_indexes(db)
        print("[OK] Local indexes created successfully")
        client.close()
        return 0

    # On Atlas - check index status
    all_ready = True
    for idx in index_defs["indexes"]:
        name = idx["name"]
        idx_type = idx["type"]

        print(f"Checking {idx_type} index: {name}...")

        index_info = check_index_status(db, name)
        if index_info is None:
            print(f"[FAIL] Index '{name}' does not exist")
            all_ready = False
            continue

        status = index_info.get("status", "UNKNOWN")
        queryable = index_info.get("queryable", False)

        if status == "READY" and queryable:
            print(f"[OK] Index '{name}' is READY and queryable")
        elif status == "BUILDING":
            print(f"[WARN] Index '{name}' is BUILDING (not yet queryable)")
            all_ready = False
        elif status == "FAILED":
            print(f"[FAIL] Index '{name}' build FAILED")
            all_ready = False
        else:
            print(f"[WARN] Index '{name}' status: {status}, queryable: {queryable}")
            if not queryable:
                all_ready = False

    client.close()

    if all_ready:
        print("[OK] All Atlas indexes are READY and queryable")
        return 0
    else:
        print("[FAIL] Some Atlas indexes are not READY")
        return 1


if __name__ == "__main__":
    import asyncio

    try:
        exit_code = asyncio.run(validate_indexes())
        sys.exit(exit_code)
    except Exception as e:
        print(f"[FAIL] Error: {e}", file=sys.stderr)
        sys.exit(1)