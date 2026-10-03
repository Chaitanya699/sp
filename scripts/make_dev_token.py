#!/usr/bin/env python3
"""
Generate a development JWT token for testing.

Usage:
    python scripts/make_dev_token.py --username dev --roles admin --tenant-id tenant-1
    python scripts/make_dev_token.py --username analyst --roles analyst --tenant-id tenant-1
    python scripts/make_dev_token.py --username viewer --roles viewer --tenant-id tenant-1
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nim_sentinel.core.security import create_access_token


def main():
    parser = argparse.ArgumentParser(description="Generate a development JWT token")
    parser.add_argument("--username", default="dev", help="Username for token")
    parser.add_argument("--user-id", default="dev-user-001", help="User ID for token")
    parser.add_argument(
        "--roles",
        nargs="+",
        default=["admin"],
        help="Roles for token (e.g., admin analyst viewer)",
    )
    parser.add_argument("--tenant-id", default="tenant-1", help="Tenant ID for token")
    parser.add_argument("--expires-minutes", type=int, default=60, help="Token expiration in minutes")

    args = parser.parse_args()

    token = create_access_token(
        user_id=args.user_id,
        username=args.username,
        roles=args.roles,
        tenant_id=args.tenant_id,
    )

    print(f"Token for {args.username} ({args.roles}) in tenant {args.tenant_id}:")
    print(token)
    print()
    print("Usage:")
    print(f"  curl -H \"Authorization: Bearer {token}\" http://localhost:8000/v1/health")
    print(f"  curl -H \"Authorization: Bearer {token}\" -F \"file=@test.txt\" http://localhost:8000/v1/documents")
    print(f"  curl -H \"Authorization: Bearer {token}\" -H \"Content-Type: application/json\" -d '{{\"query\": \"test\"}}' http://localhost:8000/v1/query")


if __name__ == "__main__":
    main()