"""Async HTTP client for the Print Vault REST API."""

import httpx
import logging

logger = logging.getLogger(__name__)


class PrintVaultClient:
    """Thin async wrapper around httpx for Print Vault API calls."""

    def __init__(self, base_url: str, timeout: int = 30):
        # Ensure base_url doesn't end with a slash for clean joining
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"Accept": "application/json"},
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # -- Core HTTP verbs ------------------------------------------------

    async def get(self, path: str, params: dict | None = None) -> dict | list:
        client = await self._get_client()
        resp = await client.get(path, params=params)
        resp.raise_for_status()
        return resp.json()

    async def post(self, path: str, json: dict | None = None) -> dict | list:
        client = await self._get_client()
        resp = await client.post(path, json=json)
        resp.raise_for_status()
        return resp.json()

    async def patch(self, path: str, json: dict | None = None) -> dict | list:
        client = await self._get_client()
        resp = await client.patch(path, json=json)
        resp.raise_for_status()
        return resp.json()

    async def delete(self, path: str) -> int:
        client = await self._get_client()
        resp = await client.delete(path)
        resp.raise_for_status()
        return resp.status_code
