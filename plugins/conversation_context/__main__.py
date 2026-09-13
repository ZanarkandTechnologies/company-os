"""Explicit local import/export and redacted validation; never reads account credentials."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .codex import collect
from .intake import IntakeError, load_policy, private_root, publish_bundle, read_bytes, read_project
from .models import Bundle


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["validate", "import", "collect-codex"])
    parser.add_argument("--root", type=Path, required=True, help="Private intake directory containing policy.json")
    parser.add_argument("--project", required=True)
    parser.add_argument("--week", required=True, help="ISO week, for example 2026-W37")
    parser.add_argument("--file", type=Path, help="Explicit selected evidence bundle to import")
    parser.add_argument("--member", help="Exact member ID for local Codex collection")
    parser.add_argument("--expected-digest", help="Prior bundle digest required when replacing an existing import")
    args = parser.parse_args(arguments)
    try:
        root = private_root(args.root)
        policy = load_policy(root)
        if args.action == "validate":
            result = read_project(root, args.project, args.week)
            result.pop("conversations")
            result.pop("trust")
        else:
            if args.action == "import":
                if not args.file:
                    raise IntakeError("import_file_required")
                bundle = Bundle.model_validate_json(read_bytes(args.file))
                if bundle.project_id != args.project or bundle.week != args.week:
                    raise IntakeError("conversation_scope_mismatch")
            else:
                binding = next((item for item in policy.projects.get(args.project, [])
                                if item.source == "codex_local" and item.member_id == args.member), None)
                if not binding:
                    raise IntakeError("source_not_authorized")
                bundle = collect(binding, args.project, args.week, policy.timezone)
            result = publish_bundle(root, bundle, args.expected_digest)
        print(json.dumps(result))
        return 0 if result["status"] in {"ready", "imported", "unchanged"} else 1
    except IntakeError as error:
        result = {"status": "blocked", "error": str(error)}
    except (OSError, ValueError, KeyError, TypeError):
        result = {"status": "blocked", "error": "conversation_input_invalid"}
    print(json.dumps(result))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
