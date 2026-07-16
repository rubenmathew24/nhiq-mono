"""Azure Container Apps Jobs control plane for the national orchestrator."""

from __future__ import annotations

import logging
import os
import time
from typing import Any
from urllib.parse import quote

import httpx

logger = logging.getLogger("ingest.orchestrate.azure")

ARM = "https://management.azure.com"
API_VERSION = "2024-03-01"


class AzureJobClient:
    """Minimal ARM client using a service principal (client credentials)."""

    def __init__(
        self,
        *,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        subscription_id: str,
        resource_group: str,
    ) -> None:
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.subscription_id = subscription_id
        self.resource_group = resource_group
        self._token: str | None = None
        self._token_expires = 0.0

    def _ensure_token(self) -> str:
        now = time.time()
        if self._token and now < self._token_expires - 60:
            return self._token
        url = (
            f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        )
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://management.azure.com/.default",
            "grant_type": "client_credentials",
        }
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, data=data)
            resp.raise_for_status()
            body = resp.json()
        self._token = body["access_token"]
        self._token_expires = now + float(body.get("expires_in", 3600))
        return self._token

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._ensure_token()}",
            "Content-Type": "application/json",
        }

    def _job_url(self, job_name: str, suffix: str = "") -> str:
        rg = quote(self.resource_group, safe="")
        name = quote(job_name, safe="")
        base = (
            f"{ARM}/subscriptions/{self.subscription_id}"
            f"/resourceGroups/{rg}"
            f"/providers/Microsoft.App/jobs/{name}"
        )
        return f"{base}{suffix}?api-version={API_VERSION}"

    def get_job(self, job_name: str) -> dict[str, Any]:
        with httpx.Client(timeout=120.0) as client:
            resp = client.get(self._job_url(job_name), headers=self._headers())
            resp.raise_for_status()
            return resp.json()

    def set_env_vars(self, job_name: str, updates: dict[str, str]) -> None:
        """Merge/replace named plain env vars on the first container."""
        job = self.get_job(job_name)
        props = job.get("properties") or {}
        template = props.get("template") or {}
        containers = template.get("containers") or []
        if not containers:
            raise RuntimeError(f"Job {job_name} has no containers")
        container = containers[0]
        env = list(container.get("env") or [])
        names = set(updates)
        new_env = [item for item in env if item.get("name") not in names]
        for name, value in updates.items():
            new_env.append({"name": name, "value": value})
        container["env"] = new_env
        containers[0] = container
        body = {"properties": {"template": {"containers": containers}}}
        with httpx.Client(timeout=180.0) as client:
            resp = client.patch(
                self._job_url(job_name), headers=self._headers(), json=body
            )
            if resp.status_code >= 400:
                logger.error("PATCH %s failed: %s", job_name, resp.text)
            resp.raise_for_status()
        logger.info("Patched %s env keys=%s", job_name, sorted(updates))

    def set_national_batch(self, job_name: str, state_fips: str) -> None:
        self.set_env_vars(
            job_name,
            {
                "INGEST_SCOPE": "national",
                "INGEST_STATE_BATCH": state_fips,
                "INGEST_COUNTY_ALLOWLIST": "",
            },
        )

    def start_job(self, job_name: str) -> str:
        """Start job; return execution name."""
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(
                self._job_url(job_name, "/start"), headers=self._headers()
            )
            if resp.status_code >= 400:
                logger.error("START %s failed: %s", job_name, resp.text)
            resp.raise_for_status()
            body = resp.json() if resp.content else {}
        # Response shape varies; try common fields
        name = (
            body.get("name")
            or (body.get("properties") or {}).get("name")
            or body.get("id", "").rstrip("/").split("/")[-1]
        )
        if not name:
            # Fall back: list executions and take newest
            time.sleep(3)
            name = self._latest_execution_name(job_name)
        logger.info("Started %s execution=%s", job_name, name)
        return name

    def _latest_execution_name(self, job_name: str) -> str:
        url = self._job_url(job_name, "/executions")
        with httpx.Client(timeout=120.0) as client:
            resp = client.get(url, headers=self._headers())
            resp.raise_for_status()
            body = resp.json()
        values = body.get("value") or []
        if not values:
            raise RuntimeError(f"No executions found for {job_name}")
        return values[0]["name"]

    def get_execution_status(self, job_name: str, execution_name: str) -> str:
        enc = quote(execution_name, safe="")
        url = self._job_url(job_name, f"/executions/{enc}")
        with httpx.Client(timeout=120.0) as client:
            resp = client.get(url, headers=self._headers())
            resp.raise_for_status()
            body = resp.json()
        return str((body.get("properties") or {}).get("status") or "Unknown")

    def wait_execution(
        self,
        job_name: str,
        execution_name: str,
        *,
        poll_seconds: int = 30,
        timeout_seconds: int = 7200,
    ) -> str:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            status = self.get_execution_status(job_name, execution_name)
            logger.info("%s/%s status=%s", job_name, execution_name, status)
            if status in ("Succeeded", "Failed", "Stopped"):
                return status
            time.sleep(poll_seconds)
        raise TimeoutError(
            f"Timed out waiting for {job_name}/{execution_name}"
        )


def client_from_env() -> AzureJobClient:
    missing = [
        k
        for k in (
            "AZURE_TENANT_ID",
            "AZURE_CLIENT_ID",
            "AZURE_CLIENT_SECRET",
            "AZURE_SUBSCRIPTION_ID",
            "AZURE_RESOURCE_GROUP",
        )
        if not (os.getenv(k) or "").strip()
    ]
    if missing:
        raise RuntimeError(
            "Orchestrator requires env: " + ", ".join(missing)
        )
    return AzureJobClient(
        tenant_id=os.environ["AZURE_TENANT_ID"].strip(),
        client_id=os.environ["AZURE_CLIENT_ID"].strip(),
        client_secret=os.environ["AZURE_CLIENT_SECRET"].strip(),
        subscription_id=os.environ["AZURE_SUBSCRIPTION_ID"].strip(),
        resource_group=os.environ["AZURE_RESOURCE_GROUP"].strip(),
    )
