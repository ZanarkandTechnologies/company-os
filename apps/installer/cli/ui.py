"""All interactive input and common customer-facing setup messages."""

from __future__ import annotations

import getpass
import sys

try:
    from prompt_toolkit.application import Application
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.keys import Keys
    from prompt_toolkit.layout import HSplit, Layout, Window
    from prompt_toolkit.layout.dimension import Dimension
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
            ("setup_answers_schema_invalid",),
            "The saved onboarding answers use an older contract. Rerun setup and choose Start over; the existing profile will be preserved as a timestamped backup before the current questions begin.",
        ),
        (
            ("profile_home_must_be_under_profiles",),
            "Choose a Hermes profile path directly under the Hermes profiles directory, for example ~/.hermes/profiles/company-os.",
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




def configure_options(
    label: str, options: list[dict], current: dict, multiple: bool,
) -> dict | None:
    """Edit prefills inline: arrows move rows, Tab fields, Ctrl+Space toggles.

    Mutate ``current`` on every edit so interruption can save a resumable draft.
    Enter accepts; Back/Escape returns None; Ctrl+C/EOF propagates to the caller.
    Field validation belongs to the caller, not this presentation boundary.
    """
    selected = current.setdefault("selected", [])
    inputs = current.setdefault("inputs", {})
    for option in options:
        values = inputs.setdefault(option["id"], {})
        for field in option.get("fields", []):
            values.setdefault(field["id"], str(field.get("default") or ""))
    entries = current.setdefault("entries", {}) if multiple else {}
    options = [dict(option) for option in options]
    for option in list(options):
        for values in entries.get(option["id"], []):
            options.append(dict(option, _values=values, label=option["label"] + " (additional)"))

    def row_values(option):
        return option["_values"] if "_values" in option else inputs[option["id"]]

    def add_entry(option):
        values = {field["id"]: str(field.get("default") or "")
                  for field in option.get("fields", [])}
        entries.setdefault(option["id"], []).append(values)
        options.append(dict(option, _values=values,
                            label=option["label"].removesuffix(" (additional)") + " (additional)"))
        select(option["id"])

    def select(option_id: str, *, toggle: bool = False) -> None:
        if not multiple:
            selected[:] = [option_id]
        elif toggle and option_id in selected:
            selected.remove(option_id)
        elif option_id not in selected:
            selected.append(option_id)

    if not (PROMPT_TOOLKIT_AVAILABLE and sys.stdin.isatty() and sys.stdout.isatty()):
        # The old numbered checklist cannot represent a default. Offer an explicit
        # keep/edit choice rather than silently clearing saved multiple selections.
        labels = [f"{index + 1}. {option['label']}" for index, option in enumerate(options)]
        if multiple:
            action = choose(label, choices=["Keep selections", "Edit selections", "Back"],
                            default="Keep selections" if selected else "Edit selections")
            if action == "Back":
                return None
            if action == "Edit selections":
                picked = choose_many(label, choices=labels + ["Back"],
                                     selected=[labels[i] for i, option in enumerate(options)
                                               if option["id"] in selected])
                if "Back" in picked:
                    return None
                picked_rows = [option for i, option in enumerate(options) if labels[i] in picked]
                selected[:] = list(dict.fromkeys(option["id"] for option in picked_rows))
                base_options = [option for option in options if "_values" not in option]
                for option in base_options:
                    option_id = option["id"]
                    retained = [row_values(row) for row in picked_rows if row["id"] == option_id]
                    if retained:
                        # The first retained row becomes the primary instance. This
                        # also makes selecting only an additional row mean exactly that.
                        inputs[option_id] = retained[0]
                    entries[option_id] = retained[1:]
                options = list(base_options)
                for option in base_options:
                    for values in entries[option["id"]]:
                        options.append(dict(option, _values=values,
                                            label=option["label"] + " (additional)"))
        else:
            default = next((labels[i] for i, option in enumerate(options)
                            if option["id"] in selected), labels[0] if labels else "Back")
            picked = choose(label, choices=labels + ["Back"], default=default)
            if picked == "Back":
                return None
            select(options[labels.index(picked)]["id"])
        for option in options:
            if option["id"] not in selected:
                continue
            for field in option.get("fields", []):
                values = row_values(option)
                values[field["id"]] = _prompt_text(
                    f"{option['label']} — {field['label']}",
                    default=values[field["id"]], console=CONSOLE,
                )
            if multiple and option.get("fields") and confirm(
                f"Add another {option['label'].removesuffix(' (additional)')} entry?", default=False
            ):
                add_entry(option)
        return current

    state = {"row": next((i for i, option in enumerate(options)
                           if option["id"] in selected), 0), "field": 0}

    def active_field():
        if state["row"] >= len(options):
            return None
        option = options[state["row"]]
        fields = option.get("fields", [])
        if not fields:
            return None
        return option, fields[state["field"] % len(fields)]

    def content():
        rows = []
        for index, option in enumerate(options):
            active = state["row"] == index
            style = "class:active" if active else ""
            marker = "[✓] " if option["id"] in selected else "[ ] "
            if active:
                rows.append(("[SetCursorPosition]", ""))
            rows.append((style, marker + option["label"]))
            for field_index, field in enumerate(option.get("fields", [])):
                focused = active and state["field"] == field_index
                value = row_values(option).get(field["id"], "")
                rows.append(("class:field" if focused else "", (
                    f"  {field['label']}{'*' if field.get('required') else ''}: "
                    f"[{value}{'▏' if focused else ''}]"
                )))
            rows.append(("", "\n"))
        if state["row"] == len(options):
            rows.append(("[SetCursorPosition]", ""))
        rows.append(("class:active" if state["row"] == len(options) else "", "← Back"))
        return rows

    bindings = KeyBindings()

    @bindings.add("up", eager=True)
    def up(event):
        state.update(row=(state["row"] - 1) % (len(options) + 1), field=0)

    @bindings.add("down", eager=True)
    def down(event):
        state.update(row=(state["row"] + 1) % (len(options) + 1), field=0)

    @bindings.add("tab", eager=True)
    @bindings.add("s-tab", eager=True)
    def next_field(event):
        pair = active_field()
        if pair:
            step = -1 if event.key_sequence[-1].key == Keys.BackTab else 1
            state["field"] = (state["field"] + step) % len(pair[0]["fields"])

    @bindings.add("c-space", eager=True)
    def toggle(event):
        if state["row"] < len(options):
            select(options[state["row"]]["id"], toggle=True)

    @bindings.add("c-n", eager=True)
    def another(event):
        if multiple and state["row"] < len(options):
            option = options[state["row"]]
            if option.get("fields"):
                add_entry(option)
                state.update(row=len(options) - 1, field=0)

    @bindings.add("c-x", eager=True)
    def remove_entry(event):
        if state["row"] < len(options):
            option = options[state["row"]]
            if "_values" in option:
                additional = entries[option["id"]]
                additional[:] = [value for value in additional if value is not option["_values"]]
                options.pop(state["row"])
                state.update(row=min(state["row"], len(options) - 1), field=0)

    def edit(value: str | None = None, *, clear: bool = False):
        pair = active_field()
        if pair:
            option, field = pair
            values = row_values(option)
            old = values[field["id"]]
            values[field["id"]] = "" if clear else old[:-1] if value is None else old + value
            select(option["id"])

    @bindings.add(" ", eager=True)
    def space(event):
        if active_field():
            edit(" ")
        else:
            toggle(event)

    @bindings.add("backspace", eager=True)
    def erase(event):
        edit()

    @bindings.add("c-u", eager=True)
    def clear(event):
        edit(clear=True)

    @bindings.add(Keys.BracketedPaste)
    @bindings.add(Keys.Any)
    def type_text(event):
        if event.data:
            edit("".join(character if character.isprintable() else " "
                         for character in event.data))

    @bindings.add("enter", eager=True)
    def submit(event):
        if state["row"] == len(options):
            event.app.exit(result=None)
            return
        if not multiple:
            select(options[state["row"]]["id"])
        event.app.exit(result=current)

    @bindings.add("escape", eager=True)
    def back(event):
        event.app.exit(result=None)

    @bindings.add("c-c", eager=True)
    def interrupt(event):
        event.app.exit(exception=KeyboardInterrupt())

    @bindings.add("c-d", eager=True)
    def eof(event):
        event.app.exit(exception=EOFError())

    control = FormattedTextControl(content, focusable=True)
    layout = Layout(HSplit([
        Window(FormattedTextControl([("class:title", f"◆ {label}")]), height=1),
        Window(FormattedTextControl([("class:hint", (
            "↑↓ rows  TAB fields  TYPE edit  CTRL+SPACE toggle  CTRL+U clear  "
            "ENTER confirm  ESC back  CTRL+C save/exit" +
            ("  CTRL+N add entry  CTRL+X remove additional entry" if multiple else "")
        ))]), wrap_lines=True, dont_extend_height=True),
        Window(control, wrap_lines=True, dont_extend_height=True),
    ]), focused_element=control)
    app = Application(layout=layout, key_bindings=bindings,
                      style=Style.from_dict({"title": "bold ansicyan", "hint": "ansibrightblack",
                                             "active": "bold ansigreen", "field": "underline"}),
                      full_screen=False, erase_when_done=True, mouse_support=False)
    app.ttimeoutlen = 0.1
    return app.run()


def _interactive_choice(label: str, choices: list[str], default: str) -> str:
    """Select one option with arrows in an ordinary interactive terminal."""
    selector = RadioList(values=[(choice, choice) for choice in choices])
    selector.current_value = default
    selector._selected_index = choices.index(default) if default in choices else 0
    selector.window.height = Dimension(max=10)
    selector.window.dont_extend_height = lambda: True
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
