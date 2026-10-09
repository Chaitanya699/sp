"""
NIM Sentinel Data Analyst Agent

Read-only MongoDB aggregation agent with allowlisted stages, row limits,
and automatic tenant_id filter injection.
"""

import logging
from dataclasses import dataclass
from typing import Any

from nim_sentinel.core.config import get_settings
from nim_sentinel.db.client import get_mongo_client

logger = logging.getLogger(__name__)

# Allowlisted aggregation stages for security
ALLOWED_STAGES = {
    "$match",
    "$project",
    "$group",
    "$sort",
    "$limit",
    "$skip",
    "$lookup",
    "$unwind",
    "$addFields",
    "$set",
    "$unset",
    "$count",
    "$facet",
    "$bucket",
    "$bucketAuto",
    "$sortByCount",
    "$sample",
    "$replaceRoot",
    "$replaceWith",
    "$redact",
    "$graphLookup",
    "$search",  # Atlas Search
    "$vectorSearch",  # Atlas Vector Search
}

# Stages that are NOT allowed (write operations, admin, etc.)
FORBIDDEN_STAGES = {
    "$out",
    "$merge",
    "$planCacheStats",
    "$collStats",
    "$indexStats",
    "$currentOp",
    "$listSessions",
    "$listLocalSessions",
    "$changeStream",
    "$changeStreamSplitLargeEvent",
}


@dataclass
class AnalystQuery:
    """A validated analyst query."""
    collection: str
    pipeline: list[dict[str, Any]]
    tenant_id: str
    max_rows: int = 1000


@dataclass
class AnalystResult:
    """Result of an analyst query execution."""
    data: list[dict[str, Any]]
    row_count: int
    truncated: bool
    execution_time_ms: float
    pipeline_used: list[dict[str, Any]]


