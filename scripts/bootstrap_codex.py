#!/usr/bin/env python3
"""Prepare project-scoped Codex harness. Dry run by default, never overwrites."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_SKILLS = ["fde-route", "fde-define", "fde-data", "fde-rules", "fde-build", "fde-verify", "fde-deliver", "fde-track", "fde-pdf-read", "fde-project-review"]


def plan(workspace, profile):
    workspace = Path(workspace).resolve()
    if not workspace.is_dir() or workspace in (Path('/'), Path.home()):
        raise ValueError("현재 과제의 구체적인 기존 폴더를 지정하세요.")
    if workspace.is_relative_to(ROOT):
        raise ValueError("키트 원본 안이 아닌 별도 과제 폴더를 지정하세요.")
    if profile not in ("app", "data", "document"):
        raise ValueError("지원 프로필: app/data/document")
    selected = BASE_SKILLS + (["fde-ui"] if profile == "app" else [])
    payload = {}
    packaged_dirs = {'skills', 'scripts', 'templates', 'guides'}
    packaged_files = {'README.md', 'LICENSE'}
    for source in ROOT.rglob('*'):
        rel = source.relative_to(ROOT)
        if not source.is_file() or source.is_symlink() or any(x in ('__pycache__', '.venv', '.git') for x in rel.parts):
            continue
        if not (rel.parts[0] in packaged_dirs or rel.as_posix() in packaged_files):
            continue
        if rel.parts[0] == 'skills' and len(rel.parts) > 1 and rel.parts[1] not in selected:
            continue
        if source.suffix == '.pyc':
            continue
        payload["fde-harness/" + source.relative_to(ROOT).as_posix()] = source.read_bytes()
    for name in selected:
        for source in (ROOT / "skills" / name).rglob('*'):
            if source.is_file():
                payload[f".agents/skills/{name}/" + source.relative_to(ROOT / "skills" / name).as_posix()] = source.read_bytes()
    guide = "FDE_INSTRUCTIONS.md" if (workspace / "AGENTS.md").exists() else "AGENTS.md"
    payload[guide] = (ROOT / "templates/CODEX_INSTRUCTIONS.md").read_bytes()
    payload["FDE_WORKSTATE.md"] = (ROOT / "templates/WORKSTATE.md").read_bytes()
    from fde_state import initial
    progress = 'FDE_PROGRESS.json'
    payload[progress] = (json.dumps(initial(), ensure_ascii=False, indent=2) + '\n').encode()
    manifest = {"version": "1.3.1", "profile": profile, "package": "fde-harness", "guide": guide,
                "state": "FDE_WORKSTATE.md", "progress": progress, "requirements": progress,
                "verification": progress, "skills": selected,
                "automatic_model_switch": False, "external_model_api": False, "automatic_hooks": False, "language": "ko", "distribution": "runtime-only"}
    payload["FDE_HARNESS.json"] = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    collisions = []
    for rel in payload:
        target = workspace / rel
        if not target.resolve().is_relative_to(workspace):
            raise ValueError(f"작업 폴더 밖으로 연결된 경로: {rel}")
        if target.exists() or target.is_symlink():
            collisions.append(rel)
    if collisions:
        raise ValueError("기존 파일 충돌. 아무 파일도 쓰지 않았습니다: " + ", ".join(collisions[:8]))
    return workspace, payload, manifest


def apply(workspace, payload):
    written = []
    for rel, body in payload.items():
        target = workspace / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(body)
        written.append(rel)
    return written


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--profile', choices=['app', 'data', 'document'], default='data')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        workspace, payload, manifest = plan(args.workspace, args.profile)
        written = apply(workspace, payload) if args.apply else []
        print(json.dumps({"mode": "installed" if args.apply else "preview", "workspace": str(workspace),
                          "files": len(payload), "planned": sorted(payload), "skills": manifest['skills'], "guide": manifest['guide'],
                          "written": written,
                          "next": f"{manifest['guide']}와 FDE_HARNESS.json을 읽게 하세요. 자동 인식은 실제 Codex에서 확인하세요."}, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError) as exc:
        print(json.dumps({"status": "설치 중단", "reason": str(exc), "note": "기존 파일을 덮지 않음. 쓰기 도중 OS 오류가 났으면 생성 목록을 확인하세요."}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
