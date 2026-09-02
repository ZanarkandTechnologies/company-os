"""Feature-first automation setup with resumable answers and Back navigation."""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from pathlib import Path

from rich.panel import Panel

from apps.installer.feature_setup import FeatureSetupError, load_state, render_text, serialize_state, with_optional_defaults, write_batch
from apps.installer.cli.ui import CONSOLE, _prompt_text, choose, choose_many, confirm


@dataclass(frozen=True)
class Preset:
    label: str
    detail: str
    value: str
    prompt: str | None = None
    providers: tuple[str, ...] = ()
    target_provider: str | None = None


@dataclass(frozen=True)
class QuestionAnswer:
    value: str
    selection: str
    providers: tuple[str, ...]
    provider_targets: dict[str, str]


@dataclass(frozen=True)
class Question:
    key: str
    section: str
    question: str
    explainer: str
    presets: tuple[Preset, ...]
    custom_hint: str


QUESTIONS = (
    Question("memory.decisions", "Memory · Decisions", "What decisions should Hermes remember?", "This controls the evidence retained for later comparisons and reports. Example: why a supplier or workflow was selected.", (Preset("Standard", "Context, options, rationale, and outcome.", "Extract decisions with their context, options, rationale, and outcome."), Preset("Lightweight", "Decision, reason, and outcome only.", "Extract each decision, its reason, and its outcome.")), "Describe the decision information to extract"),
    Question("memory.employees", "Memory · Employees", "What should employee memory capture?", "This private memory aggregates work across Projects for weekly growth reporting; it is not written to the public People table by default.", (Preset("Growth review", "Contributions, blockers, ownership, and development.", "Aggregate each employee's contributions, blockers, ownership, and growth evidence across Projects."), Preset("Delivery only", "Completed work, delayed work, and commitments.", "Aggregate each employee's completed Work, delayed Work, and next commitments across Projects.")), "Describe the employee evidence to retain"),
    Question("memory.sops", "Memory · SOPs", "What should Hermes learn from repeated work?", "This defines how completed Work becomes reusable process knowledge. Example: compare actual execution with the expected workflow.", (Preset("Baseline comparison", "Workflow, variance, and reusable lesson.", "Compare repeated Work against its workflow baseline and retain reusable process lessons."), Preset("Procedure capture", "Trigger, steps, inputs, owner, and outputs.", "Extract reusable procedures with their trigger, steps, inputs, owner, and outputs.")), "Describe the SOP knowledge to extract"),
    Question("daily.projects", "Daily · Projects", "Where are Projects stored?", "Daily begins from this exact source and reads every active Project page. It never searches for a replacement source.", (Preset("Notion", "Use one exact Notion database or data-source URL.", "Fetch all active Projects from `{input}`.", "Notion Projects URL", ("notion",), "notion"), Preset("Custom source", "Provide complete MCP-readable fetch instructions.", "{input}", "Project source instructions")), "Describe exactly where and how to fetch Projects"),
    Question("daily.work", "Daily · Work", "How should Daily find Work for each Project?", "Work may live in Project-linked Notion databases, one shared database, or Multica. Daily preserves each source's raw fields before mapping them.", (Preset("Project-local Notion", "Inspect only task sources explicitly linked in each Project.", "Discover Work only from Notion task databases explicitly linked inside that Project page.", None, ("notion",)), Preset("Shared Notion database", "Query one shared source and require an exact Project relation.", "Fetch Work from `{input}` with the hosted Notion MCP. Include only records with an exact relation to the current Project.", "Master Work database URL", ("notion",), "notion"), Preset("Multica", "Query one exact Multica workspace, optionally limited to a project.", "Fetch Work with `multica_list_issues` from {input}. Read pages of 100 with increasing offsets until a page returns fewer than 100 issues. Keep each issue ID, identifier, project ID, status, assignee, dates, URL or source reference, description, metadata, and raw properties.", "Multica target, for example: workspace_id=…; project=all", ("multica",), "multica")), "Describe how each Project's Work should be discovered"),
    Question("daily.meetings", "Daily · Meetings", "Where are meeting notes stored?", "Meeting evidence helps explain changes and blockers. Daily reads only notes tied to selected Work or the configured source.", (Preset("Inside Work", "Read embedded or explicitly linked meeting notes.", "Read Meeting notes embedded in or explicitly linked from selected Work."), Preset("Separate Notion source", "Read a dedicated Notion meeting-note source.", "Fetch Meeting notes from `{input}` and include only notes linked to the selected Work or Project.", "Meeting notes URL", ("notion",), "notion")), "Describe where and how to fetch relevant meeting notes"),
    Question("daily.existing_memory", "Daily · Existing Memory", "Where should Daily read and update Project Memory?", "Project Memory is the current week's private operating cache. Daily must update a local file owned by PM Daily; external sync is configured in Weekly.", (Preset("Standard local path", "Use weeks/<week>/project-memory.", "Read that Project's current-week Project Memory from the local weekly filesystem and update that same file."), Preset("Custom local path", "Use another private filesystem path.", "Read and update Project Memory at this private local filesystem location: {input}.", "Private local Project Memory path")), "Describe the private local Project Memory location and update rule"),
    Question("daily.people", "Daily · People", "Where are People and their contact preferences stored?", "Daily reads only People linked to selected Work. It maps the source's communication-preference and matching endpoint fields without assuming fixed column names.", (Preset("Notion People", "Provide one exact Notion People database URL.", "Fetch People from `{input}`. Map each linked Person's communication-preference field and its matching contact endpoint while preserving the original field names.", "Notion People URL", ("notion",), "notion"), Preset("No direct contacts", "Keep ticket comments only; do not fetch contact endpoints.", "Do not fetch a People directory for delivery. Keep direct delivery disabled and use exact Work comments only.")), "Describe the People source and its preference fields"),
    Question("daily.staleness", "Daily · Progress Chasing", "What makes Work stale?", "This rule decides when PM Daily creates a progress follow-up. It should identify genuine delivery risk without chasing healthy recent work.", (Preset("Standard", "Overdue, blocked, or no meaningful update for seven days.", "Treat Work as stale when it is overdue, blocked, or has no meaningful update for seven days."), Preset("Age threshold", "Choose a custom number of inactive days.", "Treat Work as stale when it is overdue, blocked, or has no meaningful update for {input} days.", "Number of days")), "Define the exact stale-work conditions"),
    Question("daily.progress_route", "Daily · Progress Delivery", "How should progress follow-ups reach people?", "The exact Work comment is the safest shared record. An optional direct copy can use the linked Person's stored preference.", (Preset("Ticket + preference", "Comment on Work, then Gmail or Telegram when configured.", "Post every progress follow-up on the exact Notion Work item, then also use the linked Person's preferred Gmail or Telegram endpoint when present.", None, ("notion", "gmail", "telegram")), Preset("Ticket only", "Use only the exact linked Work comment.", "Post every progress follow-up only on the exact linked Work item. Do not send a direct copy.", None, ("notion",))), "Describe the allowed progress-follow-up routes"),
    Question("daily.documentation_quality", "Daily · Documentation", "What counts as poor documentation?", "This rule reviews completed Work. A request should name missing evidence rather than asking for generic detail.", (Preset("Standard", "Missing outcome, evidence, rationale, or next action.", "Treat completed Work as poorly documented when its outcome, evidence, rationale, or next action is missing."), Preset("Evidence only", "Require a recorded outcome and verification evidence.", "Treat completed Work as poorly documented when either its outcome or verification evidence is missing.")), "Define good and bad documentation quality"),
    Question("daily.documentation_route", "Daily · Documentation Delivery", "How should documentation requests be delivered?", "The request must remain attached to the exact Work record unless you explicitly authorize another route.", (Preset("Ticket only", "Comment on the exact Work item.", "Deliver documentation requests only as comments on the exact Notion Work item.", None, ("notion",)), Preset("Ticket + preference", "Also send through the linked Person's preferred channel.", "Comment on the exact Notion Work item, then send the same request and Work URL through the linked Person's preferred configured channel.", None, ("notion", "gmail", "telegram"))), "Describe the allowed documentation-request routes"),
    Question("weekly.reports_destination", "Weekly · Reports", "Where should weekly reports be stored?", "This controls copies of Project, Department, and Company reports. Local files remain available even when external sync is enabled.", (Preset("Private local", "Keep reports only in the Hermes workspace.", "Keep reports in the private local workspace and call no storage integration."), Preset("Google Drive", "Upload exact report files to one folder.", "Upload each final report without rewriting it to this Google Drive folder: {input}. Read back and record each created file URL.", "Google Drive folder URL", ("google_drive",), "google_drive")), "Describe the report storage destination and sync behavior"),
    Question("weekly.sops_destination", "Weekly · SOP Memory", "Where should approved SOP Memory be stored?", "Only finalized and approved SOP knowledge may leave the private workspace; proposals remain local.", (Preset("Private local", "Keep SOP Memory only in Hermes.", "Keep SOP Memory in the private local workspace and call no provider integration."), Preset("Google Drive", "Sync approved SOPs to one exact Drive folder.", "Sync only approved finalized SOP Memory to {input}, then read back the created file.", "Google Drive folder URL", ("google_drive",), "google_drive")), "Describe the approved SOP destination and sync rule"),
    Question("weekly.employee_memory_destination", "Weekly · Employee Memory", "Where should Employee Memory be stored?", "Employee evaluation can be sensitive. Private local storage is the safe default; never write it to a public People database.", (Preset("Private local", "Keep Employee Memory only in Hermes.", "Keep Employee Memory in the private local workspace and call no provider integration."), Preset("Private Google Drive", "Sync to an access-controlled Drive folder.", "Sync Employee Memory only to this private Google Drive folder: {input}. Never use a public People database.", "Private Google Drive folder URL", ("google_drive",), "google_drive")), "Describe the private Employee Memory destination"),
    Question("weekly.decisions_destination", "Weekly · Decision Memory", "Where should promoted Decision Memory be stored?", "Only promoted final decisions sync. Draft or ambiguous decisions remain private until resolved.", (Preset("Private local", "Keep decisions only in Hermes.", "Keep Decision Memory in the private local workspace and call no provider integration."), Preset("Google Drive", "Sync promoted decisions to one exact Drive folder.", "Sync only promoted final Decision Memory to {input}, then read back the created file.", "Google Drive folder URL", ("google_drive",), "google_drive")), "Describe the Decision Memory destination"),
    Question("weekly.other_memory_destination", "Weekly · Other Memory", "Where should other extracted memory be stored?", "This applies to any additional memory types you define later. It does not override Project, SOP, Employee, or Decision rules.", (Preset("Private local", "Keep additional types only in Hermes.", "Keep every additional extracted memory type in the private local workspace."), Preset("Private Google Drive", "Sync additional types to one controlled Drive folder.", "Sync additional extracted memory only to this private Google Drive folder: {input}.", "Private Google Drive folder URL", ("google_drive",), "google_drive")), "Describe additional memory types and their destinations"),
    Question("weekly.report_recipients", "Weekly · Report Delivery", "Who should receive completed reports?", "Weekly sends the exact executive draft only to the recipients and channel selected here. Choose Custom to combine channels or add special delivery rules. Credentials are connected later.", (Preset("Gmail", "Send to one or more comma-separated email addresses.", "Send the exact executive distribution draft with Gmail to: {input}. Record each returned message ID.", "Comma-separated Gmail addresses", ("gmail",)), Preset("Telegram", "Send to one or more comma-separated Telegram IDs.", "Send the exact executive distribution draft with Telegram to: {input}. Record each returned message ID.", "Comma-separated Telegram recipient IDs", ("telegram",))), "Describe channels, separate recipient lists, and delivery instructions"),
    Question("weekly_meeting.destination", "Weekly · Meeting Ticket", "Should Hermes create a weekly meeting ticket?", "A separate Monday automation can create one planning ticket per ISO week. It checks for the exact weekly title before creating anything.", (Preset("Disabled", "Create no weekly meeting ticket.", "Do not create a weekly meeting ticket. Record `skipped_disabled` and call no task integration."), Preset("Multica", "Create it in one exact Multica workspace and project.", "Use `multica_list_issues` and `multica_create_issue` in {input}.", "Multica target: workspace_id=…; project=…", ("multica",), "multica")), "Describe the exact task system, workspace, and project"),
    Question("weekly_meeting.template", "Weekly · Meeting Ticket", "What should the weekly meeting ticket contain?", "The title includes the ISO week for idempotency. The description gives the meeting owner a ready-to-use agenda.", (Preset("Operating review", "Reports, risks, decisions, owners, and next-week commitments.", "Title the ticket `Weekly operating review — YYYY-Www`. Include links or paths to the weekly reports, unresolved risks, decisions needed, owners, and next-week commitments."), Preset("Short agenda", "Wins, blockers, decisions, and actions.", "Title the ticket `Weekly meeting — YYYY-Www`. Include wins, blockers, decisions required, and action items with owners.")), "Write the title pattern and complete ticket body instructions"),
    Question("weekly.project_memory_destination", "Project Memory · Sync", "Should Project Memory sync outside Hermes?", "The complete weekly Project Memory stays private by default. If you sync it, only the sections named here are written back to each exact Project record.", (Preset("Private local", "Keep the complete memory only in Hermes.", "Keep Project Memory in the private local workspace and call no provider integration."), Preset("Notion Project records", "Write selected sections back to each exact Project record.", "Sync only these Project Memory sections to the exact source Project record: {input}.", "Sections to sync, such as Status and Risks", ("notion",))), "Describe the destination and exact sections allowed to sync"),
)

