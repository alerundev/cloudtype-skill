"""Cloudtype HTTP client (stdlib only).

이 모듈은 다른 에이전트가 Cloudtype API를 호출할 때 사용하는 얇은 래퍼다.
표준 라이브러리만 사용하므로 외부 의존성 설치가 필요 없다.

환경변수:
    CLOUDTYPE_API_KEY   (우선)
    CLOUDTYPE_TESTAPIKEY (대체, 호환 목적)

기본 베이스 URL:
    https://api.cloudtype.io
    (개발 환경: https://api.cloudtype.dev — CLOUDTYPE_API_BASE 로 오버라이드 가능)

규칙(SKILL.md와 일치):
    - 시크릿 GET 은 제공하지 않는다.
    - 시크릿 PUT 은 기본 merge=True 로 강제한다.
    - deployment DELETE 는 제공하지 않는다 (UI 안내).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Iterable, List, Optional, Tuple

DEFAULT_BASE = "https://api.cloudtype.io"
DEV_BASE = "https://api.cloudtype.dev"


class CloudtypeError(RuntimeError):
    """API 호출 실패."""

    def __init__(self, status: int, body: str, url: str):
        super().__init__(f"HTTP {status} {url}: {body[:400]}")
        self.status = status
        self.body = body
        self.url = url


def _resolve_token(explicit: Optional[str]) -> str:
    tok = explicit or os.environ.get("CLOUDTYPE_API_KEY") or os.environ.get("CLOUDTYPE_TESTAPIKEY")
    if not tok:
        raise RuntimeError(
            "Cloudtype API key not found. Set CLOUDTYPE_API_KEY (or CLOUDTYPE_TESTAPIKEY)."
        )
    return tok


def _resolve_base(explicit: Optional[str]) -> str:
    return (explicit or os.environ.get("CLOUDTYPE_API_BASE") or DEFAULT_BASE).rstrip("/")


class CloudtypeClient:
    """얇은 HTTP 래퍼. 모든 메서드는 dict / list / None 을 반환한다."""

    def __init__(
        self,
        token: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self.token = _resolve_token(token)
        self.base_url = _resolve_base(base_url)
        self.timeout = timeout

    # ---- low-level -----------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        *,
        query: Optional[Dict[str, Any]] = None,
        body: Any = None,
    ) -> Any:
        url = self.base_url + path
        if query:
            url += "?" + urllib.parse.urlencode({k: v for k, v in query.items() if v is not None})

        data = None
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
        }
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as e:
            raise CloudtypeError(e.code, e.read().decode("utf-8", "replace"), url) from None
        except urllib.error.URLError as e:
            raise CloudtypeError(0, str(e), url) from None

        if not raw:
            return None
        text = raw.decode("utf-8", "replace")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text

    # ---- auth / scope --------------------------------------------------

    def whoami(self) -> Dict[str, Any]:
        return self._request("GET", "/auth")

    def list_scopes(self, uid: str) -> List[Dict[str, Any]]:
        return self._request("GET", f"/userscope/{uid}/scopes") or []

    def scope_resource_available(self, scope: str) -> Dict[str, Any]:
        return self._request("GET", f"/scope/{scope}/resource/available") or {}

    # ---- project / stage / deployment ---------------------------------

    def list_projects(self, scope: str) -> List[Dict[str, Any]]:
        return self._request("GET", f"/project/{scope}") or []

    def get_project(self, scope: str, project: str) -> Optional[Dict[str, Any]]:
        try:
            return self._request("GET", f"/project/{scope}/{project}")
        except CloudtypeError as e:
            if e.status == 404:
                return None
            raise

    def project_exists(self, scope: str, project: str) -> bool:
        return self.get_project(scope, project) is not None

    def create_project(
        self,
        scope: str,
        name: str,
        *,
        display_name: Optional[str] = None,
        cluster: Optional[str] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {"scope": scope, "name": name}
        if display_name is not None:
            body["displayName"] = display_name
        if cluster is not None:
            body["cluster"] = cluster
        return self._request("POST", "/project", body=body)

    def ensure_project(
        self,
        scope: str,
        name: str,
        *,
        display_name: Optional[str] = None,
        cluster: Optional[str] = None,
    ) -> Dict[str, Any]:
        """project가 없으면 생성, 있으면 그대로 반환."""
        existing = self.get_project(scope, name)
        if existing is not None:
            return existing
        return self.create_project(scope, name, display_name=display_name, cluster=cluster)

    def list_deployments(self, scope: str, project: str, stage: str = "main") -> List[Dict[str, Any]]:
        return self._request(
            "GET",
            f"/project/{scope}/{project}/stage/{stage}/deployment",
        ) or []

    def get_deployment(
        self, scope: str, project: str, stage: str, name: str
    ) -> Optional[Dict[str, Any]]:
        try:
            return self._request(
                "GET",
                f"/project/{scope}/{project}/stage/{stage}/deployment/{name}",
            )
        except CloudtypeError as e:
            if e.status == 404:
                return None
            raise

    def get_deployment_stat(
        self, scope: str, project: str, stage: str, name: str
    ) -> Optional[Dict[str, Any]]:
        return self._request(
            "GET",
            f"/project/{scope}/{project}/stage/{stage}/deployment/{name}/stat",
        )

    def get_events(
        self, scope: str, project: str, stage: str, deployment: str
    ) -> List[Dict[str, Any]]:
        return self._request(
            "GET",
            f"/project/{scope}/{project}/stage/{stage}/events",
            query={"deployment": deployment},
        ) or []

    # ---- deploy / start / stop ----------------------------------------

    def put_deployment(
        self,
        scope: str,
        project: str,
        stage: str,
        request_spec: Dict[str, Any] | Iterable[Dict[str, Any]],
        *,
        owner: Optional[str] = None,
    ) -> Any:
        """PUT /project/{scope}/{project}/stage/{stage}/deployment

        request_spec 은 단일 dict 또는 리스트 형태로 받는다.
        """
        if isinstance(request_spec, dict):
            request_list: List[Dict[str, Any]] = [request_spec]
        else:
            request_list = list(request_spec)
        body: Dict[str, Any] = {"request": request_list}
        if owner is not None:
            body["owner"] = owner
        return self._request(
            "PUT",
            f"/project/{scope}/{project}/stage/{stage}/deployment",
            body=body,
        )

    def start_deployment(self, scope: str, project: str, stage: str, name: str) -> Any:
        return self._request(
            "PUT",
            f"/project/{scope}/{project}/stage/{stage}/deployment/{name}/start",
        )

    def stop_deployment(self, scope: str, project: str, stage: str, name: str) -> Any:
        return self._request(
            "PUT",
            f"/project/{scope}/{project}/stage/{stage}/deployment/{name}/stop",
        )

    # ---- secrets (write only) -----------------------------------------

    def put_secrets(
        self,
        scope: str,
        project: str,
        stage: str,
        secrets: Dict[str, str],
        *,
        merge: bool = True,
    ) -> Any:
        """Stage-level 시크릿 저장. 기본 merge=True 강제(SKILL 정책).

        merge=False 는 사용자가 명시적으로 전체 교체를 원할 때만 호출자가 넘긴다.
        """
        body = {"secrets": secrets, "merge": bool(merge)}
        return self._request(
            "PUT",
            f"/project/{scope}/{project}/stage/{stage}/secret",
            body=body,
        )


# ---- helpers --------------------------------------------------------------

def build_deployment_request(
    *,
    name: str,
    app: str,
    git_url: Optional[str] = None,
    branch: Optional[str] = None,
    preset: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None,
    resources: Optional[Dict[str, Any]] = None,
    path: Optional[str] = None,
) -> Dict[str, Any]:
    """최소 페이로드 빌더.

    사용자가 명시적으로 준 값만 포함한다(Default-first 원칙).
    """
    context: Dict[str, Any] = {}
    if preset:
        context["preset"] = preset
    if git_url:
        git: Dict[str, Any] = {"url": git_url}
        if branch:
            git["branch"] = branch
        if path:
            git["path"] = path
        context["git"] = git

    spec: Dict[str, Any] = {"name": name, "app": app}
    if options:
        spec["options"] = options
    if resources:
        spec["resources"] = resources
    if context:
        spec["context"] = context
    return spec


def mask_secret(value: str, keep: int = 2) -> str:
    if not value:
        return ""
    if len(value) <= keep * 2:
        return "*" * len(value)
    return value[:keep] + "*" * (len(value) - keep * 2) + value[-keep:]
