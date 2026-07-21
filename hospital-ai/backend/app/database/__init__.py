"""Database package — Supabase client access."""

from app.database.supabase import (
    get_supabase_admin_client,
    get_supabase_anon_client,
)

__all__ = ["get_supabase_anon_client", "get_supabase_admin_client"]
