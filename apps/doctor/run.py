#!/usr/bin/env python3
"""Run an analysis-only Company OS automation through native Hermes tools."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from apps.installer import runtime


CONTRACTS = {
    "daily": "daily-operating-update.md",
    "weekly": "weekly-operating-review.md",
}


def analysis_prompt(workspace: Path, cadence: str) -> str:
    contract = workspace / "automations" / CONTRACTS[cadence]
    context = workspace / ".hermes.md"
    try:
        context_text = context.read_text(encoding="utf-8")
        contract_text = contract.read_text(encoding="utf-8")
    except OSError as error:
        raise ValueError("analysis_contract_unreadable") from error
    local_contract = re.sub(
        r"\n- \[ \] \*\*4 —.*?(?=\n## Output)",
        "",
        contract_text,
        flags=re.DOTALL,
    )
    if local_contract == contract_text:
        raise ValueError("analysis_external_effects_step_missing")
    return (
        f"Execute the embedded {cadence} automation contract exactly. Its external-effects "
        "step has been removed for analysis mode; do not replace it with any provider write, "
        "message delivery, or artifact sync. Perform every remaining fetch, skill, local-write, "
        "and review step. Return every changed local file path and every missing-information or "
        "authority blocker.\n\n"
        "<workspace_context>\n"
        + context_text
        + "\n</workspace_context>\n\n<automation_contract>\n"
        + local_contract
        + "\n</automation_contract>"
    )


def operate(args: argparse.Namespace) -> int:
    profile = args.profile_home.expanduser().resolve()
    workspace = profile / "workspace"
    if not (workspace / ".hermes.md").is_file():
        print("Doctor blocked: installed workspace is missing.")
        return 2
    for cadence in args.cadences or ("daily", "weekly"):
        contract = workspace / "automations" / CONTRACTS[cadence]
        if not contract.is_file():
            print(f"Doctor blocked: missing {cadence} automation contract.")
            return 2
        try:
            prompt = analysis_prompt(workspace, cadence)
        except ValueError as error:
            print(f"Doctor blocked: {error}.")
            return 2
        result = runtime.run_command(
            [
                "hermes", "chat", "--quiet", "--query-file", "-",
                "--source", "tool", "--max-turns", "80",
            ],
            profile,
            input_text=prompt,
            check=False,
            timeout=900,
        )
        if result.returncode:
            print(f"Doctor {cadence} analysis failed.")
            return 2
        print(result.stdout.strip())
    return 0


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    command.add_argument("--profile-home", type=Path, default=runtime.default_profile_home())
    command.add_argument("--cadence", dest="cadences", action="append", choices=tuple(CONTRACTS))
    return command


def main(argv: list[str] | None = None) -> int:
    return operate(parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