CUSTOM_PROVIDERS = {
    "daily.projects": ("notion",),
    "daily.work": ("notion", "multica"),
    "daily.meetings": ("notion",),
    "daily.people": ("notion",),
    "daily.progress_route": ("notion", "gmail", "telegram", "whatsapp"),
    "daily.documentation_route": ("notion", "gmail", "telegram", "whatsapp"),
    "weekly.reports_destination": ("notion", "google_drive"),
    "weekly.sops_destination": ("notion", "google_drive"),
    "weekly.employee_memory_destination": ("google_drive",),
    "weekly.decisions_destination": ("notion", "google_drive"),
    "weekly.other_memory_destination": ("google_drive",),
    "weekly.report_recipients": ("gmail", "telegram", "whatsapp"),
    "weekly_meeting.destination": ("multica",),
    "weekly.project_memory_destination": ("notion",),
}


def _ask_question(question: Question, current: str | None, position: int) -> QuestionAnswer | None:
    if question.key in {
        "daily.progress_route", "daily.documentation_route", "weekly.report_recipients"
    }:
        return _ask_delivery_question(question, current, position)
    preset_lines = "\n".join(
        f"[cyan]{index}.[/cyan] [bold]{preset.label}[/bold] — {preset.detail}"
        for index, preset in enumerate(question.presets, 1)
    )
    current_line = f"\n\n[dim]Current answer: {current}[/dim]" if current else ""
    custom_choice = str(len(question.presets) + 1)
    CONSOLE.print(Panel(
        f"[bold]{question.question}[/bold]\n\n{question.explainer}\n\n{preset_lines}\n"
        f"[cyan]{custom_choice}.[/cyan] [bold]Custom…[/bold] — {question.custom_hint}{current_line}",
        title=f"{position}/{len(QUESTIONS)} · {question.section}", border_style="cyan",
    ))
    choices = [str(index) for index in range(1, len(question.presets) + 2)] + (["keep"] if current else []) + ["back"]
    selected = choose("Choose an answer", choices=choices, default="keep" if current else "1")
    if selected == "back":
        return None
    if selected == "keep":
        return QuestionAnswer(current or "", "keep", (), {})
    if selected == custom_choice:
        value = _required_text(question.custom_hint, None)
        if value.casefold() == "back":
            return None
        providers = _ask_custom_providers(question.key)
        if providers is None:
            return None
        targets = _ask_provider_targets(providers)
        if targets is None:
            return None
        for provider, target in targets.items():
            if target not in value:
                value += f" Use `{target}` as the exact {provider} integration target."
        return QuestionAnswer(value, "custom", providers, targets)
    preset = question.presets[int(selected) - 1]
    if preset.prompt:
        detail = _required_text(preset.prompt, None)
        if detail.casefold() == "back":
            return None
        targets = {preset.target_provider: detail} if preset.target_provider else {}
        return QuestionAnswer(
            preset.value.format(input=detail),
            f"preset_{selected}",
            preset.providers,
            targets,
        )
    return QuestionAnswer(preset.value, f"preset_{selected}", preset.providers, {})


