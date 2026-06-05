"""Build inventory NAT eval prompts from demo text + live baseline hints."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from eval.ground_truth_refresh import scoring_baseline_path

REPO_ROOT = Path(__file__).resolve().parents[1]
PROMPTS_DIR = REPO_ROOT / "demos" / "prompts"


def _load_prompt_text(scenario: str) -> str:
    prompt_path = PROMPTS_DIR / f"{scenario}.txt"
    if not prompt_path.is_file():
        msg = f"prompt file not found: {prompt_path!s}"
        raise FileNotFoundError(msg)
    text = prompt_path.read_text(encoding="utf-8").replace("\r", "").strip()
    if not text:
        msg = f"prompt file is empty: {prompt_path!s}"
        raise ValueError(msg)
    return text


def _live_baseline_for_hints(live_baseline_path: Path | None) -> Path | None:
    """Resolve live baseline path; explicit missing path does not fall back to default."""
    if live_baseline_path is not None:
        return live_baseline_path if live_baseline_path.is_file() else None
    default = scoring_baseline_path("inventory")
    return default if default.is_file() else None


def resolve_org_id(demo_org_id: str, live_baseline_path: Path | None = None) -> str:
    """Prefer organization id from the live baseline when present."""
    path = _live_baseline_for_hints(live_baseline_path)
    if path is None:
        return demo_org_id.strip()
    data = json.loads(path.read_text(encoding="utf-8"))
    orgs = data.get("organizations") or []
    if orgs and isinstance(orgs[0], dict) and orgs[0].get("id") is not None:
        return str(orgs[0]["id"]).strip()
    return demo_org_id.strip()


def format_pipe_id_hints(live_baseline_path: Path | None = None) -> str:
    """Return MCP pipe_id hint lines for inventory get_cards calls."""
    path = _live_baseline_for_hints(live_baseline_path)
    if path is None:
        return "  - Use each id field from the search_pipes pipes array."
    data = json.loads(path.read_text(encoding="utf-8"))
    pipes = (data.get("organizations") or [{}])[0].get("pipes") or []
    ids = [str(pipe["id"]) for pipe in pipes if isinstance(pipe, dict) and pipe.get("id")]
    if not ids:
        return "  - Use each id field from the search_pipes pipes array."
    return f"get_cards once per pipe_id (first=50): {', '.join(ids)}"


def build_inventory_eval_prompt(
    *,
    demo_org_id: str,
    live_baseline_path: Path | None = None,
) -> str:
    """Return the inventory prompt with MCP hints (canonical for NAT smoke/profile)."""
    base = _load_prompt_text("inventory")
    org_id = resolve_org_id(demo_org_id, live_baseline_path)
    hints = format_pipe_id_hints(live_baseline_path)
    return (
        f"{base}\n\n"
        f"Pipefy MCP (inventory):\n"
        f"- search_pipes once: organization_id integer {org_id}, max_pipes_per_org 500. "
        f"Do not pass pipe_name.\n"
        f"- get_cards: pipe_id must be the numeric id string only (never English placeholders).\n"
        f"{hints}\n"
        f"- Reply with one line per pipe (Name → N open cards) after all get_cards calls."
    )


def build_inventory_profile_dataset(*, demo_org_id: str) -> list[dict[str, str]]:
    """Single-row eval dataset for nat eval profiler runs."""
    return [
        {
            "id": "inventory-1",
            "question": build_inventory_eval_prompt(demo_org_id=demo_org_id),
            "answer": "",
        }
    ]


def write_inventory_profile_dataset(path: Path, *, demo_org_id: str) -> None:
    """Write the inventory profiler dataset JSON to *path*."""
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = build_inventory_profile_dataset(demo_org_id=demo_org_id)
    path.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    """CLI argument parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--print-prompt",
        action="store_true",
        help="Print inventory eval prompt to stdout (for demos/02_nat_smoke.sh)",
    )
    parser.add_argument(
        "--write-dataset",
        type=Path,
        metavar="PATH",
        help="Write eval JSON dataset for nat eval",
    )
    parser.add_argument(
        "--demo-org-id",
        default="",
        help="DEMO_ORG_ID fallback when live baseline is missing",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    demo_org_id = args.demo_org_id.strip() or os.environ.get("DEMO_ORG_ID", "").strip()

    if args.print_prompt:
        if not demo_org_id:
            print(
                "error: DEMO_ORG_ID required (set in .env or pass --demo-org-id)",
                file=sys.stderr,
            )
            return 1
        print(build_inventory_eval_prompt(demo_org_id=demo_org_id))
        return 0

    if args.write_dataset is not None:
        if not demo_org_id:
            print(
                "error: --demo-org-id required (set DEMO_ORG_ID in .env)",
                file=sys.stderr,
            )
            return 1
        write_inventory_profile_dataset(args.write_dataset, demo_org_id=demo_org_id)
        return 0

    build_parser().print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
