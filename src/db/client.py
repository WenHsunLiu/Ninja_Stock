from dataclasses import dataclass, field
from time import time

from supabase import Client, ClientOptions, create_client

from src.config import settings


def get_supabase_client() -> Client:
    """建立並回傳 Supabase 客戶端連線實例"""
    errors = settings.validate()
    if errors:
        raise ValueError(f"環境設定錯誤: {'; '.join(errors)}")

    options = ClientOptions(auto_refresh_token=False, persist_session=False)
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_PUBLISHABLE_KEY, options)


@dataclass(frozen=True)
class AccessSession:
    access_token: str = field(repr=False)
    expires_at: int


def authorize(client: Client, session: AccessSession, required_role: str) -> Client:
    if session.expires_at <= time():
        raise PermissionError("登入已過期")
    client.postgrest.auth(session.access_token)
    if client.rpc("ninja_stock_role").execute().data != required_role:
        raise PermissionError("此帳號沒有這項操作的權限")
    return client


def sign_in(email: str, password: str, required_role: str) -> tuple[Client, AccessSession]:
    client = get_supabase_client()
    response = client.auth.sign_in_with_password({"email": email, "password": password})
    session = response.session
    if not session or not session.access_token or not session.expires_at:
        raise PermissionError("登入未完成")
    access = AccessSession(session.access_token, session.expires_at)
    return authorize(client, access, required_role), access


def get_market_sync_client() -> Client:
    email = settings.SUPABASE_SYNC_EMAIL
    password = settings.SUPABASE_SYNC_PASSWORD
    if not email or not password:
        raise ValueError("請設定 SUPABASE_SYNC_EMAIL 及 SUPABASE_SYNC_PASSWORD")
    try:
        client, _ = sign_in(email, password, "market_sync")
    except Exception:
        raise PermissionError("無法驗證行情排程帳號及其權限") from None
    return client
