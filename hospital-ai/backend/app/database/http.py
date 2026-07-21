"""Shared HTTP client for Supabase REST / Auth calls."""

from functools import lru_cache

import httpx

from app.config import get_settings


@lru_cache
def get_http_client() -> httpx.Client:
    settings = get_settings()
    return httpx.Client(
        timeout=30.0,
        verify=settings.supabase_ssl_verify,
    )
