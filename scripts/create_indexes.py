#!/usr/bin/env python3
"""
Create MongoDB Atlas Vector Search and Full-Text Search indexes.

Validates embedding dimension from models.yaml matches index definition.
Fail-fast on dimension mismatch.
"""

import json
import sys
from pathlib import Path

import yaml
from pymongo import MongoClient
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


async def create_indexes() -> None:
    """Create MongoDB Atlas Search indexes."""
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
    uri = settings.mongodb_uri or settings.mongodb_local_uri
    if not uri:
        raise ValueError("No MongoDB URI configured")

    client = MongoClient(uri)
    db = client[settings.mongodb_database]
    collection = db["chunks"]

    # Create indexes
    for idx in index_defs["indexes"]:
        name = idx["name"]
        idx_type = idx["type"]
        definition = idx["definition"]

        print(f"Creating {idx_type} index: {name}...")

        try:
            if idx_type == "vectorSearch":
                # Vector Search index creation via Atlas Admin API
                # Note: This requires Atlas Admin API or manual creation in Atlas UI
                # For programmatic creation, we use the createSearchIndex command
                await db.command(
                    "createSearchIndex",
                    "chunks",
                    name=name,
                    type=idx_type,
                    definition=definition,
                )
            elif idx_type == "search":
                await db.command(
                    "createSearchIndex",
                    "chunks",
                    name=name,
                    type=idx_type,
                    definition=definition,
                )
            print(f"[OK] Index '{name}' created successfully")
        except OperationFailure as e:
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                print(f"[OK] Index '{name}' already exists")
            else:
                print(f"[FAIL] Failed to create index '{name}': {e}")
                raise
        except Exception as e:
            # Some MongoDB deployments don't support createSearchIndex command
            # Fall back to manual instruction
            print(f"[WARN] Could not create index programmatically: {e}")
            print(f"  Please create index '{name}' manually in Atlas UI:")
            print(f"  {json.dumps(definition, indent=2)}")

    client.close()
    print("[OK] All indexes processed")


if __name__ == "__main__":
    import asyncio

    try:
        asyncio.run(create_indexes())
    except Exception as e:
        print(f"[FAIL] Error: {e}", file=sys.stderr)
        sys.exit(1)