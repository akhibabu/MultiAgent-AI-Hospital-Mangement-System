from dotenv import load_dotenv
import os
from supabase import create_client

load_dotenv()
url = os.getenv("SUPABASE_URL")
service = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
client = create_client(url, service)

print("=== Auth users ===")
result = client.auth.admin.list_users()
items = result if isinstance(result, list) else getattr(result, "users", None)
if items is None:
    print("raw:", result)
else:
    if not items:
        print("(none)")
    for u in items:
        meta = getattr(u, "user_metadata", None) or {}
        print("id=", u.id)
        print("  email=", u.email)
        print("  created=", u.created_at)
        print("  metadata=", meta)
        print()

print("=== public.users ===")
try:
    rows = client.table("users").select("*").execute()
    if not rows.data:
        print("(none)")
    else:
        for r in rows.data:
            print(r)
except Exception as e:
    print("ERROR reading public.users:", e)
