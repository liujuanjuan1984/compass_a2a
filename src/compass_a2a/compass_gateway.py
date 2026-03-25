from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from .config import Settings
from .principal import CompassPrincipal
from .read_skills import (
    SKILL_REVIEW_FINANCE_STATE,
    SKILL_REVIEW_PLANNING,
    SKILL_REVIEW_TIME_AND_ACTIVITY,
    SKILL_REVIEW_VISION_FOCUS,
    SKILL_SEARCH_PERSONAL_KNOWLEDGE,
)


class CompassGatewayError(Exception):
    pass


@dataclass(slots=True)
class AccessTokenCacheEntry:
    access_token: str
    expires_at: float
    last_used_at: float


class CompassGateway:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._access_tokens: dict[str, AccessTokenCacheEntry] = {}
        self._login_locks: dict[str, asyncio.Lock] = {}
        self._lock_guard = asyncio.Lock()

    async def authenticate(self, principal: CompassPrincipal) -> CompassPrincipal:
        principal.access_token = await self._ensure_access_token(principal)
        return principal

    async def invoke_read_skill(
        self, skill: str, arguments: dict[str, Any], principal: CompassPrincipal
    ) -> str:
        if skill == SKILL_REVIEW_TIME_AND_ACTIVITY:
            return await self._post_agentic("/agentic/timelog", dict(arguments), principal)
        if skill == SKILL_SEARCH_PERSONAL_KNOWLEDGE:
            return await self._post_agentic("/agentic/notes", dict(arguments), principal)
        if skill == SKILL_REVIEW_PLANNING:
            return await self._post_agentic("/agentic/planning", dict(arguments), principal)
        if skill == SKILL_REVIEW_FINANCE_STATE:
            target = arguments.get("target", "accounts")
            if target == "accounts":
                payload = {k: v for k, v in arguments.items() if k != "target"}
                return await self._post_agentic("/agentic/finance/accounts", payload, principal)
            if target == "cashflow":
                payload = {k: v for k, v in arguments.items() if k != "target"}
                return await self._post_agentic("/agentic/finance/cashflow", payload, principal)
            if target == "trading":
                payload = {k: v for k, v in arguments.items() if k != "target"}
                return await self._post_agentic("/agentic/finance/trading", payload, principal)
            raise CompassGatewayError(
                "review_finance_state requires target=accounts|cashflow|trading"
            )
        if skill == SKILL_REVIEW_VISION_FOCUS:
            vision_id = arguments.get("vision_id")
            if not isinstance(vision_id, str) or not vision_id:
                raise CompassGatewayError("review_vision_focus requires vision_id")
            params = {
                "include_subtasks": arguments.get("include_subtasks", True),
                "include_notes": arguments.get("include_notes", True),
                "include_time_records": arguments.get("include_time_records", True),
            }
            return await self._get_agentic(
                f"/agentic/visions/{vision_id}",
                params=params,
                principal=principal,
            )

        raise CompassGatewayError(f"Unsupported skill: {skill}")

    async def execute_write_command(
        self, command: str, arguments: dict[str, Any], principal: CompassPrincipal
    ) -> str:
        del arguments, principal
        raise CompassGatewayError(f"Write command execution is not enabled yet: {command}")

    async def _post_agentic(
        self, path: str, payload: dict[str, Any], principal: CompassPrincipal
    ) -> str:
        data = await self._request("POST", path, principal=principal, json=payload)
        return self._extract_content(data)

    async def _get_agentic(
        self,
        path: str,
        *,
        params: dict[str, Any],
        principal: CompassPrincipal,
    ) -> str:
        data = await self._request("GET", path, principal=principal, params=params)
        return self._extract_content(data)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        principal: CompassPrincipal,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        token = await self._ensure_access_token(principal)
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(
            base_url=self._settings.compass_api_base_url, timeout=30.0
        ) as client:
            response = await client.request(
                method,
                path,
                json=json,
                params=params,
                headers=headers,
            )
            if response.status_code == 401:
                token = await self._refresh_access_token(principal, force=True)
                headers["Authorization"] = f"Bearer {token}"
                response = await client.request(
                    method,
                    path,
                    json=json,
                    params=params,
                    headers=headers,
                )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = self._response_detail(response)
            raise CompassGatewayError(
                f"Compass agentic request failed for {path}: {detail}"
            ) from exc

        return response.json()

    async def _ensure_access_token(self, principal: CompassPrincipal) -> str:
        now = time.time()
        if principal.access_token and not self._is_expired(principal.access_token_expires_at, now):
            return principal.access_token
        principal.access_token = None
        principal.access_token_expires_at = None

        cached = self._get_cached_entry(principal.cache_key, now)
        if cached:
            principal.access_token = cached.access_token
            principal.access_token_expires_at = cached.expires_at
            return cached.access_token

        return await self._refresh_access_token(principal)

    async def _refresh_access_token(
        self, principal: CompassPrincipal, *, force: bool = False
    ) -> str:
        lock = await self._get_login_lock(principal.cache_key)
        async with lock:
            now = time.time()
            self._prune_expired_entries(now)
            cached = self._get_cached_entry(principal.cache_key, now)
            if cached and not force:
                principal.access_token = cached.access_token
                principal.access_token_expires_at = cached.expires_at
                return cached.access_token

            if force:
                self._access_tokens.pop(principal.cache_key, None)
                principal.access_token = None
                principal.access_token_expires_at = None

            payload = {"email": principal.username, "password": principal.password}
            login_path = "/auth/login"
            async with httpx.AsyncClient(
                base_url=self._settings.compass_api_base_url,
                timeout=30.0,
            ) as client:
                response = await client.post(login_path, json=payload)

            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                detail = self._response_detail(response)
                raise CompassGatewayError(
                    f"Compass login failed for {login_path}: {detail}"
                ) from exc

            body = response.json()
            access_token = body.get("access_token")
            if not isinstance(access_token, str) or not access_token:
                raise CompassGatewayError("Compass login response missing access_token")

            expires_at = self._resolve_token_expiration(body, now)
            self._access_tokens[principal.cache_key] = AccessTokenCacheEntry(
                access_token=access_token,
                expires_at=expires_at,
                last_used_at=now,
            )
            self._prune_cache_capacity()
            principal.access_token = access_token
            principal.access_token_expires_at = expires_at
            return access_token

    async def _get_login_lock(self, cache_key: str) -> asyncio.Lock:
        async with self._lock_guard:
            lock = self._login_locks.get(cache_key)
            if lock is None:
                lock = asyncio.Lock()
                self._login_locks[cache_key] = lock
            return lock

    @staticmethod
    def _extract_content(payload: dict[str, Any]) -> str:
        content = payload.get("content")
        if not isinstance(content, str) or not content.strip():
            raise CompassGatewayError("Compass agentic response missing content")
        return content

    @staticmethod
    def _response_detail(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return response.text
        detail = payload.get("detail")
        return detail if isinstance(detail, str) else str(payload)

    def _get_cached_entry(self, cache_key: str, now: float) -> AccessTokenCacheEntry | None:
        entry = self._access_tokens.get(cache_key)
        if entry is None:
            return None
        if self._is_expired(entry.expires_at, now):
            self._access_tokens.pop(cache_key, None)
            return None
        entry.last_used_at = now
        return entry

    def _prune_expired_entries(self, now: float) -> None:
        expired_keys = [
            cache_key
            for cache_key, entry in self._access_tokens.items()
            if self._is_expired(entry.expires_at, now)
        ]
        for cache_key in expired_keys:
            self._access_tokens.pop(cache_key, None)

    def _prune_cache_capacity(self) -> None:
        max_entries = max(1, self._settings.token_cache_max_entries)
        if len(self._access_tokens) <= max_entries:
            return
        overflow = len(self._access_tokens) - max_entries
        lru_entries = sorted(
            self._access_tokens.items(),
            key=lambda item: item[1].last_used_at,
        )
        for cache_key, _ in lru_entries[:overflow]:
            self._access_tokens.pop(cache_key, None)

    def _resolve_token_expiration(self, payload: dict[str, Any], now: float) -> float:
        refresh_skew = max(0, self._settings.token_cache_refresh_skew_seconds)

        expires_at = payload.get("expires_at")
        resolved_expiry = self._parse_explicit_expiration(expires_at)
        if resolved_expiry is not None:
            return max(now + 1, resolved_expiry - refresh_skew)

        expires_in = payload.get("expires_in")
        if isinstance(expires_in, (int, float)) and expires_in > 0:
            return now + max(1, float(expires_in) - refresh_skew)

        default_ttl = max(1, self._settings.token_cache_ttl_seconds - refresh_skew)
        return now + default_ttl

    @staticmethod
    def _parse_explicit_expiration(value: Any) -> float | None:
        if isinstance(value, (int, float)) and value > 0:
            return float(value)
        if isinstance(value, str) and value.strip():
            normalized = value.strip().replace("Z", "+00:00")
            try:
                parsed = datetime.fromisoformat(normalized)
            except ValueError:
                return None
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed.timestamp()
        return None

    @staticmethod
    def _is_expired(expires_at: float | None, now: float) -> bool:
        return expires_at is not None and now >= expires_at