class DataAnalystAgent:
    """
    Read-only MongoDB aggregation agent for data analysis.

    Features:
    - Allowlisted aggregation stages only
    - Automatic tenant_id filter injection
    - Row limit enforcement (default 1000, max 10000)
    - Read-only enforcement (no write stages)
    - Query validation and sanitization
    """

    def __init__(
        self,
        max_rows: int = 1000,
        absolute_max_rows: int = 10000,
    ) -> None:
        self.max_rows = max_rows
        self.absolute_max_rows = absolute_max_rows
        self._client = None

    async def _get_client(self):
        """Get MongoDB client."""
        if self._client is None:
            self._client = await get_mongo_client()
        return self._client

    def validate_pipeline(self, pipeline: list[dict[str, Any]]) -> tuple[bool, str]:
        """
        Validate that pipeline only uses allowed stages.

        Returns:
            (is_valid, error_message)
        """
        if not isinstance(pipeline, list):
            return False, "Pipeline must be a list"

        for i, stage in enumerate(pipeline):
            if not isinstance(stage, dict):
                return False, f"Stage {i} must be a dictionary"

            if len(stage) != 1:
                return False, f"Stage {i} must have exactly one key (the stage operator)"

            stage_name = list(stage.keys())[0]

            if stage_name in FORBIDDEN_STAGES:
                return False, f"Forbidden stage: {stage_name}"

            if stage_name not in ALLOWED_STAGES:
                return False, f"Stage not in allowlist: {stage_name}"

            # Additional validation for specific stages
            if stage_name == "$lookup":
                # Validate $lookup structure
                lookup_spec = stage["$lookup"]
                if not isinstance(lookup_spec, dict):
                    return False, "$lookup must be a dictionary"
                if "from" not in lookup_spec:
                    return False, "$lookup requires 'from' field"

            if stage_name == "$match":
                # Ensure no prohibited operators in $match
                match_spec = stage["$match"]
                if not isinstance(match_spec, dict):
                    return False, "$match must be a dictionary"

        return True, ""

    def inject_tenant_filter(self, pipeline: list[dict[str, Any]], tenant_id: str) -> list[dict[str, Any]]:
        """
        Inject tenant_id filter into the pipeline.

        Adds $match stage at the beginning if not present, or merges with existing $match.
        """
        if not pipeline:
            return [{"$match": {"tenant_id": tenant_id}}]

        # Check if first stage is $match
        first_stage = pipeline[0]
        first_stage_name = list(first_stage.keys())[0] if first_stage else None

        if first_stage_name == "$match":
            # Merge tenant_id into existing $match
            existing_match = first_stage["$match"]
            if isinstance(existing_match, dict):
                # Create new match with tenant_id AND existing conditions
                new_match = {"tenant_id": tenant_id}
                # Handle $and if present
                if "$and" in existing_match:
                    new_match["$and"] = [{"tenant_id": tenant_id}] + existing_match["$and"]
                else:
                    # Wrap existing conditions in $and with tenant_id
                    conditions = [{"tenant_id": tenant_id}]
                    for k, v in existing_match.items():
                        conditions.append({k: v})
                    new_match = {"$and": conditions}
                return [{"$match": new_match}] + pipeline[1:]

        # No $match at start, prepend one
        return [{"$match": {"tenant_id": tenant_id}}] + pipeline

    def enforce_row_limit(self, pipeline: list[dict[str, Any]], max_rows: int) -> list[dict[str, Any]]:
        """
        Ensure pipeline has a $limit stage within bounds.
        """
        # Check if $limit already exists
        has_limit = any("$limit" in stage for stage in pipeline)

        if not has_limit:
            # Add $limit at the end
            pipeline = pipeline + [{"$limit": max_rows}]
        else:
            # Find and cap existing $limit
            new_pipeline = []
            for stage in pipeline:
                if "$limit" in stage:
                    current_limit = stage["$limit"]
                    if isinstance(current_limit, int) and current_limit > max_rows:
                        new_pipeline.append({"$limit": max_rows})
                    else:
                        new_pipeline.append(stage)
                else:
                    new_pipeline.append(stage)
            pipeline = new_pipeline

        return pipeline

    def sanitize_pipeline(self, pipeline: list[dict[str, Any]], tenant_id: str, max_rows: int) -> list[dict[str, Any]]:
        """
        Full pipeline sanitization: validate, inject tenant filter, enforce row limit.
        """
        # Validate
        is_valid, error = self.validate_pipeline(pipeline)
        if not is_valid:
            raise ValueError(f"Pipeline validation failed: {error}")

        # Inject tenant filter
        pipeline = self.inject_tenant_filter(pipeline, tenant_id)

        # Enforce row limit
        pipeline = self.enforce_row_limit(pipeline, max_rows)

        return pipeline

    async def execute(
        self,
        collection: str,
        pipeline: list[dict[str, Any]],
        tenant_id: str,
        max_rows: int | None = None,
    ) -> AnalystResult:
        """
        Execute a read-only aggregation query.

        Args:
            collection: Collection name (e.g., "documents", "chunks", "sessions")
            pipeline: Aggregation pipeline (list of stages)
            tenant_id: Tenant ID for isolation
            max_rows: Maximum rows to return (default: self.max_rows, max: self.absolute_max_rows)

        Returns:
            AnalystResult with data and metadata
        """
        import time

        start_time = time.perf_counter()

        # Resolve max_rows
        if max_rows is None:
            max_rows = self.max_rows
        max_rows = min(max_rows, self.absolute_max_rows)

        # Sanitize pipeline
        safe_pipeline = self.sanitize_pipeline(pipeline, tenant_id, max_rows)

        logger.info(
            "DataAnalyst executing query",
            extra={
                "collection": collection,
                "tenant_id": tenant_id,
                "pipeline_stages": len(safe_pipeline),
                "max_rows": max_rows,
            },
        )

        try:
            client = await self._get_client()
            db = client[get_settings().mongodb_database]
            coll = db[collection]

            # Execute aggregation
            cursor = coll.aggregate(safe_pipeline)
            # coll.aggregate returns a coroutine in motor/pymongo async, need to await it
            if hasattr(cursor, '__await__'):
                cursor = await cursor
            data = []
            async for doc in cursor:
                data.append(doc)
                if len(data) >= max_rows:
                    break

            execution_time_ms = (time.perf_counter() - start_time) * 1000
            truncated = len(data) >= max_rows

            logger.info(
                "DataAnalyst query completed",
                extra={
                    "collection": collection,
                    "tenant_id": tenant_id,
                    "rows_returned": len(data),
                    "truncated": truncated,
                    "execution_time_ms": execution_time_ms,
                },
            )

            return AnalystResult(
                data=data,
                row_count=len(data),
                truncated=truncated,
                execution_time_ms=execution_time_ms,
                pipeline_used=safe_pipeline,
            )

        except Exception as e:
            execution_time_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "DataAnalyst query failed",
                extra={
                    "collection": collection,
                    "tenant_id": tenant_id,
                    "error": str(e),
                    "execution_time_ms": execution_time_ms,
                },
            )
            raise

    async def execute_simple(
        self,
        collection: str,
        filter_query: dict[str, Any] | None = None,
        projection: dict[str, Any] | None = None,
        sort: list[tuple[str, int]] | None = None,
        limit: int | None = None,
        tenant_id: str = "",
    ) -> AnalystResult:
        """
        Execute a simple query without writing raw pipeline.

        Args:
            collection: Collection name
            filter_query: Filter conditions (tenant_id auto-added)
            projection: Fields to include/exclude
            sort: Sort specification as list of (field, direction) tuples
            limit: Row limit
            tenant_id: Tenant ID

        Returns:
            AnalystResult
        """
        pipeline = []

        # Build $match
        match_conditions = {}
        if filter_query:
            match_conditions.update(filter_query)
        if tenant_id:
            match_conditions["tenant_id"] = tenant_id
        if match_conditions:
            pipeline.append({"$match": match_conditions})

        # Build $project
        if projection:
            pipeline.append({"$project": projection})

        # Build $sort
        if sort:
            sort_dict = {field: direction for field, direction in sort}
            pipeline.append({"$sort": sort_dict})

        # Build $limit
        if limit:
            pipeline.append({"$limit": limit})

        return await self.execute(collection, pipeline, tenant_id, limit or self.max_rows)


# Global instance
_data_analyst: DataAnalystAgent | None = None


def get_data_analyst() -> DataAnalystAgent:
    """Get the global DataAnalystAgent instance."""
    global _data_analyst
    if _data_analyst is None:
        _data_analyst = DataAnalystAgent()
    return _data_analyst


def reset_data_analyst() -> None:
    """Reset the global DataAnalystAgent (for testing)."""
    global _data_analyst
    _data_analyst = None