def _ask_delivery_question(
    question: Question, current: str | None, position: int
) -> QuestionAnswer | None:
    """Collect real channel combinations and the value each channel consumes."""
    is_weekly = question.key == "weekly.report_recipients"
    labels = ["Notion Work comment", "Gmail", "Telegram", "WhatsApp", "Custom instructions"]
    if is_weekly:
        labels = labels[1:]
    if current:
        labels.insert(0, "Keep current")
    labels.append("Back")
    current_line = f"\n\n[dim]Current answer: {current}[/dim]" if current else ""
    CONSOLE.print(Panel(
        f"[bold]{question.question}[/bold]\n\n{question.explainer}\n\n"
        "Select every enabled channel. Each selected channel gets its own target field."
        f"{current_line}",
        title=f"{position}/{len(QUESTIONS)} · {question.section}", border_style="cyan",
    ))
    selected = choose_many(
        "Delivery channels",
        choices=labels,
        selected=["Keep current"] if current else None,
    )
    if "Back" in selected:
        return None
    if "Keep current" in selected:
        return QuestionAnswer(current or "", "keep", (), {})
    if not selected:
        return QuestionAnswer(
            "Keep the executive distribution draft local and send nothing."
            if is_weekly else "Keep this follow-up local and send nothing.",
            "channels_none", (), {},
        )
    providers: list[str] = []
    instructions: list[str] = []
    artifact = "executive distribution draft" if is_weekly else (
        "progress follow-up" if question.key == "daily.progress_route" else "documentation request"
    )
    for label in selected:
        if label == "Notion Work comment":
            providers.append("notion")
            instructions.append(f"Post each {artifact} to its exact Notion Work `source_url`; verify the exact comment by reading it back.")
        elif label == "Gmail":
            providers.append("gmail")
            target = _required_text("Gmail recipients" if is_weekly else "People field containing the Gmail address", None)
            if target.casefold() == "back":
                return None
            instructions.append(f"Send the exact {artifact} with Gmail to {target}; record the returned message ID.")
        elif label == "Telegram":
            providers.append("telegram")
            target = _required_text("Telegram targets (comma-separated IDs)" if is_weekly else "People field containing the Telegram target", None)
            if target.casefold() == "back":
                return None
            instructions.append(f"Send the exact {artifact} with `messages_send` to these Telegram targets: {target}; record each returned message ID.")
        elif label == "WhatsApp":
            providers.append("whatsapp")
            target = _required_text("WhatsApp targets (comma-separated E.164 numbers or JIDs)" if is_weekly else "People field containing the WhatsApp E.164 number or JID", None)
            if target.casefold() == "back":
                return None
            instructions.append(f"Send the exact {artifact} with `messages_send` to these WhatsApp targets: {target}; record each returned message ID.")
        else:
            custom = _required_text(question.custom_hint, None)
            if custom.casefold() == "back":
                return None
            instructions.append(custom)
            custom_providers = _ask_custom_providers(question.key)
            if custom_providers is None:
                return None
            providers.extend(custom_providers)
    return QuestionAnswer(" ".join(instructions), "channels", tuple(dict.fromkeys(providers)), {})


