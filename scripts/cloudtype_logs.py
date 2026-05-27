"""Cloudtype log streaming CLI.

빌드/실행/터미널 WebSocket 엔드포인트를 콘솔에서 스트리밍한다.
Cloudtype 서버는 WS 연결 직후 `prepare` envelope를 첫 메시지로 받고
`"accept"` 응답 뒤에 텍스트 프레임을 흘려보낸다.

의존성:
    pip install websockets

사용 예:
    python3 cloudtype_logs.py run    --scope myspace --project demo --stage main --deployment web
    python3 cloudtype_logs.py build  --scope myspace --project demo --stage main --deployment web
    python3 cloudtype_logs.py attach --scope myspace --project demo --stage main --deployment web
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from typing import Any, Dict, Optional

try:
    import websockets  # type: ignore
except Exception:  # pragma: no cover - missing dependency
    websockets = None  # type: ignore

DEFAULT_WS_BASE = "wss://api.cloudtype.io"

ENDPOINTS = {
    "run": "/project/logs",
    "build": "/project/build/logs",
    "attach": "/project/attach",
}


def _resolve_token(explicit: Optional[str]) -> str:
    tok = explicit or os.environ.get("CLOUDTYPE_API_KEY")
    if not tok:
        raise SystemExit(
            "Cloudtype API key not found. Set CLOUDTYPE_API_KEY."
        )
    return tok


def _resolve_ws_base(explicit: Optional[str]) -> str:
    return (explicit or os.environ.get("CLOUDTYPE_WS_BASE") or DEFAULT_WS_BASE).rstrip("/")


async def _stream(kind: str, args: argparse.Namespace) -> int:
    if websockets is None:
        sys.stderr.write(
            "websockets 패키지가 필요합니다. `pip install websockets` 후 다시 실행하세요.\n"
        )
        return 3

    token = _resolve_token(args.token)
    base = _resolve_ws_base(args.ws_base)
    url = base + ENDPOINTS[kind]

    prepare: Dict[str, Any] = {
        "type": "prepare",
        "params": {
            "scope": args.scope,
            "project": args.project,
            "stage": args.stage,
            "deployment": args.deployment,
            "options": {
                "follow": True,
                "pretty": False,
                "tailLines": args.tail,
                "previous": False,
                "timestamps": args.timestamps,
            },
        },
        "headers": {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
        },
    }

    async with websockets.connect(url, max_size=None) as ws:  # type: ignore
        await ws.send(json.dumps(prepare))
        try:
            async for frame in ws:
                if isinstance(frame, bytes):
                    sys.stdout.buffer.write(frame)
                    sys.stdout.flush()
                else:
                    sys.stdout.write(frame)
                    if not frame.endswith("\n"):
                        sys.stdout.write("\n")
                    sys.stdout.flush()
        except KeyboardInterrupt:
            pass
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cloudtype-logs", description="Stream Cloudtype logs over WebSocket")
    p.add_argument("--ws-base", help="WebSocket base URL override")
    p.add_argument("--token", help="API token override")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_target(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--scope", required=True)
        sp.add_argument("--project", required=True)
        sp.add_argument("--stage", default="main")
        sp.add_argument("--deployment", required=True)
        sp.add_argument("--tail", type=int, default=500)
        sp.add_argument("--timestamps", action="store_true", default=True)
        sp.add_argument("--no-timestamps", dest="timestamps", action="store_false")

    for kind in ("run", "build", "attach"):
        sp = sub.add_parser(kind, help=f"Stream {kind} logs")
        add_target(sp)
        sp.set_defaults(kind=kind)
    return p


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return asyncio.run(_stream(args.kind, args))


if __name__ == "__main__":
    raise SystemExit(main())
