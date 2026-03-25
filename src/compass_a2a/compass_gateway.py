from __future__ import annotations

import asyncio
from typing import Any

import httpx

from .config import Settings
from .principal import CompassPrincipal
from .skills import (
    SKILL_REVIEW_FINANCE_STATE,
    SKILL_REVIEW_PLANNING,
    SKILL_REVIEW_TIME_AND_ACTIVITY,
    SKILL_REVIEW_VISION_FOCUS,
    SKILL_SEARCH_PERSONAL_KNOWLEDGE,
)


class CompassGatewayError(Exception):
    pass


class CompassGateway:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._access_tokens: dict[str, str] = {}
        self._login_locks: dict[str, asyncio.Lock] = {}
        self._lock_guard = asyncio.Lock()

    async def authenticate(self, principal: CompassPrincipal) -> CompassPrincipal:
        principal.access_token = await self._ensure_access_token(principal)
        return principal

    async def invoke(
        self, skill: str, arguments: dict[str, Any], principal: CompassPrincipal
    ) -> str:
        if skill == SKILL_REVIEW_TIME_AND_ACTIVITY:
            payload = self._with_default_locale(arguments)
            return await self._post_agentic("/agentic/timelog", payload, principal)
        if skill == SKILL_SEARCH_PERSONAL_KNOWLEDGE:
            payload = self._with_default_locale(arguments)
            return await self._post_agentic("/agentic/notes", payload, principal)
        if skill == SKILL_REVIEW_PLANNING:
            payload = self._with_default_locale(arguments)
            return await self._post_agentic("/agentic/planning", payload, principal)
        if skill == SKILL_REVIEW_FINANCE_STATE:
            target = arguments.get("target", "accounts")
            if target == "accounts":
                payload = self._with_default_locale(
                    {k: v for k, v in arguments.items() if k != "target"}
                )
                return await self._post_agentic("/agentic/finance/accounts", payload, principal)
            if target == "cashflow":
                payload = self._with_default_locale(
                    {k: v for k, v in arguments.items() if k != "target"}
                )
                return await self._post_agentic("/agentic/finance/cashflow", payload, principal)
            if target == "trading":
                payload = self._with_default_locale(
                    {k: v for k, v in arguments.items() if k != "target"}
                )
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

    def _with_default_locale(self, arguments: dict[str, Any]) -> dict[str, Any]:
        payload = dict(arguments)
        payload.setdefault("locale", self._settings.default_locale)
        return payload

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
        if principal.access_token:
            return principal.access_token

        cached = self._access_tokens.get(principal.cache_key)
        if cached:
            principal.access_token = cached
            return cached

        return await self._refresh_access_token(principal)

    async def _refresh_access_token(
        self, principal: CompassPrincipal, *, force: bool = False
    ) -> str:
        lock = await self._get_login_lock(principal.cache_key)
        async with lock:
            cached = self._access_tokens.get(principal.cache_key)
            if cached and not force:
                principal.access_token = cached
                return cached

            if force:
                self._access_tokens.pop(principal.cache_key, None)
                principal.access_token = None

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

            self._access_tokens[principal.cache_key] = access_token
            principal.access_token = access_token
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
