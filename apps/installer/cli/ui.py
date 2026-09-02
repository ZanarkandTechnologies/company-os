"""All interactive input and common customer-facing setup messages."""

from __future__ import annotations

import getpass
import json
import sys

try:
    from prompt_toolkit.application import Application
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.keys import Keys
    from prompt_toolkit.layout import HSplit, Layout, Window
    from prompt_toolkit.layout.controls import FormattedTextControl
    from prompt_toolkit.styles import Style
    from prompt_toolkit.widgets import CheckboxList, RadioList
    PROMPT_TOOLKIT_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only in minimal Python installs
    Application = KeyBindings = Keys = HSplit = Layout = Window = None
    FormattedTextControl = Style = CheckboxList = RadioList = None
    PROMPT_TOOLKIT_AVAILABLE = False
from rich.console import Console
from rich.prompt import Confirm, Prompt


CONSOLE = Console()
UNSET_VALUES = {"", "REPLACE_ME", "—"}


def _friendly_runtime_error(error: Exception) -> str:
    """Translate stable internal failure codes into one customer action."""
    code = str(error)
    messages = (
        (
            ("installed_setup_missing", "profile_install_did_not_create_distribution"),
            "The Hermes profile installation is incomplete. Run setup again and choose Repair setup.",
        ),
        (
            ("profile_setup_receipt_unreadable", "profile_setup_receipt_invalid"),
            "Hermes could not confirm that setup finished. Run setup again and choose Repair setup.",
        ),
        (
            ("workspace_configuration_requires_input",),
            "Workspace setup needs your answers. Run setup interactively instead of unattended mode.",
        ),
        (
            ("feature_setup_migration_required",),
            "This profile predates feature setup. Choose Update Company OS features before updating software; existing schedules and prompts were left unchanged.",
        ),
        (
            ("workspace_configuration_cancelled",),
            "Workspace setup was cancelled. Your saved draft is still available when you rerun setup.",
        ),
        (
            ("model_auth_requires_input", "model_auth_incomplete"),
            "An AI model credential is required. Rerun setup interactively and complete Hermes model authorization.",
        ),
        (
            ("notion_token_invalid",),
            "Notion rejected the integration token. Rerun setup and paste a valid internal integration token.",
        ),
        (
            ("notion_unavailable",),
            "Notion could not be reached, so the token was not changed. Check the internet connection and retry.",
        ),
        (
            ("composio_api_key_requires_input", "composio_api_key_missing"),
            "Gmail or Google Drive needs a Composio project API key. Rerun setup interactively and paste it when prompted.",
        ),
        (
            ("composio_http_401", "composio_http_403"),
            "Composio rejected the saved API key. Rerun setup and choose Repair setup to replace it.",
        ),
        (
            ("composio_unavailable",),
            "Composio could not be reached. Check the internet connection, then rerun setup and choose Test integrations.",
        ),
        (
            ("composio_connections_incomplete",),
            "One or more requested Composio accounts were not connected. Rerun setup and finish every displayed OAuth link.",
        ),
        (
            ("composio_mcp_connection_test_failed",),
            "The Google accounts are connected, but Hermes could not discover the restricted Composio tools. Rerun Repair setup.",
        ),
        (
            ("mcp_authorization_incomplete",),
            "Provider authorization did not finish. Rerun setup and complete the browser authorization before continuing.",
        ),
        (
            ("mcp_connection_test_failed",),
            "Provider authorization completed, but Hermes could not discover its tools. Rerun Repair setup.",
        ),
    )
    for prefixes, message in messages:
        if code.startswith(prefixes):
            return message
    return (
        "This setup step could not finish. Check the message below, then rerun setup "
        f"and choose Repair setup if needed.\nSupport detail: {code}"
    )


def current_value(raw: str) -> str:
    value = raw.strip()
    if value.startswith('"') and value.endswith('"'):
        try:
            return str(json.loads(value))
        except json.JSONDecodeError:
            pass
    return "" if value in UNSET_VALUES else value


def _prompt_text(*args, **kwargs) -> str:
    """Normalize Rich's optional prompt result at the interactive boundary."""
    value = Prompt.ask(*args, **kwargs)
    return str(value or "").strip()


def confirm(label: str, *, default: bool) -> bool:
    return bool(Confirm.ask(label, default=default, console=CONSOLE))


def choose(label: str, *, choices: list[str], default: str) -> str:
    if PROMPT_TOOLKIT_AVAILABLE and sys.stdin.isatty() and sys.stdout.isatty():
        return _interactive_choice(label, choices, default)
    return _prompt_text(
        label,
        choices=choices,
        default=default,
        console=CONSOLE,
    )


def choose_many(
    label: str,
    *,
    choices: list[str],
    selected: list[str] | None = None,
) -> list[str]:
    """Choose zero or more values with the same portable interaction model."""
    selected_indices = [
        index for index, value in enumerate(choices) if value in (selected or [])
    ]
    if PROMPT_TOOLKIT_AVAILABLE and sys.stdin.isatty() and sys.stdout.isatty():
        indices = _interactive_checklist(label, choices, selected_indices)
    else:
        indices = _numbered_checklist(label, choices)
    return [choices[index] for index in indices]