def _ask_custom_providers(question_key: str) -> tuple[str, ...] | None:
    CONSOLE.print("[dim]Choose the integrations this custom instruction requires. This is used only during setup authorization.[/dim]")
    allowed = CUSTOM_PROVIDERS.get(question_key, ())
    choices = ["none", *allowed]
    if len(allowed) > 1:
        choices.append("multiple")
    choices.append("back")
    choice = choose(
        "Required integrations",
        choices=choices,
        default="none",
    )
    if choice == "back":
        return None
    if choice != "multiple":
        return () if choice == "none" else (choice,)
    while True:
        raw = _required_text("Comma-separated integrations", None)
        if raw.casefold() == "back":
            return None
        values = tuple(sorted({value.strip() for value in raw.split(",") if value.strip()}))
        if set(values) <= set(allowed):
            return values
        CONSOLE.print(f"[yellow]Use only: {', '.join(allowed)}.[/yellow]")


def _ask_provider_targets(providers: tuple[str, ...]) -> dict[str, str] | None:
    targets: dict[str, str] = {}
    for provider in providers:
        if provider not in {"notion", "google_drive"}:
            continue
        value = _required_text(f"Exact {provider} source or destination URL", None)
        if value.casefold() == "back":
            return None
        targets[provider] = value
    return targets


