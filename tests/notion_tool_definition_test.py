from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERMES_ROOT = Path(os.getenv("HERMES_AGENT_PATH") or Path.home() / ".hermes/hermes-agent")
sys.path.insert(0, str(HERMES_ROOT))
sys.path.insert(0, str(ROOT / "profiles/howie-ai/plugins/platforms"))

from notion.adapter import _trigger_question, register  # noqa: E402
from tools.registry import registry  # noqa: E402


class Context:
    def register_tool(self, **kwargs):
        registry.register(**kwargs)

    def register_cli_command(self, **kwargs):
        pass

    def register_platform(self, **kwargs):
        pass


register(Context())
names = {
    "notion_get_page",
    "notion_get_ticket_context",
    "notion_list_data_sources",
    "notion_update_page_properties",
}
definitions = registry.get_definitions(names, quiet=True)
assert len(definitions) == 4, definitions
for definition in definitions:
    assert definition["type"] == "function"
    function = definition["function"]
    assert function["name"] in names
    assert function["parameters"]["type"] == "object"
    assert "function" not in function
    assert "type" not in function

assert _trigger_question(" @VishanAI: What is blocked?", "@vishanai") == "What is blocked?"
assert _trigger_question("ordinary comment", "@vishanai") == ""

print("Notion tool definitions have one valid Hermes/OpenAI wrapper.")
