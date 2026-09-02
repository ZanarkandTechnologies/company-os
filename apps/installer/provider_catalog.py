"""Load and validate selectable data-source providers for setup and health."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


DEFAULT_CATALOG = Path(__file__).resolve().parent / "providers"
MANAGED_DATA_SOURCES = re.compile(
    r"<!-- hermes:managed data-sources -->(.*?)<!-- /hermes:managed data-sources -->",
    re.DOTALL,
)
ROW = re.compile(
    r"^\| `(?P<role>[^`]+)` \| (?P<provider>[^|]+?) \| (?P<source>[^|]+?) \|",
    re.MULTILINE,
)
IDENTIFIER = re.compile(r"^[a-z][a-z0-9_-]*$")


class CatalogError(ValueError):
    """A catalog or selected-provider contract is invalid."""


def _required_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CatalogError(f"catalog_invalid:{field}")
    return value.strip()


def _validate_provider(provider: Any, source_id: str) -> dict[str, Any]:
    if not isinstance(provider, dict):
        raise CatalogError(f"catalog_invalid:{source_id}.provider")
    provider_id = _required_string(provider.get("id"), f"{source_id}.provider.id")
    if not IDENTIFIER.fullmatch(provider_id):
        raise CatalogError(f"catalog_invalid:{source_id}.{provider_id}.id")
    _required_string(provider.get("label"), f"{source_id}.{provider_id}.label")
    mcp = provider.get("mcp")
    if not isinstance(mcp, dict) or mcp.get("source") not in {
        "hermes_catalog",
        "composio_session",
    }:
        raise CatalogError(f"catalog_invalid:{source_id}.{provider_id}.mcp")
    name = _required_string(mcp.get("name"), f"{source_id}.{provider_id}.mcp.name")
    if not IDENTIFIER.fullmatch(name):
        raise CatalogError(f"catalog_invalid:{source_id}.{provider_id}.mcp.name")
    if mcp["source"] == "composio_session":
        toolkit = _required_string(
            mcp.get("toolkit"), f"{source_id}.{provider_id}.mcp.toolkit"
        )
        if not IDENTIFIER.fullmatch(toolkit):
            raise CatalogError(f"catalog_invalid:{source_id}.{provider_id}.mcp.toolkit")
        tools = mcp.get("tools")
        if not isinstance(tools, list) or not tools or not all(
            isinstance(tool, str) and re.fullmatch(r"[A-Z][A-Z0-9_]*", tool)
            for tool in tools
        ):
            raise CatalogError(f"catalog_invalid:{source_id}.{provider_id}.mcp.tools")
    test = provider.get("test")
    if not isinstance(test, dict):
        raise CatalogError(f"catalog_invalid:{source_id}.{provider_id}.test")
    risk = test.get("risk")
    if risk not in {"read_only", "reversible", "irreversible"}:
        raise CatalogError(f"catalog_invalid:{source_id}.{provider_id}.test.risk")
    if not isinstance(test.get("requires_confirmation"), bool):
        raise CatalogError(
            f"catalog_invalid:{source_id}.{provider_id}.test.requires_confirmation"
        )
    if risk != "read_only" and not test["requires_confirmation"]:
        raise CatalogError(
            f"catalog_invalid:{source_id}.{provider_id}.test.side_effect_confirmation"
        )
    for field in ("prompt", "expected_output"):
        _required_string(test.get(field), f"{source_id}.{provider_id}.test.{field}")
    assertions = test.get("assertions")
    if not isinstance(assertions, list) or not assertions or not all(
        isinstance(item, str) and item.strip() for item in assertions
    ):
        raise CatalogError(f"catalog_invalid:{source_id}.{provider_id}.test.assertions")
    readiness = provider.get("readiness")
    if not isinstance(readiness, dict):
        raise CatalogError(f"catalog_invalid:{source_id}.{provider_id}.readiness")
    importance = readiness.get("importance")
    if importance not in {"core", "optional", "destination", "capability", "alias"}:
        raise CatalogError(
            f"catalog_invalid:{source_id}.{provider_id}.readiness.importance"
        )
    if importance == "alias":
        alias_of = _required_string(
            readiness.get("alias_of"),
            f"{source_id}.{provider_id}.readiness.alias_of",
        )
        if not IDENTIFIER.fullmatch(alias_of) or alias_of == source_id:
            raise CatalogError(
                f"catalog_invalid:{source_id}.{provider_id}.readiness.alias_of"
            )
    elif importance == "capability":
        if readiness.get("proof") != "connection_receipt":
            raise CatalogError(
                f"catalog_invalid:{source_id}.{provider_id}.readiness.proof"
            )
    else:
        readiness_prompt = _required_string(
            readiness.get("prompt"),
            f"{source_id}.{provider_id}.readiness.prompt",
        )
        lowered_prompt = readiness_prompt.lower()
        if "read-only" not in lowered_prompt or not re.search(
            r"(?:do not|without)[^.]{0,120}(?:make|making) changes|make no changes",
            lowered_prompt,
        ):
            raise CatalogError(
                f"catalog_invalid:{source_id}.{provider_id}.readiness.read_only"
            )
        allowed = readiness.get("allowed_read_tools")
        if not isinstance(allowed, list) or not allowed or not all(
            isinstance(value, str)
            and re.fullmatch(r"mcp__[A-Za-z0-9_]+__[A-Za-z0-9_]+", value)
            for value in allowed
        ):
            raise CatalogError(
                f"catalog_invalid:{source_id}.{provider_id}.readiness.allowed_read_tools"
            )
    for field in ("required_fields", "required_relations", "optional_fields"):
        values = readiness.get(field, [])
        if not isinstance(values, list) or not all(
            isinstance(value, str) and IDENTIFIER.fullmatch(value) for value in values
        ):
            raise CatalogError(
                f"catalog_invalid:{source_id}.{provider_id}.readiness.{field}"
            )
        if len(values) != len(set(values)):
            raise CatalogError(
                f"catalog_invalid:{source_id}.{provider_id}.readiness.{field}"
            )
    return provider


def load_catalog(directory: Path = DEFAULT_CATALOG) -> dict[str, dict[str, Any]]:
    """Return the complete validated catalog keyed by data-source role."""
    if not directory.is_dir():
        raise CatalogError(f"catalog_missing:{directory}")
    catalog: dict[str, dict[str, Any]] = {}
    for path in sorted(directory.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise CatalogError(f"catalog_unreadable:{path.name}") from error
        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            raise CatalogError(f"catalog_invalid:{path.name}.schema_version")
        source_id = _required_string(payload.get("id"), f"{path.name}.id")
        if source_id != path.stem or not IDENTIFIER.fullmatch(source_id):
            raise CatalogError(f"catalog_invalid:{path.name}.id")
        _required_string(payload.get("label"), f"{source_id}.label")
        providers = payload.get("providers")
        if not isinstance(providers, list) or not providers:
            raise CatalogError(f"catalog_invalid:{source_id}.providers")
        validated = [_validate_provider(provider, source_id) for provider in providers]
        provider_ids = [str(provider["id"]) for provider in validated]
        if len(provider_ids) != len(set(provider_ids)):
            raise CatalogError(f"catalog_invalid:{source_id}.duplicate_provider")
        payload["providers"] = validated
        catalog[source_id] = payload
    if not catalog:
        raise CatalogError("catalog_empty")
    return catalog


def provider_for(
    catalog: dict[str, dict[str, Any]], role: str, provider_id: str
) -> dict[str, Any]:
    source = catalog.get(role)
    if source is None:
        raise CatalogError(f"unsupported_data_source:{role}")
    for provider in source["providers"]:
        if provider["id"] == provider_id:
            return provider
    raise CatalogError(f"unsupported_provider:{role}:{provider_id}")


def selected_bindings(
    workspace: Path, catalog: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Resolve configured managed rows to their catalog provider definitions."""
    try:
        content = workspace.read_text(encoding="utf-8")
    except OSError as error:
        raise CatalogError(f"workspace_unreadable:{workspace}") from error
    block = MANAGED_DATA_SOURCES.search(content)
    if not block:
        raise CatalogError("workspace_data_sources_missing")
    bindings: list[dict[str, Any]] = []
    for row in ROW.finditer(block.group(1)):
        role = row.group("role").strip()
        provider_id = row.group("provider").strip().lower()
        source = row.group("source").strip()
        if provider_id in {"", "—", "replace_me"}:
            continue
        if source.lower() in {"", "—", "replace_me"}:
            raise CatalogError(f"source_missing:{role}")
        provider = provider_for(catalog, role, provider_id)
        bindings.append(
            {
                "case_id": f"{role}:{provider_id}",
                "data_source": role,
                "source": source,
                "provider": provider,
            }
        )
    return bindings


