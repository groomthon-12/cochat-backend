from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration_account import IntegrationAccount
from app.models.integration_token import IntegrationToken


async def get_or_create_integration(
    db: AsyncSession,
    provider: str,
    account_identifier: str,
    account_name: str,
) -> IntegrationAccount:
    """provider + account_identifier 조합으로 기존 연동 계정을 조회하고, 없으면 새로 생성."""
    result = await db.execute(
        select(IntegrationAccount).where(
            IntegrationAccount.provider == provider,
            IntegrationAccount.account_identifier == account_identifier,
        )
    )
    integration = result.scalar_one_or_none()

    if integration is None:
        integration = IntegrationAccount(
            provider=provider,
            account_identifier=account_identifier,
            account_name=account_name,
            status="active",
        )
        db.add(integration)
        await db.flush()  # id 확보

    return integration


async def get_or_create_user_integration(
    db: AsyncSession,
    user_id: int,
    provider: str,
    account_identifier: str,
    account_name: str,
) -> IntegrationAccount:
    """Get or create an integration owned by an application user."""
    result = await db.execute(
        select(IntegrationAccount).where(
            IntegrationAccount.user_id == user_id,
            IntegrationAccount.provider == provider,
            IntegrationAccount.account_identifier == account_identifier,
        )
    )
    integration = result.scalar_one_or_none()

    if integration is None:
        integration = IntegrationAccount(
            user_id=user_id,
            provider=provider,
            account_identifier=account_identifier,
            account_name=account_name,
            status="active",
        )
        db.add(integration)
        await db.flush()
        return integration

    integration.account_name = account_name
    integration.status = "active"
    return integration


async def get_integration_by_account(
    db: AsyncSession,
    provider: str,
    account_identifier: str,
) -> IntegrationAccount | None:
    """provider + account_identifier로 연동 계정 조회."""
    result = await db.execute(
        select(IntegrationAccount).where(
            IntegrationAccount.provider == provider,
            IntegrationAccount.account_identifier == account_identifier,
        )
    )
    return result.scalar_one_or_none()


async def get_integration_by_user_account(
    db: AsyncSession,
    user_id: int,
    provider: str,
    account_identifier: str,
) -> IntegrationAccount | None:
    """Look up an integration for a specific application user."""
    result = await db.execute(
        select(IntegrationAccount).where(
            IntegrationAccount.user_id == user_id,
            IntegrationAccount.provider == provider,
            IntegrationAccount.account_identifier == account_identifier,
        )
    )
    return result.scalar_one_or_none()


async def list_integrations_by_user(
    db: AsyncSession,
    user_id: int,
    provider: str | None = None,
) -> list[IntegrationAccount]:
    """List integrations owned by an application user."""
    stmt = select(IntegrationAccount).where(IntegrationAccount.user_id == user_id)
    if provider is not None:
        stmt = stmt.where(IntegrationAccount.provider == provider)
    result = await db.execute(stmt.order_by(IntegrationAccount.created_at.desc()))
    return list(result.scalars().all())


async def get_integration_by_id_for_user(
    db: AsyncSession,
    user_id: int,
    integration_id: int,
    provider: str | None = None,
) -> IntegrationAccount | None:
    """Get a single integration owned by an application user."""
    stmt = select(IntegrationAccount).where(
        IntegrationAccount.id == integration_id,
        IntegrationAccount.user_id == user_id,
    )
    if provider is not None:
        stmt = stmt.where(IntegrationAccount.provider == provider)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def upsert_token(
    db: AsyncSession,
    integration_id: int,
    access_token: str,
    refresh_token: str | None = None,
    expires_at: datetime | None = None,
) -> IntegrationToken:
    """integration_id에 대한 토큰을 저장하거나 갱신."""
    result = await db.execute(
        select(IntegrationToken).where(
            IntegrationToken.integration_id == integration_id
        )
    )
    token = result.scalar_one_or_none()

    if token is None:
        token = IntegrationToken(
            integration_id=integration_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
        )
        db.add(token)
    else:
        token.access_token = access_token
        token.refresh_token = refresh_token
        token.expires_at = expires_at

    return token


async def get_token_by_integration_id(
    db: AsyncSession,
    integration_id: int,
) -> IntegrationToken | None:
    """integration_id에 연결된 저장 토큰 조회."""
    result = await db.execute(
        select(IntegrationToken).where(
            IntegrationToken.integration_id == integration_id
        )
    )
    return result.scalar_one_or_none()