def _interactive_choice(label: str, choices: list[str], default: str) -> str:
    """Select one option with arrows in an ordinary interactive terminal."""
    selector = RadioList(values=[(choice, choice) for choice in choices])
    selector.current_value = default
    bindings = KeyBindings()

    @bindings.add("enter", eager=True)
    def confirm_choice(event) -> None:
        highlighted_value = selector.values[selector._selected_index][0]
        event.app.exit(result=str(highlighted_value))

    @bindings.add(Keys.ControlC, eager=True)
    def cancel_choice(event) -> None:
        event.app.exit(exception=KeyboardInterrupt())

    layout = Layout(
        HSplit(
            [
                Window(
                    FormattedTextControl([("class:title", f"◆ {label}")]),
                    height=1,
                ),
                Window(
                    FormattedTextControl(
                        [("class:hint", "  ↑↓ navigate  ENTER confirm  CTRL+C cancel")]
                    ),
                    height=1,
                ),
                Window(height=1),
                selector,
            ]
        ),
        focused_element=selector,
    )
    return Application(
        layout=layout,
        key_bindings=bindings,
        style=Style.from_dict(
            {
                "title": "bold ansicyan",
                "hint": "ansibrightblack",
                "radio-selected": "bold ansigreen",
                "radio-checked": "ansigreen",
            }
        ),
        full_screen=False,
        erase_when_done=True,
        mouse_support=False,
    ).run()


def pause(label: str) -> None:
    Prompt.ask(label, default="", show_default=False, console=CONSOLE)


def _prompt_secret(label: str) -> str:
    """Require one nonempty secret without echoing or persisting blank input."""
    while True:
        value = str(getpass.getpass(label) or "").strip()
        if value:
            return value
        CONSOLE.print("[yellow]A value is required. Press Ctrl+C to stop safely.[/yellow]")


def _numbered_checklist(title: str, items: list[str]) -> list[int]:
    """Hermes-style non-curses fallback, also useful for piped test input."""
    CONSOLE.print(f"\n[bold cyan]◆ {title}[/bold cyan]")
    CONSOLE.print("[dim]Choose roles to configure; Enter skips this section.[/dim]")
    for index, item in enumerate(items, start=1):
        CONSOLE.print(f"  [dim]{index}.[/dim] {item}")
    while True:
        raw = _prompt_text(
            "Selection (comma-separated numbers or 'all')",
            default="",
            show_default=False,
            console=CONSOLE,
        ).lower()
        if not raw:
            return []
        if raw == "all":
            return list(range(len(items)))
        try:
            chosen = sorted({int(value.strip()) - 1 for value in raw.split(",")})
        except ValueError:
            chosen = []
        if chosen and all(0 <= index < len(items) for index in chosen):
            return chosen
        CONSOLE.print(f"[yellow]Enter numbers from 1 to {len(items)}, 'all', or Enter.[/yellow]")


def _interactive_checklist(
    title: str,
    labels: list[str],
    selected_indices: list[int] | None = None,
) -> list[int]:
    """Return selected indices from a portable, non-full-screen checklist."""
    checklist = CheckboxList(
        values=list(enumerate(labels)),
        default_values=selected_indices or [],
        open_character="[",
        select_character="✓",
        close_character="]",
    )
    bindings = KeyBindings()

    # CheckboxList normally treats Enter like Space. Eager application bindings
    # make Enter finish this wizard step while Space remains the toggle key.
    @bindings.add("enter", eager=True)
    def confirm(event) -> None:
        event.app.exit(result=list(checklist.current_values))

    @bindings.add(Keys.Escape, eager=True)
    def skip(event) -> None:
        event.app.exit(result=[])

    @bindings.add(Keys.ControlC, eager=True)
    def cancel(event) -> None:
        event.app.exit(exception=KeyboardInterrupt())

    layout = Layout(
        HSplit(
            [
                Window(
                    FormattedTextControl([("class:title", f"◆ {title}")]),
                    height=1,
                ),
                Window(
                    FormattedTextControl(
                        [("class:hint", "  ↑↓ navigate  SPACE toggle  ENTER confirm  ESC skip")]
                    ),
                    height=1,
                ),
                Window(height=1),
                checklist,
            ]
        ),
        focused_element=checklist,
    )
    return Application(
        layout=layout,
        key_bindings=bindings,
        style=Style.from_dict(
            {
                "title": "bold ansicyan",
                "hint": "ansibrightblack",
                "checkbox-selected": "bold ansigreen",
                "checkbox-checked": "ansigreen",
            }
        ),
        # Keeping this false avoids the alternate screen used by dialog helpers.
        full_screen=False,
        erase_when_done=True,
        mouse_support=False,
    ).run()
