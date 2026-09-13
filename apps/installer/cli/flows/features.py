"""JSON-defined questions, editable saved answers, and reviewed bundle generation."""
from __future__ import annotations
import copy
import json
from pathlib import Path
from zoneinfo import available_timezones
from rich.panel import Panel
from apps.installer.feature_setup import FeatureSetupError, write_batch
from apps.installer import prompt_generation as generation
from apps.installer.cli.ui import CONSOLE, _prompt_text, choose, confirm, configure_options



def _select_timezone(current: str | None) -> str | None:
    """Select one valid IANA timezone without requiring exact free-text input."""
    zones = sorted(
        zone for zone in available_timezones()
        if not zone.startswith(("posix/", "right/"))
    )
    grouped: dict[str, list[str]] = {}
    for zone in zones:
        region = zone.split("/", 1)[0] if "/" in zone else "Global"
        grouped.setdefault(region, []).append(zone)
    current_region = (
        current.split("/", 1)[0] if current and "/" in current else "Global"
    )
    regions = sorted(grouped)
    if current_region not in grouped:
        current_region = "Global" if "Global" in grouped else regions[0]

    while True:
        region_choices = regions + ["Back"]
        region = choose(
            "Timezone region",
            choices=region_choices,
            default=current_region,
        )
        if region == "Back":
            return None
        zone_choices = grouped[region] + ["Back to regions"]
        default_zone = current if current in grouped[region] else grouped[region][0]
        zone = choose(
            "Company timezone",
            choices=zone_choices,
            default=default_zone,
        )
        if zone == "Back to regions":
            current_region = region
            continue
        return zone



def _save_draft(path: Path, document: dict) -> None:
    write_batch({path: json.dumps(document, indent=2, ensure_ascii=False, sort_keys=True) + "\n"})


def configure_features(root: Path, *, apply: bool = True, import_answers: Path | None = None,
                       output_dir: Path | None = None) -> int:
    root = root.resolve()
    output = output_dir.resolve() if output_dir else root
    answer_path = root / "config" / "setup-answers.json"
    draft_path = root / "config" / "setup-answers.draft.json"
    _, questions = generation.discover(root)
    selected_path = draft_path if draft_path.is_file() else answer_path
    if import_answers is not None:
        if not import_answers.is_file():
            raise FeatureSetupError(f"setup_import_missing:{import_answers}")
        if selected_path.exists() and not confirm("Review imported answers instead of the existing local answers/draft?", default=False):
            return 1
        selected_path = import_answers
    loaded = generation.load_document(selected_path)
    document = generation.migrate(loaded, questions)
    values = document.setdefault("values", {})
    if draft_path.exists() and import_answers is None:
        CONSOLE.print("Resuming saved onboarding draft. Completed fields remain editable.")
    if document.get("legacy"):
        CONSOLE.print("Review older answers; new choices never inherit write authority automatically.")
    index = 0
    try:
        while index < len(questions):
            question = questions[index]
            key = question["id"]
            values.setdefault(key, copy.deepcopy(generation.default_value(question)))
            help_text = question.get("help", "").strip()
            content = question["label"] + ("\n\n" + help_text if help_text else "")
            CONSOLE.print(Panel(content, title=f"{index + 1}/{len(questions)} · Setup"))
            prior = document.get("legacy", {}).get("answers", {}).get(key)
            if prior and key in document.get("review_required", []):
                CONSOLE.print("Previous answer: " + prior, markup=False)
            if question["kind"] == "timezone":
                value = _select_timezone(values[key] or None)
            elif question["kind"] == "text":
                value = _prompt_text(question["label"], default=values[key] or None, console=CONSOLE)
                if value.casefold() == "back":
                    value = None
            else:
                value = configure_options(question["label"], question["options"], values[key],
                                          multiple=question["kind"] == "multi")
            if value is None:
                if index == 0:
                    _save_draft(draft_path, document)
                    return 1
                index -= 1
                continue
            values[key] = value
            try:
                generation.validate_values([question], {key: value})
            except FeatureSetupError as error:
                CONSOLE.print(str(error), style="yellow", markup=False)
                continue
            document.get("editing", {}).pop(key, None)
            if key in document.get("review_required", []):
                document["review_required"].remove(key)
            _save_draft(draft_path, document)
            index += 1
        document.pop("review_required", None)
        bundle = generation.render_bundle(root, document)
        expected = {name: (output / name).read_text(encoding="utf-8") if (output / name).exists() else None
                    for name in bundle}
        CONSOLE.print(generation.preview(output, bundle) or "No generated changes.", markup=False)
        CONSOLE.print("Review custom instructions and provider destinations. Generation does not install.")
        if not apply or not confirm("Save answers and this generated package?", default=False):
            return 0 if not apply else 1
        tracking = document.get("generation", {})
        if output != root:
            tracking = tracking.get("destinations", {}).get(str(output), {})
        hashes = tracking.get("outputs", {})
        conflicts = [name for name, before in expected.items()
                     if before is not None and before != bundle[name]
                     and hashes.get(name) != generation.digest(before)]
        adopt = False
        if conflicts:
            CONSOLE.print("Manual/untracked generated files:\n" + "\n".join(conflicts), markup=False)
            adopt = confirm("Replace these files with the exact preview?", default=False)
            if not adopt:
                return 1
        generation.apply_bundle(output, answer_path, document, bundle, adopt=adopt, expected=expected, source_root=root)
        draft_path.unlink(missing_ok=True)
        CONSOLE.print(f"Generated {len(bundle)} files. Answers: {answer_path}", markup=False)
        return 0
    except (KeyboardInterrupt, EOFError):
        _save_draft(draft_path, document)
        CONSOLE.print("\nInterrupted. Active configuration unchanged; draft saved.")
        try:
            keep = confirm("Keep answers as a resumable draft?", default=True)
        except (KeyboardInterrupt, EOFError):
            keep = True
        if not keep:
            draft_path.unlink(missing_ok=True)
        return 1
