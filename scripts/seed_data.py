#!/usr/bin/env python3
"""
Seed sample sales/orders documents with tenant_id for testing data analyst agent.

This script creates sample documents with sales data that can be queried
using the DataAnalystAgent with MongoDB aggregation pipelines.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nim_sentinel.db.client import get_database
from nim_sentinel.db.repositories import get_document_repository, get_chunk_repository
from nim_sentinel.rag.ingestion.pipeline import IngestionPipeline, IngestionConfig
from nim_sentinel.core.config import get_model_config


# Sample sales data
SALES_DOCUMENTS = [
    {
        "filename": "q1_2024_sales_report.txt",
        "content": """Q1 2024 Sales Report - Tenant: acme_corp

Executive Summary:
Total Revenue: $2,450,000
Total Orders: 1,247
Average Order Value: $1,965
Top Product Category: Enterprise Software (45% of revenue)

Monthly Breakdown:
January 2024: $780,000 (412 orders)
February 2024: $820,000 (425 orders)
March 2024: $850,000 (410 orders)

Top Products:
1. NIM Sentinel Enterprise License - $1,100,000 (500 licenses)
2. NIM Sentinel Professional License - $650,000 (650 licenses)
3. NIM Sentinel Starter License - $300,000 (300 licenses)
4. Professional Services - $400,000 (40 engagements)

Regional Performance:
- North America: $1,200,000 (49%)
- Europe: $750,000 (31%)
- APAC: $500,000 (20%)

Key Metrics:
- Customer Acquisition Cost: $2,500
- Customer Lifetime Value: $45,000
- Churn Rate: 2.1% (quarterly)
- Net Revenue Retention: 115%
""",
        "source_type": "text",
    },
    {
        "filename": "q2_2024_sales_report.txt",
        "content": """Q2 2024 Sales Report - Tenant: acme_corp

Executive Summary:
Total Revenue: $2,890,000
Total Orders: 1,456
Average Order Value: $1,985
Top Product Category: Enterprise Software (48% of revenue)

Monthly Breakdown:
April 2024: $920,000 (465 orders)
May 2024: $980,000 (490 orders)
June 2024: $990,000 (501 orders)

Top Products:
1. NIM Sentinel Enterprise License - $1,350,000 (580 licenses)
2. NIM Sentinel Professional License - $780,000 (780 licenses)
3. NIM Sentinel Starter License - $360,000 (360 licenses)
4. Professional Services - $400,000 (40 engagements)

Regional Performance:
- North America: $1,450,000 (50%)
- Europe: $880,000 (30%)
- APAC: $560,000 (19%)

Key Metrics:
- Customer Acquisition Cost: $2,300
- Customer Lifetime Value: $48,000
- Churn Rate: 1.8% (quarterly)
- Net Revenue Retention: 118%

Growth: +18% QoQ revenue growth
""",
        "source_type": "text",
    },
    {
        "filename": "q3_2024_sales_report.txt",
        "content": """Q3 2024 Sales Report - Tenant: acme_corp

Executive Summary:
Total Revenue: $3,120,000
Total Orders: 1,580
Average Order Value: $1,975
Top Product Category: Enterprise Software (50% of revenue)

Monthly Breakdown:
July 2024: $1,020,000 (515 orders)
August 2024: $1,050,000 (530 orders)
September 2024: $1,050,000 (535 orders)

Top Products:
1. NIM Sentinel Enterprise License - $1,500,000 (620 licenses)
2. NIM Sentinel Professional License - $850,000 (850 licenses)
3. NIM Sentinel Starter License - $370,000 (370 licenses)
4. Professional Services - $400,000 (40 engagements)

Regional Performance:
- North America: $1,580,000 (51%)
- Europe: $950,000 (30%)
- APAC: $590,000 (19%)

Key Metrics:
- Customer Acquisition Cost: $2,100
- Customer Lifetime Value: $52,000
- Churn Rate: 1.5% (quarterly)
- Net Revenue Retention: 122%

Growth: +8% QoQ revenue growth
""",
        "source_type": "text",
    },
    {
        "filename": "q4_2024_sales_report.txt",
        "content": """Q4 2024 Sales Report - Tenant: acme_corp

Executive Summary:
Total Revenue: $3,580,000
Total Orders: 1,790
Average Order Value: $2,000
Top Product Category: Enterprise Software (52% of revenue)

