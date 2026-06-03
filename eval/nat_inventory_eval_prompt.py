"""Build inventory eval prompt and JSON dataset for NAT profiler runs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_PROMPTS_DIR = _REPO_ROOT / "demos" / "prompts"
_LIVE_BASELINE = _REPO_ROOT / "eval" / "fixtures" / "live" / "inventory.json"


def _load_prompt_text(scenario: str) -> str:
    prompt_path = _PROMPTS_DIR / f"{scenario}.txt"
    if not prompt_path.is_file():
        raise FileNotFoundError(f"prompt file not found: {prompt_path}")
    text = prompt_path.read_text(encoding="utf-8").replace("\r", "").strip()
    if not text:
        raise ValueError(f"prompt file is empty: {prompt_path}")
    return text


def _inventory_org_id(demo_org_id: str) -> str:
    if not _LIVE_BASELINE.is_file():
        return demo_org_id
    data = json.loads(_LIVE_BASELINE.read_text(encoding="utf-8"))
    orgs = data.get("organizations") or []
    if orgs and isinstance(orgs[0], dict) and orgs[0].get("id") is not None:
        return str(orgs[0]["id"]).strip()
    return demo_org_id


def _pipe_id_hints() -> str:
    if not _LIVE_BASELINE.is_file():
        return "  - Use each id field from the search_pipes pipes array."
    data = json.loads(_LIVE_BASELINE.read_text(encoding="utf-8"))
    pipes = (data.get("organizations") or [{}])[0].get("pipes") or []
    ids = [str(pipe["id"]) for pipe in pipes if isinstance(pipe, dict) and pipe.get("id")]
    if not ids:
        return "  - Use each id field from the search_pipes pipes array."
    return f"get_cards once per pipe_id (first=50): {', '.join(ids)}"


def build_inventory_eval_prompt(*, demo_org_id: str) -> str:
    """Return the inventory prompt with MCP hints (matches demos/02_nat_smoke.sh)."""
    base = _load_prompt_text("inventory")
    org_id = _inventory_org_id(demo_org_id)
    hints = _pipe_id_hints()
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


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write-dataset",
        type=Path,
        metavar="PATH",
        required=True,
        help="Write eval JSON dataset for nat eval",
    )
    parser.add_argument(
        "--demo-org-id",
        default="",
        help="DEMO_ORG_ID fallback when live baseline is missing",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    demo_org_id = args.demo_org_id.strip()
    if not demo_org_id:
        print(
            "error: --demo-org-id required (set DEMO_ORG_ID in .env)",
            file=sys.stderr,
        )
        return 1
    write_inventory_profile_dataset(args.write_dataset, demo_org_id=demo_org_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
