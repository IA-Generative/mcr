from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import HTTPException, status
from loguru import logger


@asynccontextmanager
async def relay_upstream_errors(action: str) -> AsyncIterator[None]:
    try:
        yield
    except httpx.HTTPStatusError as e:
        logger.error(
            "HTTP error for {}: {} - {}",
            action,
            e.response.status_code,
            e.response.text,
        )
        raise HTTPException(
            status_code=e.response.status_code, detail=e.response.text
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error for {}: {}", action, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error",
        ) from e