Monthly Breakdown:
October 2024: $1,150,000 (570 orders)
November 2024: $1,200,000 (600 orders)
December 2024: $1,230,000 (620 orders)

Top Products:
1. NIM Sentinel Enterprise License - $1,800,000 (700 licenses)
2. NIM Sentinel Professional License - $950,000 (950 licenses)
3. NIM Sentinel Starter License - $430,000 (430 licenses)
4. Professional Services - $400,000 (40 engagements)

Regional Performance:
- North America: $1,850,000 (52%)
- Europe: $1,050,000 (29%)
- APAC: $680,000 (19%)

Key Metrics:
- Customer Acquisition Cost: $1,950
- Customer Lifetime Value: $55,000
- Churn Rate: 1.2% (quarterly)
- Net Revenue Retention: 125%

Growth: +15% QoQ revenue growth
Annual 2024 Total: $12,040,000 (+22% YoY)
""",
        "source_type": "text",
    },
    {
        "filename": "customer_orders_2024.txt",
        "content": """Customer Orders 2024 - Tenant: acme_corp

Major Customer Orders:

1. TechCorp Industries
   - Order ID: ORD-2024-001
   - Date: 2024-01-15
   - Product: NIM Sentinel Enterprise License (100 licenses)
   - Value: $220,000
   - Region: North America
   - Status: Completed

2. Global Finance Ltd
   - Order ID: ORD-2024-002
   - Date: 2024-02-20
   - Product: NIM Sentinel Enterprise License (150 licenses)
   - Value: $330,000
   - Region: Europe
   - Status: Completed

3. HealthTech Solutions
   - Order ID: ORD-2024-003
   - Date: 2024-03-10
   - Product: NIM Sentinel Professional License (200 licenses)
   - Value: $200,000
   - Region: North America
   - Status: Completed

4. RetailMax Group
   - Order ID: ORD-2024-004
   - Date: 2024-04-05
   - Product: NIM Sentinel Enterprise License (80 licenses)
   - Value: $176,000
   - Region: APAC
   - Status: Completed

5. Manufacturing Plus
   - Order ID: ORD-2024-005
   - Date: 2024-05-12
   - Product: NIM Sentinel Enterprise License (120 licenses)
   - Value: $264,000
   - Region: North America
   - Status: Completed

6. EduTech Systems
   - Order ID: ORD-2024-006
   - Date: 2024-06-18
   - Product: NIM Sentinel Professional License (300 licenses)
   - Value: $300,000
   - Region: Europe
   - Status: Completed

7. LogisticsHub Inc
   - Order ID: ORD-2024-007
   - Date: 2024-07-22
   - Product: NIM Sentinel Enterprise License (90 licenses)
   - Value: $198,000
   - Region: North America
   - Status: Completed

8. MediaStream Co
   - Order ID: ORD-2024-008
   - Date: 2024-08-30
   - Product: NIM Sentinel Professional License (250 licenses)
   - Value: $250,000
   - Region: APAC
   - Status: Completed

9. EnergyGrid Corp
   - Order ID: ORD-2024-009
   - Date: 2024-09-14
   - Product: NIM Sentinel Enterprise License (110 licenses)
   - Value: $242,000
   - Region: Europe
   - Status: Completed

10. FinServe Partners
    - Order ID: ORD-2024-010
    - Date: 2024-10-25
    - Product: NIM Sentinel Enterprise License (130 licenses)
    - Value: $286,000
    - Region: North America
    - Status: Completed

Total Major Orders: $2,466,000 (10 orders)
Average Major Order: $246,600
""",
        "source_type": "text",
    },
    {
        "filename": "product_catalog.txt",
        "content": """NIM Sentinel Product Catalog - Tenant: acme_corp

Product Line: NIM Sentinel

1. NIM Sentinel Starter License
   - SKU: NIM-STARTER
   - Price per license: $1,000/year
   - Target: Small teams (1-10 users)
   - Features: Basic RAG, 10K documents, Community support
   - Category: Software License

2. NIM Sentinel Professional License
   - SKU: NIM-PRO
   - Price per license: $1,000/year
   - Target: Growing teams (10-100 users)
   - Features: Advanced RAG, 100K documents, Email support, SSO
   - Category: Software License