def _required_text(label: str, current: str | None) -> str:
    while True:
        value = _prompt_text(label, default=current or None, console=CONSOLE)
        if value:
            return value
        CONSOLE.print("[yellow]A value is required. Enter it or press Ctrl+C to stop safely.[/yellow]")


def collect_answers(
    existing: dict[str, str] | None = None,
    selections: dict[str, str] | None = None,
    requirements: dict[str, tuple[str, ...]] | None = None,
    targets: dict[str, dict[str, str]] | None = None,
) -> tuple[dict[str, str], dict[str, str], dict[str, tuple[str, ...]], dict[str, dict[str, str]], bool]:
    answers = dict(existing or {})
    selected = dict(selections or {})
    providers = dict(requirements or {})
    provider_targets = dict(targets or {})
    index = 0
    while index < len(QUESTIONS):
        question = QUESTIONS[index]
        answer = _ask_question(question, answers.get(question.key), index + 1)
        if answer is None:
            if index == 0:
                return answers, selected, providers, provider_targets, True
            index = max(0, index - 1)
            continue
        effective_providers = (
            providers.get(question.key, ())
            if answer.selection == "keep"
            else answer.providers
        )
        if (
            question.key in {"daily.progress_route", "daily.documentation_route"}
            and {"gmail", "telegram", "whatsapp"} & set(effective_providers)
            and selected.get("daily.people") == "preset_2"
        ):
            CONSOLE.print(
                "[yellow]Direct delivery needs a People source. Change People, "
                "or choose ticket-only delivery.[/yellow]"
            )
            index = next(
                position
                for position, candidate in enumerate(QUESTIONS)
                if candidate.key == "daily.people"
            )
            continue
        if (
            question.key in {"daily.progress_route", "daily.documentation_route"}
            and "notion" in effective_providers
            and selected.get("daily.work") == "preset_3"
        ):
            CONSOLE.print(
                "[yellow]Multica Work has no Notion Work comment target. "
                "Choose Gmail, Telegram, WhatsApp, or local-only delivery.[/yellow]"
            )
            continue
        answers[question.key] = answer.value
        if answer.selection != "keep":
            selected[question.key] = answer.selection
            providers[question.key] = answer.providers
            provider_targets[question.key] = answer.provider_targets
        index += 1
    return answers, selected, providers, provider_targets, False


