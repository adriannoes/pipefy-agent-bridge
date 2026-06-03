"""CLI wrapper for inventory NAT profiler dataset generation (see eval/inventory_prompt.py)."""

from __future__ import annotations

from eval.inventory_prompt import (
    build_inventory_eval_prompt,
    build_inventory_profile_dataset,
    main,
    write_inventory_profile_dataset,
)

__all__ = [
    "build_inventory_eval_prompt",
    "build_inventory_profile_dataset",
    "write_inventory_profile_dataset",
]


if __name__ == "__main__":
    raise SystemExit(main())
