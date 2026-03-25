from __future__ import annotations

import asyncio
from typing import Any

import httpx

from .config import Settings
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
        self._access_token: str | None = None
        self._login_lock = asyncio.Lock()

    async def invoke(self, skill: str, arguments: dict[str, Any]) -> str:
        if skill == SKILL_REVIEW_TIME_AND_ACTIVITY:
            payload = self._with_default_locale(arguments)
            return await self._post_agentic("/agentic/timelog", payload)
        if skill == SKILL_SEARCH_PERSONAL_KNOWLEDGE:
            payload = self._with_default_locale(arguments)
            return await self._post_agentic("/agentic/notes", payload)
        if skill == SKILL_REVIEW_PLANNING:
            payload = self._with_default_locale(arguments)
            return await self._post_agentic("/agentic/planning", payload)
        if skill == SKILL_REVIEW_FINANCE_STATE:
            target = arguments.get("target", "accounts")
            if target == "accounts":
                payload = self._with_default_locale(
                    {k: v for k, v in arguments.items() if k != "target"}
                )
                return await self._post_agentic("/agentic/finance/accounts", payload)
            if target == "cashflow":
                payload = self._with_default_locale(
                    {k: v for k, v in arguments.items() if k != "target"}
                )
                return await self._post_agentic("/agentic/finance/cashflow", payload)
            if target == "trading":
                payload = self._with_default_locale(
                    {k: v for k, v in arguments.items() if k != "target"}
                )
                return await self._post_agentic("/agentic/finance/trading", payload)
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
            return await self._get_agentic(f"/agentic/visions/{vision_id}", params=params)

        raise CompassGatewayError(f"Unsupported skill: {skill}")

    def _with_default_locale(self, arguments: dict[str, Any]) -> dict[str, Any]:
        payload = dict(arguments)
        payload.setdefault("locale", self._settings.default_locale)
        return payload

    async def _post_agentic(self, path: str, payload: dict[str, Any]) -> str:
        data = await self._request("POST", path, json=payload)
        return self._extract_content(data)

    async def _get_agentic(self, path: str, *, params: dict[str, Any]) -> str:
        data = await self._request("GET", path, params=params)
        return self._extract_content(data)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        token = await self._ensure_access_token()
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
                token = await self._refresh_access_token(force=True)
                headers["Authorization"] = f"Bearer {token}"
                response = await client.request(
                    method, path, json=json, params=params, headers=headers
                )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = self._response_detail(response)
            raise CompassGatewayError(
                f"Compass agentic request failed for {path}: {detail}"
            ) from exc

        return response.json()

    async def _ensure_access_token(self) -> str:
        if self._access_token:
            return self._access_token
        return await self._refresh_access_token()

    async def _refresh_access_token(self, *, force: bool = False) -> str:
        if not self._settings.compass_email or not self._settings.compass_password:
            raise CompassGatewayError(
                "Compass credentials are not configured. Set "
                "COMPASS_A2A_COMPASS_EMAIL and COMPASS_A2A_COMPASS_PASSWORD."
            )

        async with self._login_lock:
            if self._access_token and not force:
                return self._access_token

            if force:
                self._access_token = None

            payload = {
                "email": self._settings.compass_email,
                "password": self._settings.compass_password,
            }
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
            self._access_token = access_token
            return access_token

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