def collect_identity(existing: dict[str, str] | None = None, *, start_at_end: bool = False) -> dict[str, str] | None:
    answers = dict(existing or {})
    fields = (
        ("company.name", "Company name", "Used in the workspace heading, automation job names, and reports."),
        ("company.description", "Company description", "A short operating description helps Hermes interpret Projects, Work, and reports in the right business context."),
        ("company.timezone", "Company timezone", "Daily and Weekly schedules, date windows, and overdue checks use this IANA timezone, for example Asia/Kuala_Lumpur."),
    )
    index = len(fields) - 1 if start_at_end else 0
    while index < len(fields):
        key, question, explainer = fields[index]
        CONSOLE.print(Panel(f"[bold]{question}[/bold]\n\n{explainer}\n\nType [cyan]back[/cyan] to return to the previous question.", title=f"{index + 1}/{len(fields)} · Hermes Workspace", border_style="cyan"))
        value = _required_text(question, answers.get(key))
        if value.casefold() == "back":
            if index == 0:
                return None
            index = max(0, index - 1)
            continue
        answers[key] = value
        index += 1
    return answers


def _render_workspace_identity(content: str, answers: dict[str, str]) -> str:
    before = content
    after = before
    mapping = {
        "company_name": answers["company.name"],
        "company_description": answers["company.description"],
        "company_timezone": answers["company.timezone"],
    }
    for field, value in mapping.items():
        pattern = re.compile(rf"^{re.escape(field)}:\s*.*$", re.MULTILINE)
        if not pattern.search(after):
            raise FeatureSetupError(f"workspace_identity_field_missing:{field}")
        escaped = value.replace('"', '\\"')
        after = pattern.sub(f'{field}: "{escaped}"', after, count=1)
    return after


