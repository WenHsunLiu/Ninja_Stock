from supabase import create_client, Client
from src.config import settings


def get_supabase_client() -> Client:
    """建立並回傳 Supabase 客戶端連線實例"""
    errors = settings.validate()
    if errors:
        raise ValueError(f"環境設定錯誤: {'; '.join(errors)}")

    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
