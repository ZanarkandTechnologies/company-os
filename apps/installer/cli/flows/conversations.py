"""Guided conversation-source configuration for the Company OS profile."""

from __future__ import annotations

from pathlib import Path

from rich.panel import Panel

from apps.installer import runtime
from apps.installer.conversation_setup import (
    ENV_NAME, ConversationSetupError, default_intake_root,
    discover_codex_session_roots, enabled_sources_for_state, load_policy_if_present,
    save_policy, test_policy,
)
from apps.installer.feature_setup import SetupState
from apps.installer.feature_setup import load_state
from apps.installer.cli.ui import CONSOLE, _prompt_text, confirm


def _required(label: str, default: str = "") -> str:
    while True:
        value = _prompt_text(label, default=default or None, console=CONSOLE).strip()
        if value:
            return value
        CONSOLE.print("[yellow]A value is required. Press Ctrl+C to stop safely.[/yellow]")


def _existing_root(profile_home: Path) -> Path:
    configured = runtime.profile_env_value(profile_home, ENV_NAME)
    return Path(configured).expanduser() if configured else default_intake_root(profile_home)


def _binding_summary(projects: dict) -> str:
    return f"{len(projects)} project(s), {sum(len(items) for items in projects.values())} member/source mapping(s)"


def configure_conversations(profile_home: Path, state: SetupState, *, non_interactive: bool = False) -> None:
    sources = enabled_sources_for_state(state)
    if not sources:
        CONSOLE.print("[dim]Work conversations are disabled; saved private mappings will not be read.[/dim]")
        return
    if non_interactive:
        root = _existing_root(profile_home)
        policy = load_policy_if_present(root) if root.is_dir() else None
        if not policy:
            raise ConversationSetupError("conversation_setup_requires_input")
        runtime.save_profile_secret(profile_home, ENV_NAME, str(root.resolve()))
        return

    CONSOLE.print(Panel.fit(
        "[bold]Connect work conversations[/bold]\n"
        "Add each Company OS Project and participating member. Local Codex reads only sessions whose saved "
        "working directory exactly matches the repository you choose. Conversation bodies remain in private local storage outside source repositories.",
        border_style="cyan",
    ))
    root = Path(_required("Private conversation storage", str(_existing_root(profile_home)))).expanduser()
    if not root.is_absolute():
        raise ConversationSetupError("conversation_intake_path_must_be_absolute")
    root.mkdir(parents=True, exist_ok=True)
    existing = load_policy_if_present(root)
    timezone = state.answers.get("company.timezone", "Asia/Kuala_Lumpur")
    projects: dict[str, list[dict]] = {}
    if existing:
        CONSOLE.print(f"[cyan]Found saved configuration:[/cyan] {_binding_summary(existing['projects'])}")
        if confirm("Keep the saved project and member mappings?", default=True):
            projects = existing["projects"]
        else:
            CONSOLE.print("[dim]The replacement will be written only after validation.[/dim]")

    while not projects or confirm("Add another project/member mapping?", default=not projects):
        project_id = _required("Company OS Project ID")
        member_id = _required("Company OS Person ID")
        bindings = projects.setdefault(project_id, [])
        if "chatgpt_manual" in sources and confirm(
            f"Allow {member_id} to submit selected ChatGPT conversations for {project_id}?", default=True
        ):
            bindings.append({"source": "chatgpt_manual", "member_id": member_id, "cwd": None, "session_roots": []})
        if "codex_local" in sources and confirm(
            f"Connect local Codex Desktop conversations for {member_id}?", default=True
        ):
            cwd = Path(_required("Exact project repository folder", str(Path.cwd()))).expanduser()
            if not cwd.is_absolute() or not cwd.is_dir():
                raise ConversationSetupError("codex_project_folder_must_exist")
            roots = discover_codex_session_roots()
            if not roots:
                CONSOLE.print("[yellow]No local Codex session folders were detected. Manual Codex submissions remain available.[/yellow]")
            bindings.append({"source": "codex_local", "member_id": member_id, "cwd": str(cwd.resolve()), "session_roots": roots})
        if not bindings:
            projects.pop(project_id, None)
            CONSOLE.print("[yellow]Select at least one source for this mapping.[/yellow]")

    policy_path = save_policy(root, timezone=timezone, projects=projects)
    runtime.save_profile_secret(profile_home, ENV_NAME, str(root.resolve()))
    CONSOLE.print(f"[green]Conversation sources saved.[/green] {_binding_summary(projects)}")
    CONSOLE.print(f"[dim]Private policy: {policy_path}[/dim]")
    if confirm("Test this week's configured sources now?", default=True):
        for project_id in projects:
            status = test_policy(root, project_id, sources)
            color = "green" if status.status == "ready" else "yellow"
            CONSOLE.print(
                f"[{color}]{project_id}: {status.status}[/{color}] — {status.conversations} conversation(s), "
                f"{status.messages} message(s), {status.bindings} configured source(s)"
            )
            for gap in status.gaps:
                CONSOLE.print(f"  [dim]Coverage: {gap}[/dim]")


def configure_command(profile_home: Path) -> int:
    """Open only the conversation mapping step for an installed profile."""
    try:
        state = load_state(profile_home / "config" / "setup-answers.json")
        if not enabled_sources_for_state(state):
            CONSOLE.print(Panel.fit(
                "[bold yellow]Work conversations are disabled[/bold yellow]\n"
                "Choose Update Company OS features first and enable a supported conversation source.",
                border_style="yellow",
            ))
            return 1
        configure_conversations(profile_home, state)
        return 0
    except (ConversationSetupError, OSError, ValueError) as error:
        CONSOLE.print(Panel.fit(
            "[bold red]Conversation setup stopped safely[/bold red]\n"
            f"Support detail: {error}", border_style="red"
        ))
        return 2


def status_command(profile_home: Path, *, test: bool = False) -> int:
    """Show redacted mappings and optionally test current-week availability."""
    try:
        state = load_state(profile_home / "config" / "setup-answers.json")
        sources = enabled_sources_for_state(state)
        if not sources:
            CONSOLE.print("[yellow]Work conversations are disabled.[/yellow]")
            return 1
        root = _existing_root(profile_home)
        policy = load_policy_if_present(root)
        if not policy:
            raise ConversationSetupError("conversation_setup_requires_input")
        CONSOLE.print(Panel.fit(
            "[bold]Work conversation status[/bold]\n"
            f"Enabled sources: {', '.join(sources)}\n"
            f"Mappings: {_binding_summary(policy['projects'])}\n"
            f"Private storage: {root}", border_style="cyan"
        ))
        if test:
            for project_id in policy["projects"]:
                result = test_policy(root, project_id, sources)
                color = "green" if result.status == "ready" else "yellow"
                CONSOLE.print(
                    f"[{color}]{project_id}: {result.status}[/{color}] — "
                    f"{result.conversations} conversation(s), {result.messages} message(s)"
                )
                for gap in result.gaps:
                    CONSOLE.print(f"  [dim]Coverage: {gap}[/dim]")
        return 0
    except (ConversationSetupError, OSError, ValueError) as error:
        CONSOLE.print(f"[red]Conversation status unavailable.[/red] Support detail: {error}")
        return 2