def configure_features(root: Path, *, apply: bool = True) -> int:
    answer_path = root / "config" / "setup-answers.json"
    state = load_state(answer_path)
    answers = with_optional_defaults(state.answers)
    selections = state.selections
    requirements = state.provider_requirements
    targets = state.provider_targets
    return_to_identity = False
    while True:
        identity = collect_identity(answers, start_at_end=return_to_identity)
        if identity is None:
            return 1
        answers = identity
        answers, selections, requirements, targets, return_to_identity = collect_answers(
            answers, selections, requirements, targets
        )
        if not return_to_identity:
            break
    answers["weekly.projects"] = answers["daily.projects"]
    selections["weekly.projects"] = selections.get("daily.projects", "derived")
    requirements["weekly.projects"] = requirements.get("daily.projects", ())
    targets["weekly.projects"] = targets.get("daily.projects", {})
    paths = (
        root / "automations" / "daily-operating-update.md",
        root / "automations" / "weekly-operating-review.md",
        root / "automations" / "weekly-meeting-ticket.md",
    )
    previews: list[str] = []
    workspace = root / "workspace.hermes.md"
    workspace_source = workspace if workspace.is_file() else root / "workspace.hermes.template.md"
    workspace_before = workspace_source.read_text(encoding="utf-8")
    workspace_after = _render_workspace_identity(workspace_before, answers)
    previews.extend(difflib.unified_diff(workspace_before.splitlines(), workspace_after.splitlines(), fromfile=str(workspace), tofile=str(workspace), lineterm=""))
    for path in paths:
        before = path.read_text(encoding="utf-8")
        after, _ = render_text(before, answers)
        previews.extend(difflib.unified_diff(before.splitlines(), after.splitlines(), fromfile=str(path), tofile=str(path), lineterm=""))
    CONSOLE.print(Panel("\n".join(previews) or "No automation changes.", title="Automation preview", border_style="cyan"))
    if apply and not confirm("Save answers and sync the automation prompts?", default=True):
        return 1
    if apply:
        rendered = {
            workspace: workspace_after,
            answer_path: serialize_state(answers, selections, requirements, targets),
        }
        for path in paths:
            rendered[path] = render_text(path.read_text(encoding="utf-8"), answers)[0]
        write_batch(rendered)
        CONSOLE.print(f"[green]Automation prompts synced.[/green] Answers: {answer_path}")
    return 0