3. NIM Sentinel Enterprise License
   - SKU: NIM-ENT
   - Price per license: $2,200/year
   - Target: Large organizations (100+ users)
   - Features: Full RAG, Unlimited documents, 24/7 support, SSO, Audit logs, Custom models
   - Category: Software License

4. Professional Services
   - SKU: NIM-PRO-SVC
   - Price: $10,000/engagement
   - Services: Implementation, Custom integration, Training, Optimization
   - Category: Services

5. NIM Sentinel Data Analyst Add-on
   - SKU: NIM-DA-ADDON
   - Price per license: $500/year
   - Features: MongoDB aggregation queries, Read-only analytics, Tenant isolation
   - Category: Add-on

Pricing Notes:
- Volume discounts available for 500+ licenses
- Multi-year contracts: 10% discount (2-year), 15% discount (3-year)
- Non-profit and educational discounts: 25% off
""",
        "source_type": "text",
    },
]


async def seed_data(tenant_id: str = "acme_corp"):
    """Seed sample sales documents for a tenant."""
    print(f"Seeding data for tenant: {tenant_id}")

    # Get database and repositories
    db = await get_database()
    doc_repo = get_document_repository(db, tenant_id)
    chunk_repo = get_chunk_repository(db, tenant_id)

    # Get embedding model config
    embedding_config = get_model_config("embedding")

    # Create ingestion pipeline
    pipeline = IngestionPipeline(
        tenant_id=tenant_id,
        document_repo=doc_repo,
        chunk_repo=chunk_repo,
        config=IngestionConfig(
            chunk_strategy="semantic",
            embedding_model=embedding_config.primary,
        ),
    )

    # Ingest each document
    for i, doc_data in enumerate(SALES_DOCUMENTS):
        print(f"\n[{i+1}/{len(SALES_DOCUMENTS)}] Ingesting: {doc_data['filename']}")

        try:
            # Create document record first
            import hashlib
            content_bytes = doc_data["content"].encode("utf-8")
            content_hash = hashlib.sha256(content_bytes).hexdigest()

            # Check for duplicate
            existing = await doc_repo.get_by_content_hash(content_hash)
            if existing:
                print(f"  Document already exists (duplicate): {existing['_id']}")
                continue

            document_id = await doc_repo.create_document(
                filename=doc_data["filename"],
                source_type=doc_data["source_type"],
                content_hash=content_hash,
                metadata={"seeded": True, "category": "sales"},
                status="processing",
            )

            result = await pipeline.ingest_bytes(
                content=content_bytes,
                filename=doc_data["filename"],
                source_type=doc_data["source_type"],
                document_id=document_id,
                metadata={"seeded": True, "category": "sales"},
            )

            print(f"  Document ID: {result.document_id}")
            print(f"  Chunks: {result.chunk_count}")
            print(f"  Tokens: {result.token_count}")
            print(f"  Status: {result.status}")

        except Exception as e:
            print(f"  ERROR: {e}")

    print(f"\nSeeding complete for tenant: {tenant_id}")
    print(f"   Total documents: {len(SALES_DOCUMENTS)}")


async def verify_seeded_data(tenant_id: str = "acme_corp"):
    """Verify seeded data by querying."""
    print(f"\nVerifying seeded data for tenant: {tenant_id}")

    db = await get_database()
    doc_repo = get_document_repository(db, tenant_id)
    chunk_repo = get_chunk_repository(db, tenant_id)

    # List documents
    documents = await doc_repo.list_documents(limit=50)
    print(f"\nDocuments found: {len(documents)}")
    for doc in documents:
        print(f"  - {doc.get('filename', 'N/A')}: {doc.get('chunk_count', 0)} chunks, status={doc.get('status', 'N/A')}")

    # Count chunks
    from nim_sentinel.core.constants import COLLECTION_CHUNKS
    chunk_count = await db[COLLECTION_CHUNKS].count_documents({"tenant_id": tenant_id})
    print(f"\nTotal chunks in database: {chunk_count}")


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Seed sample sales data")
    parser.add_argument("--tenant", default="acme_corp", help="Tenant ID")
    parser.add_argument("--verify-only", action="store_true", help="Only verify existing data")
    args = parser.parse_args()

    if args.verify_only:
        await verify_seeded_data(args.tenant)
    else:
        await seed_data(args.tenant)
        await verify_seeded_data(args.tenant)


if __name__ == "__main__":
    asyncio.run(main())