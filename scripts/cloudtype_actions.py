"""Cloudtype actions CLI.

스킬 정책에 맞춰 안전한 액션만 제공:
    - whoami / list / status / events
    - project ensure / create
    - deploy (create/update/redeploy 동일 PUT)
    - start / stop
    - secret put (merge=true 기본)

명시적으로 제공하지 않는 것:
    - deployment DELETE   (UI에서 직접)
    - secret GET          (UI에서 직접)

사용 예:
    python3 cloudtype_actions.py whoami
    python3 cloudtype_actions.py ensure-project --scope myspace --name my-project
    python3 cloudtype_actions.py deploy --scope myspace --project my-project \\
        --stage main --name web --app web --preset html \\
        --git https://github.com/alerundev/demo-fruit-shop.git --branch main \\
        --option docbase=/ --option spa=true --option ports=8080
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

try:
    from cloudtype_client import (
        CloudtypeClient,
        CloudtypeError,
        build_deployment_request,
    )
except ImportError:  # pragma: no cover - direct invocation fallback
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, here)
    from cloudtype_client import (  # type: ignore
        CloudtypeClient,
        CloudtypeError,
        build_deployment_request,
    )


def _print_json(obj: Any) -> None:
    json.dump(obj, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


def _parse_kv(items: List[str]) -> Dict[str, Any]:
    """`--option key=value` 들을 dict로. 간단한 타입 추론(true/false/int/float/json) 지원."""
    out: Dict[str, Any] = {}
    for raw in items or []:
        if "=" not in raw:
            raise SystemExit(f"--option/--resource expects key=value: got {raw!r}")
        k, v = raw.split("=", 1)
        k = k.strip()
        v = v.strip()
        if v.lower() == "true":
            out[k] = True
        elif v.lower() == "false":
            out[k] = False
        else:
            try:
                out[k] = int(v)
                continue
            except ValueError:
                pass
            try:
                out[k] = float(v)
                continue
            except ValueError:
                pass
            if v and v[0] in "[{":
                try:
                    out[k] = json.loads(v)
                    continue
                except json.JSONDecodeError:
                    pass
            out[k] = v
    return out


def _parse_env_pairs(items: List[str], *, kind: str) -> List[Dict[str, str]]:
    """`NAME=value` 또는 `NAME=secret:KEY` 형식의 env/buildenv 항목."""
    out: List[Dict[str, str]] = []
    for raw in items or []:
        if "=" not in raw:
            raise SystemExit(f"--{kind} expects NAME=value or NAME=secret:KEY (got {raw!r})")
        name, value = raw.split("=", 1)
        if value.startswith("secret:"):
            out.append({"name": name, "secret": value[len("secret:") :]})
        else:
            out.append({"name": name, "value": value})
    return out


def cmd_whoami(client: CloudtypeClient, args: argparse.Namespace) -> int:
    _print_json(client.whoami())
    return 0


def cmd_list_deployments(client: CloudtypeClient, args: argparse.Namespace) -> int:
    deps = client.list_deployments(args.scope, args.project, args.stage)
    if args.json:
        _print_json(deps)
        return 0
    for d in deps:
        name = d.get("name", "?")
        status = (d.get("stat") or {}).get("status", "?")
        ready = (d.get("stat") or {}).get("ready", "?")
        replicas = (d.get("stat") or {}).get("replicas", "?")
        print(f"{name:30}  {status:12}  {ready}/{replicas}")
    return 0


def cmd_status(client: CloudtypeClient, args: argparse.Namespace) -> int:
    stat = client.get_deployment_stat(args.scope, args.project, args.stage, args.name)
    _print_json(stat)
    return 0


def cmd_events(client: CloudtypeClient, args: argparse.Namespace) -> int:
    _print_json(client.get_events(args.scope, args.project, args.stage, args.name))
    return 0


def cmd_ensure_project(client: CloudtypeClient, args: argparse.Namespace) -> int:
    proj = client.ensure_project(
        args.scope,
        args.name,
        display_name=args.display_name,
        cluster=args.cluster,
    )
    _print_json(proj)
    return 0


def cmd_create_project(client: CloudtypeClient, args: argparse.Namespace) -> int:
    proj = client.create_project(
        args.scope,
        args.name,
        display_name=args.display_name,
        cluster=args.cluster,
    )
    _print_json(proj)
    return 0


def cmd_deploy(client: CloudtypeClient, args: argparse.Namespace) -> int:
    # project 부재 시 우선 생성 (스킬 정책: A-0)
    if args.ensure_project:
        client.ensure_project(args.scope, args.project, display_name=args.project_display_name)

    options = _parse_kv(args.option or [])
    env = _parse_env_pairs(args.env or [], kind="env")
    buildenv = _parse_env_pairs(args.buildenv or [], kind="buildenv")
    if env:
        options["env"] = env
    if buildenv:
        options["buildenv"] = buildenv

    resources = _parse_kv(args.resource or []) or None

    spec = build_deployment_request(
        name=args.name,
        app=args.app,
        git_url=args.git,
        branch=args.branch,
        preset=args.preset,
        options=options or None,
        resources=resources,
        path=args.path,
    )

    resp = client.put_deployment(
        args.scope,
        args.project,
        args.stage,
        spec,
        owner=args.owner,
    )
    _print_json(resp)
    return 0


def cmd_start(client: CloudtypeClient, args: argparse.Namespace) -> int:
    _print_json(client.start_deployment(args.scope, args.project, args.stage, args.name))
    return 0


def cmd_stop(client: CloudtypeClient, args: argparse.Namespace) -> int:
    _print_json(client.stop_deployment(args.scope, args.project, args.stage, args.name))
    return 0


def cmd_put_secrets(client: CloudtypeClient, args: argparse.Namespace) -> int:
    if not args.secret:
        raise SystemExit("Provide one or more --secret KEY=VALUE")
    pairs: Dict[str, str] = {}
    for raw in args.secret:
        if "=" not in raw:
            raise SystemExit(f"--secret expects KEY=VALUE (got {raw!r})")
        k, v = raw.split("=", 1)
        pairs[k] = v
    resp = client.put_secrets(
        args.scope,
        args.project,
        args.stage,
        pairs,
        merge=not args.replace,
    )
    _print_json(resp)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cloudtype", description="Cloudtype skill CLI")
    p.add_argument("--base-url", help="API base URL override")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("whoami").set_defaults(func=cmd_whoami)

    def add_common_target(sp: argparse.ArgumentParser, *, require_name: bool = True) -> None:
        sp.add_argument("--scope", required=True)
        sp.add_argument("--project", required=True)
        sp.add_argument("--stage", default="main")
        if require_name:
            sp.add_argument("--name", required=True)

    lst = sub.add_parser("list", help="List deployments in a stage")
    lst.add_argument("--scope", required=True)
    lst.add_argument("--project", required=True)
    lst.add_argument("--stage", default="main")
    lst.add_argument("--json", action="store_true")
    lst.set_defaults(func=cmd_list_deployments)

    st = sub.add_parser("status", help="Get deployment status")
    add_common_target(st)
    st.set_defaults(func=cmd_status)

    ev = sub.add_parser("events", help="Get k8s events for a deployment")
    add_common_target(ev)
    ev.set_defaults(func=cmd_events)

    ensure = sub.add_parser("ensure-project", help="Create project if absent")
    ensure.add_argument("--scope", required=True)
    ensure.add_argument("--name", required=True)
    ensure.add_argument("--display-name")
    ensure.add_argument("--cluster")
    ensure.set_defaults(func=cmd_ensure_project)

    create = sub.add_parser("create-project", help="Force create a project")
    create.add_argument("--scope", required=True)
    create.add_argument("--name", required=True)
    create.add_argument("--display-name")
    create.add_argument("--cluster")
    create.set_defaults(func=cmd_create_project)

    dep = sub.add_parser(
        "deploy",
        help="Create / update / redeploy a deployment (same PUT)",
    )
    dep.add_argument("--scope", required=True)
    dep.add_argument("--project", required=True)
    dep.add_argument("--stage", default="main")
    dep.add_argument("--name", required=True, help="Deployment (service) name")
    dep.add_argument("--app", required=True, help="preset.config[0].app value (e.g. node@20, web, dockerfile)")
    dep.add_argument("--preset", help="preset name (e.g. node, html, vue, dockerfile, container, postgresql)")
    dep.add_argument("--git", help="GitHub repo URL (.git)")
    dep.add_argument("--branch", help="Branch (e.g. main)")
    dep.add_argument("--path", help="Subdirectory in repo (e.g. /backend)")
    dep.add_argument("--owner", help="Owner uid (optional)")
    dep.add_argument("--option", action="append", default=[], help="options.key=value (repeatable)")
    dep.add_argument("--resource", action="append", default=[], help="resources.key=value (repeatable)")
    dep.add_argument("--env", action="append", default=[], help="env NAME=value or NAME=secret:KEY (repeatable)")
    dep.add_argument("--buildenv", action="append", default=[], help="buildenv NAME=value or NAME=secret:KEY")
    dep.add_argument("--ensure-project", action="store_true", help="Create project if it does not exist")
    dep.add_argument("--project-display-name", help="Used when ensure-project creates it")
    dep.set_defaults(func=cmd_deploy)

    start = sub.add_parser("start")
    add_common_target(start)
    start.set_defaults(func=cmd_start)

    stop = sub.add_parser("stop")
    add_common_target(stop)
    stop.set_defaults(func=cmd_stop)

    sec = sub.add_parser(
        "put-secrets",
        help="Write stage-level secrets (merge=true by default)",
    )
    sec.add_argument("--scope", required=True)
    sec.add_argument("--project", required=True)
    sec.add_argument("--stage", default="main")
    sec.add_argument("--secret", action="append", default=[], help="KEY=VALUE (repeatable)")
    sec.add_argument(
        "--replace",
        action="store_true",
        help="Send merge=false (replace entire store). 사용자 명시 시에만.",
    )
    sec.set_defaults(func=cmd_put_secrets)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    client = CloudtypeClient(base_url=args.base_url)
    try:
        return args.func(client, args)
    except CloudtypeError as e:
        sys.stderr.write(f"cloudtype error: {e}\n")
        return 1
    except RuntimeError as e:
        sys.stderr.write(f"error: {e}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
