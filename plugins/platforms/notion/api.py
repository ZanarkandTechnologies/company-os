"""Small direct Notion API adapter used by the plugin tools and event enrichment."""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

API_ROOT = "https://api.notion.com/v1"
DEFAULT_VERSION = "2026-03-11"
_PAGE_ID = re.compile(r"^(?:[0-9a-fA-F]{32}|[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12})$")
_BOT_ID = ""
DEFAULT_TRIGGER = "@hermes"


class NotionCredentialError(RuntimeError):
    """A redacted credential-validation failure safe for setup output."""


def validate_token(token: str) -> None:
    """Validate one candidate integration token without reading profile state."""
    cleaned = token.strip()
    if not cleaned:
        raise NotionCredentialError("notion_token_invalid")
    request = urllib.request.Request(
        API_ROOT + "/users/me",
        method="GET",
        headers={
            "Authorization": f"Bearer {cleaned}",
            "Notion-Version": DEFAULT_VERSION,
            "User-Agent": "hermes-notion-platform/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            if response.status != 200:
                raise NotionCredentialError("notion_token_invalid")
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        code = "notion_token_invalid" if error.code in {401, 403} else "notion_unavailable"
        raise NotionCredentialError(code) from error
    except (OSError, ValueError, urllib.error.URLError) as error:
        raise NotionCredentialError("notion_unavailable") from error
    if not isinstance(payload, dict) or payload.get("object") != "user":
        raise NotionCredentialError("notion_token_invalid")


def _setting(name: str, default: str = "") -> str:
    """Read profile-scoped values without borrowing another profile's env."""
    try:
        from agent.secret_scope import UnscopedSecretError, get_secret
    except ModuleNotFoundError:  # Direct unit tests outside the Hermes runtime.
        return str(os.getenv(name, default) or default).strip()
    try:
        value = get_secret(name, default)
    except UnscopedSecretError:
        value = os.getenv(name, default)
    return str(value or default).strip()


def _token() -> str:
    token = _setting("NOTION_TOKEN")
    if not token:
        raise RuntimeError("NOTION_TOKEN is not configured")
    return token


def _page_id(value: str) -> str:
    value = value.strip()
    if not _PAGE_ID.fullmatch(value):
        raise ValueError("page_id must be a Notion UUID")
    return value


def _bounded_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(_setting(name, str(default)))
    except ValueError:
        value = default
    return max(minimum, min(maximum, value))


def _request(method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        API_ROOT + path,
        data=payload,
        method=method,
        headers={
            "Authorization": f"Bearer {_token()}",
            "Notion-Version": _setting("NOTION_API_VERSION", DEFAULT_VERSION),
            "Content-Type": "application/json",
            "User-Agent": "hermes-notion-platform/1.0",
        },
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            if error.code == 429 and attempt < 2:
                try:
                    retry_after = min(float(error.headers.get("Retry-After", "1")), 5.0)
                except ValueError:
                    retry_after = 1.0
                time.sleep(max(0.1, retry_after))
                continue
            detail = error.read(4096).decode("utf-8", "replace")
            raise RuntimeError(f"Notion API {error.code}: {detail}") from error
    raise RuntimeError("Notion API request exhausted retries")


def _paginate(method: str, path: str, body: dict[str, Any] | None = None, *, limit: int = 200) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    cursor = ""
    while len(results) < limit:
        if method == "GET":
            separator = "&" if "?" in path else "?"
            cursor_query = "" if not cursor else separator + urllib.parse.urlencode({"start_cursor": cursor})
            response = _request("GET", path + cursor_query)
        else:
            request_body = dict(body or {})
            if cursor:
                request_body["start_cursor"] = cursor
            response = _request(method, path, request_body)
        page = response.get("results")
        if not isinstance(page, list):
            break
        results.extend(item for item in page if isinstance(item, dict))
        if not response.get("has_more") or not response.get("next_cursor"):
            break
        cursor = str(response["next_cursor"])
    return results[:limit]


def _plain_text(rich_text: Any) -> str:
    if not isinstance(rich_text, list):
        return ""
    return "".join(str(item.get("plain_text") or "") for item in rich_text if isinstance(item, dict))


def compact_page(page: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": page.get("id"),
        "url": page.get("url"),
        "created_time": page.get("created_time"),
        "last_edited_time": page.get("last_edited_time"),
        "archived": page.get("archived", False),
        "in_trash": page.get("in_trash", False),
        "parent": page.get("parent", {}),
        "properties": page.get("properties", {}),
    }


def get_page(page_id: str) -> dict[str, Any]:
    return compact_page(_request("GET", f"/pages/{_page_id(page_id)}"))


def get_comment(comment_id: str) -> dict[str, Any]:
    comment = _request("GET", f"/comments/{_page_id(comment_id)}")
    return {
        "id": comment.get("id"),
        "discussion_id": comment.get("discussion_id"),
        "parent": comment.get("parent", {}),
        "created_time": comment.get("created_time"),
        "last_edited_time": comment.get("last_edited_time"),
        "created_by": comment.get("created_by", {}),
        "text": _plain_text(comment.get("rich_text")),
    }


def get_bot_id() -> str:
    global _BOT_ID
    if not _BOT_ID:
        _BOT_ID = str(_request("GET", "/users/me").get("id") or "")
    return _BOT_ID


def comment_trigger() -> str:
    return _setting("NOTION_COMMENT_TRIGGER", DEFAULT_TRIGGER) or DEFAULT_TRIGGER


def _allowed_data_source_ids() -> set[str]:
    return {
        _page_id(item.strip())
        for item in _setting("NOTION_ALLOWED_DATA_SOURCES").split(",")
        if item.strip()
    }


def _assert_ticket_scope(page: dict[str, Any]) -> None:
    allowed = _allowed_data_source_ids()
    if not allowed:
        raise RuntimeError("NOTION_ALLOWED_DATA_SOURCES is not configured")
    parent_value = page.get("parent")
    parent: dict[str, Any] = parent_value if isinstance(parent_value, dict) else {}
    source_id = str(parent.get("data_source_id") or "").strip()
    if source_id not in allowed:
        raise RuntimeError("Notion page is outside the configured PKMS data-source scope")


def list_comments(block_id: str, *, limit: int = 200) -> list[dict[str, Any]]:
    block_id = _page_id(block_id)
    comments = _paginate("GET", f"/comments?block_id={block_id}&page_size=100", limit=limit)
    return [
        {
            "id": item.get("id"),
            "discussion_id": item.get("discussion_id"),
            "parent": item.get("parent", {}),
            "created_time": item.get("created_time"),
            "last_edited_time": item.get("last_edited_time"),
            "created_by": item.get("created_by", {}),
            "text": _plain_text(item.get("rich_text")),
        }
        for item in comments
    ]


def comment_parent_id(comment: dict[str, Any]) -> str:
    """Return the page/block whose open comments contain the discussion."""
    parent_value = comment.get("parent")
    parent: dict[str, Any] = parent_value if isinstance(parent_value, dict) else {}
    for key in ("page_id", "block_id"):
        value = str(parent.get(key) or "").strip()
        if value:
            return _page_id(value)
    raise ValueError("comment parent must contain a Notion page_id or block_id")


def list_data_sources() -> dict[str, Any]:
    root_page_id = _page_id(_setting("NOTION_ROOT_PAGE_ID"))
    get_page(root_page_id)
    sources = _paginate(
        "POST",
        "/search",
        {"filter": {"property": "object", "value": "data_source"}, "page_size": 100},
        limit=_bounded_int("NOTION_MAX_DATA_SOURCES", 200, 1, 500),
    )
    allowed = _allowed_data_source_ids()
    compact_sources = [
        {
            "id": item.get("id"),
            "title": _plain_text(item.get("title")),
            "parent": item.get("parent", {}),
            "properties": {
                name: {"id": value.get("id"), "type": value.get("type")}
                for name, value in (item.get("properties") or {}).items()
                if isinstance(value, dict)
            },
        }
        for item in sources
        if item.get("id") in allowed
    ]
    return {"root_page_id": root_page_id, "data_sources": compact_sources}


def _compact_block(block: dict[str, Any]) -> dict[str, Any]:
    block_type = str(block.get("type") or "unsupported")
    block_value = block.get(block_type)
    value: dict[str, Any] = block_value if isinstance(block_value, dict) else {}
    text = _plain_text(value.get("rich_text") or value.get("caption"))
    if not text and block_type in {"child_page", "child_database"}:
        text = str(value.get("title") or "")
    return {
        "id": block.get("id"),
        "type": block_type,
        "text": text,
        "has_children": bool(block.get("has_children")),
    }


def get_ticket_context(page_id: str) -> dict[str, Any]:
    page_id = _page_id(page_id)
    page = get_page(page_id)
    _assert_ticket_scope(page)
    max_blocks = _bounded_int("NOTION_CONTEXT_MAX_BLOCKS", 100, 1, 300)
    max_comments = _bounded_int("NOTION_CONTEXT_MAX_COMMENTS", 200, 1, 500)
    max_depth = _bounded_int("NOTION_CONTEXT_MAX_DEPTH", 12, 1, 20)
    blocks: list[dict[str, Any]] = []
    comments = list_comments(page_id, limit=max_comments)
    queue: list[tuple[str, int]] = [(page_id, 0)]
    visited = {page_id}
    while queue and len(blocks) < max_blocks:
        parent_id, depth = queue.pop(0)
        children = _paginate("GET", f"/blocks/{parent_id}/children?page_size=100", limit=max_blocks - len(blocks))
        for child in children:
            if len(blocks) >= max_blocks:
                break
            compact = _compact_block(child)
            blocks.append(compact)
            if len(comments) < max_comments and compact["id"]:
                comments.extend(list_comments(str(compact["id"]), limit=max_comments - len(comments)))
            child_id = str(compact["id"] or "")
            if compact["has_children"] and child_id and child_id not in visited and depth < max_depth:
                visited.add(child_id)
                queue.append((child_id, depth + 1))
    return {
        "page": page,
        "blocks": blocks,
        "open_comments": comments[:max_comments],
        "limits": {
            "max_blocks": max_blocks,
            "max_comments": max_comments,
            "max_depth": max_depth,
            "blocks_truncated": len(blocks) >= max_blocks,
            "comments_truncated": len(comments) >= max_comments,
            "resolved_comments_available": False,
        },
    }


def render_ticket_context(context: dict[str, Any]) -> str:
    maximum = _bounded_int("NOTION_CONTEXT_MAX_CHARS", 50_000, 4_000, 100_000)
    rendered = json.dumps(context, ensure_ascii=False, separators=(",", ":"))
    if len(rendered) <= maximum:
        return rendered
    return json.dumps(
        {"context_excerpt": rendered[: maximum - 100], "context_truncated": True},
        ensure_ascii=False,
        separators=(",", ":"),
    )


def create_comment_reply(discussion_id: str, content: str) -> dict[str, Any]:
    discussion_id = _page_id(discussion_id.removeprefix("discussion:"))
    maximum = _bounded_int("NOTION_REPLY_MAX_CHARS", 12_000, 1_000, 50_000)
    content = content.strip()
    if len(content) > maximum:
        content = content[: maximum - 32] + "\n\n[response truncated]"
    rich_text = [
        {"type": "text", "text": {"content": content[index : index + 1900]}}
        for index in range(0, len(content), 1900)
    ]
    if not rich_text:
        raise ValueError("comment reply cannot be empty")
    response = _request("POST", "/comments", {"discussion_id": discussion_id, "rich_text": rich_text})
    return {"id": response.get("id"), "discussion_id": response.get("discussion_id")}


def update_page_properties(page_id: str, properties: dict[str, Any]) -> dict[str, Any]:
    if _setting("NOTION_ENABLE_WRITES").lower() != "true":
        raise RuntimeError("Notion writes are disabled; set NOTION_ENABLE_WRITES=true explicitly")
    page_id = _page_id(page_id)
    _request("PATCH", f"/pages/{page_id}", {"properties": properties})
    return get_page(page_id)


def notion_get_page(args: dict | None = None, **kwargs: Any) -> str:
    values = args or kwargs
    return json.dumps(get_page(str(values.get("page_id") or "")), separators=(",", ":"))


def notion_get_ticket_context(args: dict | None = None, **kwargs: Any) -> str:
    values = args or kwargs
    return render_ticket_context(get_ticket_context(str(values.get("page_id") or "")))


def notion_list_data_sources(args: dict | None = None, **kwargs: Any) -> str:
    del args, kwargs
    return json.dumps(list_data_sources(), ensure_ascii=False, separators=(",", ":"))


def has_token() -> bool:
    return bool(_setting("NOTION_TOKEN"))


def notion_update_page_properties(args: dict | None = None, **kwargs: Any) -> str:
    values = args or kwargs
    properties = values.get("properties")
    if not isinstance(properties, dict):
        raise ValueError("properties must be an object")
    return json.dumps(
        update_page_properties(str(values.get("page_id") or ""), properties),
        separators=(",", ":"),
    )
