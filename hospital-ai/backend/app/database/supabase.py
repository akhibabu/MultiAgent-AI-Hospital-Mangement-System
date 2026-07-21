"""Supabase client factories."""

from functools import lru_cache

from supabase import Client, create_client

from app.config import get_settings


@lru_cache
def get_supabase_anon_client() -> Client:
    """Client using the anon key — suitable for Auth sign-in flows."""
    settings = get_settings()
    settings.require_supabase()
    return create_client(settings.supabase_url, settings.supabase_anon_key)


@lru_cache
def get_supabase_admin_client() -> Client:
    """Service-role client — bypasses RLS; never expose to the browser."""
    settings = get_settings()
    settings.require_supabase()
    return create_client(
        settings.supabase_url,
        settings.supabase_service_role_key,
    )