def connection_key(provider: dict[str, Any]) -> str:
    mcp = provider["mcp"]
    return f"{mcp['source']}:{mcp['name']}"


def configuration_hash(bindings: list[dict[str, Any]]) -> str:
    stable = [
        {
            "case_id": binding["case_id"],
            "source": binding["source"],
            "connection": connection_key(binding["provider"]),
            "test": binding["provider"]["test"],
        }
        for binding in sorted(bindings, key=lambda item: item["case_id"])
    ]
    encoded = json.dumps(stable, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def readiness_hash(bindings: list[dict[str, Any]]) -> str:
    """Hash only the selected role-owned data-readiness contracts."""
    stable = [
        {
            "case_id": binding["case_id"],
            "source": binding["source"],
            "connection": connection_key(binding["provider"]),
            "readiness": binding["provider"]["readiness"],
        }
        for binding in sorted(bindings, key=lambda item: item["case_id"])
    ]
    encoded = json.dumps(stable, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def render_readiness_prompt(binding: dict[str, Any]) -> str:
    """Render the role's read-only, bounded readiness prompt."""
    prompt = str(binding["provider"]["readiness"].get("prompt") or "")
    return prompt.replace("{{source}}", binding["source"])


def render_test_prompt(binding: dict[str, Any], run_id: str) -> str:
    prompt = str(binding["provider"]["test"]["prompt"])
    return prompt.replace("{{source}}", binding["source"]).replace(
        "{{run_id}}", run_id
    )
