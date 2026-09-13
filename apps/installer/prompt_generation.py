"""Load the questionnaire and fill configured templates; never execute providers.

Deterministic invariants: stable choices, complete substitutions, contained output
paths, drift detection, and recoverable publication of one generated bundle.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from apps.installer.feature_setup import FeatureSetupError, write_batch

VERSION = 5
SLOT = re.compile(r"\$\{([a-zA-Z_][a-zA-Z0-9_]*)\}")
WHEN = re.compile(r"<!-- (when:([a-z0-9_.-]+)=([a-z0-9_,.-]+)|endwhen) -->")
IDENT = re.compile(r"^[a-z][a-z0-9_.-]*$")


@dataclass(frozen=True)
class Package:
    path: Path
    metadata: dict
    body: str


def template_root(root: Path) -> Path:
    return root / "apps" / "installer" / "templates"


def discover(root: Path) -> tuple[list[Package], list[dict]]:
    packages, questions = [], {}
    base = template_root(root)
    if not base.is_dir():
        raise FeatureSetupError(f"template_packages_missing:{base}")
    question_path = root / "apps" / "installer" / "questions.json"
    try:
        declared = json.loads(question_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise FeatureSetupError(f"questionnaire_unreadable:{question_path}") from error
    if not isinstance(declared, list) or not declared:
        raise FeatureSetupError("questionnaire_requires_nonempty_list")
    for question in declared:
        if not isinstance(question, dict):
            raise FeatureSetupError("questionnaire_question_invalid")
        key = question.get("id", "")
        if not isinstance(key, str) or not IDENT.fullmatch(key) or key in questions:
            raise FeatureSetupError(f"questionnaire_question_duplicate_or_invalid:{key}")
        if question.get("kind") not in {"text", "timezone", "select", "multi"}:
            raise FeatureSetupError(f"questionnaire_question_kind:{key}")
        options = question.get("options", [])
        if not isinstance(options, list) or any(not isinstance(o, dict) for o in options):
            raise FeatureSetupError(f"questionnaire_options_invalid:{key}")
        ids = [option.get("id", "") for option in options]
        if any(not isinstance(i, str) or not IDENT.fullmatch(i) for i in ids) or len(ids) != len(set(ids)):
            raise FeatureSetupError(f"questionnaire_option_id:{key}")
        if question["kind"] in {"select", "multi"} and not options:
            raise FeatureSetupError(f"questionnaire_options_missing:{key}")
        if question["kind"] in {"text", "timezone"} and options:
            raise FeatureSetupError(f"questionnaire_options_hidden_by_kind:{key}")
        if question["kind"] == "text" and key not in {"company.name", "company.description"}:
            raise FeatureSetupError(f"questionnaire_policy_requires_choices:{key}")
        for option in options:
            fields = option.get("fields", [])
            if not isinstance(fields, list) or any(not isinstance(f, dict) for f in fields):
                raise FeatureSetupError(f"questionnaire_fields_invalid:{key}")
            names = [field.get("id", "") for field in fields]
            if any(not isinstance(i, str) or not IDENT.fullmatch(i) for i in names) or len(names) != len(set(names)):
                raise FeatureSetupError(f"questionnaire_field_id:{key}")
        questions[key] = question
    for path in sorted(base.rglob("*.md")):
        if path.name == "README.md":
            continue
        if path.is_symlink():
            raise FeatureSetupError(f"template_symlink:{path}")
        text = path.read_text(encoding="utf-8")
        metadata, body = {}, text
        if text.startswith("---\n{"):
            try:
                header, body = text[4:].split("\n---\n", 1)
                metadata = json.loads(header)
            except (ValueError, json.JSONDecodeError) as error:
                raise FeatureSetupError(f"template_header_invalid:{path}") from error
        relative = path.relative_to(base).as_posix()
        metadata.setdefault("output", relative)
        packages.append(Package(path, metadata, body))
        if "questions" in metadata:
            raise FeatureSetupError(f"questions_belong_in_questions_json:{path}")
    for package in packages:
        for key in package.metadata.get("refs", []):
            if key not in questions:
                raise FeatureSetupError(f"template_reference_unknown:{key}")
    return packages, sorted(questions.values(), key=lambda q: (q.get("order", 100), q["id"]))


def load_document(path: Path) -> dict:
    if not path.exists():
        return {"schema_version": VERSION, "values": {}}
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise FeatureSetupError(f"setup_answers_unreadable:{path}") from error
    if not isinstance(result, dict) or result.get("schema_version") not in {4, VERSION}:
        raise FeatureSetupError("setup_answers_schema_invalid")
    return result


def question_list(root: Path) -> list[dict]:
    """Return the ordered questionnaire from questions.json."""
    return discover(root)[1]


def migrate(document: dict, questions: list[dict]) -> dict:
    """Keep v4 prose for human review; never infer new write authority."""
    if document["schema_version"] == VERSION:
        values = document.get("values", {})
        if not isinstance(values, dict):
            raise FeatureSetupError("setup_values_invalid")
        matching = values.get("organization.matching")
        if isinstance(matching, str):
            question = next(q for q in questions if q["id"] == "organization.matching")
            values["organization.matching"] = (
                {"selected": ["custom"], "inputs": {"custom": {"input": matching}}}
                if matching.strip() else default_value(question)
            )
        return document
    answers = document.get("answers", {})
    values = {q["id"]: answers[q["id"]] for q in questions
              if q["kind"] in {"text", "timezone"} and q["id"] in answers}
    if isinstance(answers.get("organization.matching"), str) and answers["organization.matching"].strip():
        values["organization.matching"] = {"selected": ["custom"], "inputs": {
            "custom": {"input": answers["organization.matching"]}}}
    return {"schema_version": VERSION, "values": values,
            "legacy": document, "review_required": [q["id"] for q in questions if q["id"] not in values]}


def default_value(question: dict):
    if question["kind"] in {"text", "timezone"}:
        return question.get("default", "")
    default = question.get("default", [] if question["kind"] == "multi" else "")
    selected = default if isinstance(default, list) else [default] if default else []
    return {"selected": selected, "inputs": {}}


def validate_field(value: str, field: dict, label: str) -> None:
    if not isinstance(value, str) or (field.get("required", True) and not value.strip()):
        raise FeatureSetupError(f"setup_input_required:{label}")
    rule = field.get("validation")
    if rule == "enum" and value not in field.get("allowed_values", []):
        raise FeatureSetupError(f"setup_choice_invalid:{label}:{value}")
    if rule == "provider_id" and not IDENT.fullmatch(value):
        raise FeatureSetupError(f"setup_provider_id_invalid:{label}:{value}")
    if value and rule == "sync_sections":
        sections = [section.strip() for section in value.split(",")]
        if any(section not in field.get("allowed_values", []) for section in sections):
            raise FeatureSetupError(f"setup_sync_section_invalid:{label}")
    if value and rule == "positive_integer" and (not value.isdecimal() or int(value) < 1):
        raise FeatureSetupError(f"setup_positive_integer_required:{label}")
    if value and rule == "url" and not value.startswith(("https://", "http://")):
        raise FeatureSetupError(f"setup_url_required:{label}")
    if value and rule == "memory_pattern":
        memory_pattern(value)


def memory_pattern(value: str) -> str:
    value = value.replace("<id>", "<unit-id>")
    if "<week>" not in value or "<unit-id>" not in value or not value.endswith(".md"):
        raise FeatureSetupError("memory_pattern_requires_week_unit_and_md")
    safe_relative(value)
    if "${" in value or "{{" in value:
        raise FeatureSetupError("memory_pattern_invalid_placeholder")
    return value


def validate_values(questions: list[dict], values: dict) -> None:
    if not isinstance(values, dict):
        raise FeatureSetupError("setup_values_invalid")
    known = {q["id"] for q in questions}
    if set(values) - known:
        raise FeatureSetupError("setup_unknown_answers:" + ",".join(sorted(set(values) - known)))
    for question in questions:
        key = question["id"]
        if key not in values:
            raise FeatureSetupError(f"setup_answer_missing:{key}")
        value = values[key]
        if question["kind"] in {"text", "timezone"}:
            validate_field(value, question, key)
            if question["kind"] == "timezone":
                try:
                    ZoneInfo(value)
                except (ZoneInfoNotFoundError, ValueError) as error:
                    raise FeatureSetupError("setup_timezone_invalid") from error
            continue
        if not isinstance(value, dict) or set(value) - {"selected", "inputs", "entries"}:
            raise FeatureSetupError(f"setup_selection_invalid:{key}")
        selected, inputs = value.get("selected"), value.get("inputs", {})
        options = {o["id"]: o for o in question["options"]}
        if not isinstance(selected, list) or not all(isinstance(i, str) for i in selected):
            raise FeatureSetupError(f"setup_selection_invalid:{key}")
        if len(selected) != len(set(selected)) or set(selected) - set(options):
            raise FeatureSetupError(f"setup_option_unknown_or_duplicate:{key}")
        if question["kind"] == "select" and len(selected) != 1:
            raise FeatureSetupError(f"setup_single_selection_required:{key}")
        if question.get("required", False) and not selected:
            raise FeatureSetupError(f"setup_selection_required:{key}")
        if not isinstance(inputs, dict) or set(inputs) - set(options):
            raise FeatureSetupError(f"setup_option_inputs_invalid:{key}")
        entries = value.get("entries", {})
        if (not isinstance(entries, dict) or set(entries) - set(options)
                or (entries and question["kind"] != "multi")
                or any(not isinstance(rows, list) for rows in entries.values())):
            raise FeatureSetupError(f"setup_entries_invalid:{key}")
        for option_id in selected:
            fields = options[option_id].get("fields", [])
            for supplied in [inputs.get(option_id, {}), *entries.get(option_id, [])]:
                if not isinstance(supplied, dict) or set(supplied) - {f["id"] for f in fields}:
                    raise FeatureSetupError(f"setup_field_unknown:{key}:{option_id}")
                for field in fields:
                    validate_field(supplied.get(field["id"], field.get("default", "")), field,
                                   f"{key}:{option_id}:{field['id']}")


def rendered_answers(questions: list[dict], values: dict) -> tuple[dict, dict, dict, dict]:
    answers, selections, requirements, targets = {}, {}, {}, {}
    effective = values
    for question in questions:
        key, value = question["id"], values[question["id"]]
        if isinstance(value, str):
            answers[key] = value
            continue
        selected = value["selected"]
        selections[key] = tuple(selected_text(effective[key])) or ("none",)
        rows, providers, bound = [], [], {}
        instances = [(option, index, supplied)
                     for option in question["options"] if option["id"] in selected
                     for index, supplied in enumerate([value.get("inputs", {}).get(option["id"], {}),
                                                       *value.get("entries", {}).get(option["id"], [])])]
        for option, index, supplied in instances:
            inputs = {f["id"]: supplied.get(f["id"], f.get("default", ""))
                      for f in option.get("fields", [])}
            render = option.get("render", option["label"])
            # Replace declared fields once; inserted prose is never parsed as a template.
            render = re.sub(r"\{([a-z][a-z0-9_]*)\}", lambda m: inputs.get(m[1], m[0]), render)
            rows.append(render)
            option_providers = option.get("providers", [])
            if option.get("providers_from"):
                option_providers = [inputs[option["providers_from"]]]
            if option.get("target_kind") == "record_rule":
                target_url = urlparse(inputs.get("target", ""))
                if target_url.scheme == "https" and target_url.hostname in {"notion.so", "www.notion.so", "app.notion.com"}:
                    option_providers = ["notion"]
            option_providers = [p for p in option_providers if p != "local"]
            propagation = selected_text(effective.get("automation.propagation", {"selected": ["none"]}))
            is_daily_route = key in {"daily.progress_route", "daily.documentation_route"}
            is_weekly_route = key.startswith("weekly.")
            active = not ((is_daily_route and not set(propagation) & {"daily", "both"}) or
                          (is_weekly_route and not set(propagation) & {"weekly", "both"}))
            if not active:
                continue
            providers.extend(option_providers)
            target = inputs.get("target", "")
            if target and (option.get("target_kind") != "record_rule" or target.startswith("https://")):
                for provider in option_providers:
                    suffix = f":{index + 1}" if index else ""
                    bound[f"{provider}:{option['id']}{suffix}"] = target
        answers[key] = "\n".join(rows)
        requirements[key] = tuple(dict.fromkeys(providers))
        targets[key] = bound
    return answers, selections, requirements, targets


def safe_relative(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or "\\" in value or not value or ":" in value:
        raise FeatureSetupError(f"generated_path_invalid:{value}")
    return path


def contained(root: Path, relative: str) -> Path:
    path = root / safe_relative(relative)
    if not path.resolve().is_relative_to(root.resolve()) or path.is_symlink():
        raise FeatureSetupError(f"generated_path_escape:{relative}")
    return path


def selected_text(value) -> list[str]:
    return value["selected"] if isinstance(value, dict) else [value]


def compact_table_rows(text: str) -> str:
    """Remove empty conditional slots between table rows, outside code fences."""
    rows, fence = [], ""
    for line in text.splitlines():
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if marker:
            if not fence:
                fence = marker[1]
            elif marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not marker[2].strip():
                fence = ""
        if not fence and line.strip().startswith("|") and line.strip().endswith("|"):
            index = len(rows)
            while index and not rows[index - 1].strip():
                index -= 1
            if index and rows[index - 1].strip().startswith("|") and rows[index - 1].strip().endswith("|"):
                del rows[index:]
        rows.append(line)
    return "\n".join(rows)


def conditional(text: str, values: dict) -> str:
    result, stack, last = [], [True], 0
    for match in WHEN.finditer(text):
        if stack[-1]:
            result.append(text[last:match.start()])
        if match[1] == "endwhen":
            if len(stack) == 1:
                raise FeatureSetupError("template_unbalanced_condition")
            stack.pop()
        else:
            if match[2] not in values:
                raise FeatureSetupError(f"template_condition_unknown:{match[2]}")
            stack.append(stack[-1] and bool(set(selected_text(values[match[2]])) & set(match[3].split(","))))
        last = match.end()
    if len(stack) != 1:
        raise FeatureSetupError("template_unbalanced_condition")
    result.append(text[last:])
    return "".join(result)


def substitute(text: str, context: dict) -> str:
    def replace(match):
        if match[1] not in context:
            raise FeatureSetupError(f"template_variable_unknown:{match[1]}")
        return str(context[match[1]])
    return SLOT.sub(replace, text)


def render_bundle(root: Path, document: dict) -> dict[str, str]:
    packages, questions = discover(root)
    document = migrate(document, questions)
    if document.get("schema_version") != VERSION or document.get("review_required"):
        raise FeatureSetupError("setup_migration_review_required:run setup.py features")
    values = document.get("values", {})
    validate_values(questions, values)
    meetings = selected_text(values.get("daily.meetings", {"selected": []}))
    if "inside_work" in meetings and not selected_text(values.get("daily.work", {"selected": []})):
        raise FeatureSetupError("inside_work_meetings_require_work_source")
    answers, _, _, _ = rendered_answers(questions, values)
    context = {"answer__" + k.replace(".", "_"): v for k, v in answers.items()}
    for package in packages:
        for key, variants in package.metadata.get("variants", {}).items():
            choice = selected_text(values[key])
            if len(choice) != 1 or choice[0] not in variants:
                raise FeatureSetupError(f"template_variant_missing:{key}")
            for name, value in variants[choice[0]].items():
                if name in context and context[name] != value:
                    raise FeatureSetupError(f"template_variant_conflict:{name}")
                context[name] = value
    unit = context.get("unit_key", "project")
    default_memory = f"weeks/<week>/{unit}-memory/{unit}--<unit-id>.md"
    memory_value = values.get("daily.existing_memory", {})
    pattern = default_memory
    if isinstance(memory_value, dict):
        for option in memory_value["selected"]:
            fields = memory_value.get("inputs", {}).get(option, {})
            pattern = fields.get("pattern", fields.get("input", "")) or pattern
    pattern = memory_pattern(pattern)
    context.update(memory_current=pattern, memory_next=pattern.replace("<week>", "<next-week>"),
                   memory_default=default_memory, memory_pattern=pattern)
    context.update(memory_directory=str(Path(pattern).parent),
                   next_memory_directory=str(Path(pattern.replace("<week>", "<next-week>")).parent))
    bundle = {}
    for package in packages:
        condition = package.metadata.get("when")
        if condition and not set(selected_text(values[condition["question"]])) & set(condition["options"]):
            continue
        output = substitute(package.metadata["output"], context)
        safe_relative(output)
        if output != "workspace.hermes.md" and not output.startswith(("automations/", "skills/pm-daily/", "skills/pm-weekly/", "templates/")):
            raise FeatureSetupError(f"generated_output_not_allowed:{output}")
        body = compact_table_rows(substitute(conditional(package.body, values), context)).lstrip("\n")
        if "runtime" in package.metadata:
            runtime = {substitute(k, context): substitute(v, context) if isinstance(v, str) else v
                       for k, v in package.metadata["runtime"].items()}
            header = "\n".join(k + ": " + (v if k == "status" and v in {"draft", "approved"}
                                             else json.dumps(v, ensure_ascii=False)) for k, v in runtime.items())
            body = "---\n" + header + "\n---\n" + body
        if output in bundle:
            raise FeatureSetupError(f"generated_output_duplicate:{output}")
        if "<!-- when:" in body or "<!-- endwhen" in body or "proposed-template" in body:
            raise FeatureSetupError(f"generated_unresolved_directive:{output}")
        bundle[output] = body.rstrip() + "\n"
    for key in ("automations/daily-operating-update.md", "automations/weekly-operating-review.md",
                "skills/pm-daily/SKILL.md", "skills/pm-weekly/SKILL.md", "workspace.hermes.md"):
        if key not in bundle:
            raise FeatureSetupError(f"generated_primary_missing:{key}")
    return bundle


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def preview(root: Path, bundle: dict) -> str:
    rows = []
    for relative, after in bundle.items():
        path = contained(root, relative)
        before = path.read_text(encoding="utf-8") if path.exists() else ""
        rows.extend(difflib.unified_diff(before.splitlines(), after.splitlines(), fromfile=relative, tofile=relative, lineterm=""))
    return "\n".join(rows)


def apply_bundle(root: Path, config_path: Path, document: dict, bundle: dict, *, adopt=False, expected=None, source_root: Path | None = None) -> None:
    source_root = (source_root or root).resolve()
    root = root.resolve()
    external = root != source_root
    destination_key = str(root)
    generation = document.get("generation", {})
    state = generation.get("destinations", {}).get(destination_key, {}) if external else generation
    hashes = dict(state.get("outputs", {}))
    state_root = contained(root, ".generation") if external else config_path.parent.resolve()
    marker = contained(state_root, "generation-incomplete")
    if marker.exists():
        try:
            pending = json.loads(marker.read_text(encoding="utf-8"))
            hashes.update(pending.get("retire", {}))
        except ValueError as error:
            raise FeatureSetupError("generation_recovery_marker_invalid") from error
    files = {}
    for relative, content in bundle.items():
        path = contained(root, relative)
        before = path.read_text(encoding="utf-8") if path.exists() else None
        if expected is not None and before != expected.get(relative):
            raise FeatureSetupError(f"generated_concurrent_edit:{relative}")
        if before is not None and before != content:
            if not adopt and hashes.get(relative) != digest(before):
                raise FeatureSetupError(f"generated_manual_edit:{relative}:review diff and explicitly adopt")
        if before != content:
            files[path] = content
            if before is not None:
                backup = contained(state_root, f"generation-backups/{digest(before)}/{relative}")
                files[backup] = before
    retired = []
    retirement_hashes = {}
    for relative, old_hash in hashes.items():
        if relative in bundle:
            continue
        path = contained(root, relative)
        if not path.is_file():
            continue
        before = path.read_text(encoding="utf-8")
        if digest(before) != old_hash:
            raise FeatureSetupError(f"obsolete_generated_file_modified:{relative}")
        files[contained(state_root, f"generation-backups/{digest(before)}/{relative}")] = before
        retired.append(path)
        retirement_hashes[relative] = old_hash
    packages, _ = discover(source_root)
    saved = dict(document)
    current = {"outputs": {k: digest(v) for k, v in bundle.items()},
               "templates": {str(p.path.relative_to(template_root(source_root))): digest(p.path.read_text()) for p in packages}}
    current["questionnaire"] = digest((source_root / "apps/installer/questions.json").read_text(encoding="utf-8"))
    saved["generation"] = dict(generation)
    if external:
        saved["generation"]["destinations"] = {**generation.get("destinations", {}), destination_key: current}
    else:
        saved["generation"].update(current)
    files[config_path] = json.dumps(saved, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    # Marker survives process death; installation can reject interrupted generation.
    write_batch({marker: json.dumps({"retire": retirement_hashes}) + "\n"})
    write_batch(files)
    for path in retired:
        path.unlink()
    marker.unlink()


def generate(root: Path, config_path: Path | None = None, *, apply=False, adopt=False, output_root: Path | None = None) -> dict:
    root = root.resolve()
    config_path = config_path or root / "config" / "setup-answers.json"
    document = load_document(config_path)
    bundle = render_bundle(root, document)
    if apply:
        apply_bundle(output_root or root, config_path, document, bundle, adopt=adopt, source_root=root)
    return bundle
