"""OpenShorts integration for long-form -> multi-clip generation.

Uses the OpenShorts REST API so Stockpile can hand off a local source video,
request a target number of clips, and monitor the asynchronous job.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import httpx


class OpenShortsError(RuntimeError):
    pass


class OpenShortsClient:
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = (base_url or os.getenv("OPENSHORTS_API_URL", "")).rstrip("/")
        self.api_key = api_key or os.getenv("OPENSHORTS_API_KEY", "")

    @property
    def enabled(self) -> bool:
        return bool(self.base_url)

    def _headers(self) -> Dict[str, str]:
        if self.api_key:
            return {"Authorization": f"Bearer {self.api_key}"}
        return {}

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        if not self.enabled:
            raise OpenShortsError("OPENSHORTS_API_URL is not configured")
        headers = dict(self._headers())
        headers.update(kwargs.pop("headers", {}) or {})
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.request(
                method,
                f"{self.base_url}{path}",
                headers=headers,
                **kwargs,
            )
        if response.status_code >= 400:
            try:
                detail = response.json().get("detail") or response.text[:500]
            except Exception:
                detail = response.text[:500]
            raise OpenShortsError(f"OpenShorts HTTP {response.status_code}: {detail}")
        return response

    async def create_upload(self, filename: str) -> Dict[str, Any]:
        response = await self._request(
            "POST",
            "/api/uploads",
            json={"filename": filename},
        )
        return response.json()

    async def upload_file(self, upload_url: str, source_path: Path) -> None:
        def chunks():
            with source_path.open("rb") as handle:
                while True:
                    chunk = handle.read(1024 * 1024)
                    if not chunk:
                        break
                    yield chunk

        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.put(upload_url, content=chunks())
        if response.status_code >= 400:
            raise OpenShortsError(
                f"OpenShorts upload failed with HTTP {response.status_code}: "
                f"{response.text[:500]}"
            )

    async def process_upload(
        self,
        upload_id: str,
        target_clips: Optional[int] = None,
        clip_min_seconds: Optional[float] = None,
        clip_max_seconds: Optional[float] = None,
        captions: bool = True,
        auto_hook: bool = True,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "upload_id": upload_id,
            "acknowledged": True,
            "confirm_rights": True,
            "output_format": "vertical",
            "captions": captions,
            "auto_hook": auto_hook,
        }
        if target_clips is not None:
            body["target_clips"] = target_clips
        if clip_min_seconds is not None:
            body["clip_min_seconds"] = clip_min_seconds
        if clip_max_seconds is not None:
            body["clip_max_seconds"] = clip_max_seconds

        response = await self._request("POST", "/api/process", json=body)
        return response.json()

    async def submit_local_file(
        self,
        source_path: Path,
        target_clips: int = 5,
        clip_min_seconds: float = 15.0,
        clip_max_seconds: float = 60.0,
        captions: bool = True,
        auto_hook: bool = True,
    ) -> Dict[str, Any]:
        if not source_path.exists():
            raise OpenShortsError(f"Source file not found: {source_path}")

        upload = await self.create_upload(source_path.name)
        upload_url = upload.get("upload_url")
        upload_id = upload.get("upload_id")
        if not upload_url or not upload_id:
            raise OpenShortsError("OpenShorts did not return upload_url/upload_id")

        await self.upload_file(upload_url, source_path)
        return await self.process_upload(
            upload_id=upload_id,
            target_clips=max(1, min(15, int(target_clips))),
            clip_min_seconds=clip_min_seconds,
            clip_max_seconds=clip_max_seconds,
            captions=captions,
            auto_hook=auto_hook,
        )

    async def get_status(self, job_id: str) -> Dict[str, Any]:
        response = await self._request("GET", f"/api/status/{job_id}")
        return response.json()


open_shorts_client = OpenShortsClient()
