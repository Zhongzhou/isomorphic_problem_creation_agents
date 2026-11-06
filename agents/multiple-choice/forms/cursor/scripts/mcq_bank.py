"""Parse a multiple-choice input file and keep the scene, tally, and item checks."""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write(
        "PyYAML is required. Run this skill with the repo venv:\n"
        ".venv/Scripts/python.exe -m pip install -r "
        ".cursor/skills/multiple-choice-questions/requirements.txt\n"
    )
    sys.exit(1)


MAX_UPDATES = 5
DEFAULT_TEMPLATE = "Templates/Problem-bank-template-mathjax.yaml"
HEADER = (
    "# Review file for the multiple-choice question workflow.\n"
    "# scenes with status kept are the scenes the user selected.\n"
    "# scenes with status backup are not drawn and do not become items.\n"
    "# The user chooses how many scenes to keep. This file does not set that number.\n"
)


def configure_stdio() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


def fail(message: str, code: int = 1) -> None:
    sys.stderr.write(message.rstrip() + "\n")
    raise SystemExit(code)


def emit(payload: dict, code: int = 0) -> None:
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    raise SystemExit(code)


def load_yaml(path: Path):
    if not path.is_file():
        fail(f"File not found: {path}")
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def save(path: Path, data: dict) -> None:
    body = yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=1000)
    path.write_text(HEADER + body, encoding="utf-8")


def text_of(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return str(value).strip()


def fold(value: str) -> str:
    return " ".join(value.split()).casefold()


def as_bool(value, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    folded = fold(str(value))
    if folded in {"yes", "true", "y"}:
        return True
    if folded in {"no", "false", "n"}:
        return False
    fail(f"Expected yes or no, got {value!r}.")
    return default


def as_positive_int(value, label: str):
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return None, f"{label} must be a positive integer."
    return value, ""


def section_map(data: dict) -> dict:
    return {fold(str(key)): value for key, value in data.items()}


def merge_dicts(items) -> dict:
    merged = {}
    if isinstance(items, dict):
        return dict(items)
    if not isinstance(items, list):
        return merged
    for item in items:
        if isinstance(item, dict):
            merged.update(item)
    return merged


def parse_named_list(value, prefix: str) -> list[dict]:
    found = []
    items = value if isinstance(value, list) else ([value] if isinstance(value, dict) else [])
    for item in items:
        if isinstance(item, dict):
            for key, raw in item.items():
                if fold(str(key)).startswith(prefix):
                    found.append({"id": str(key).strip(), "text": text_of(raw)})
        elif isinstance(item, str) and item.strip():
            found.append({"id": f"{prefix} {len(found) + 1}", "text": item.strip()})
    return found


def parse_scenario(name: str, value) -> dict:
    fields = merge_dicts(value)
    variations = []
    for key, raw in fields.items():
        if fold(str(key)).startswith("variation"):
            variations.append({"id": str(key).strip(), "text": text_of(raw)})
    return {
        "id": name,
        "description": text_of(fields.get("description")),
        "specifications": text_of(fields.get("specifications")),
        "variations": variations,
        "scenes": [],
        "rejected": [],
    }


def parse_scenario_section(value) -> tuple[list[dict], list[dict]]:
    common = []
    scenarios = []
    items = value if isinstance(value, list) else ([value] if isinstance(value, dict) else [])
    for item in items:
        if not isinstance(item, dict):
            continue
        for key, raw in item.items():
            folded = fold(str(key))
            if folded == "common variations":
                common = parse_named_list(raw, "variation")
            elif folded.startswith("scenario"):
                scenarios.append(parse_scenario(str(key).strip(), raw))
    return common, scenarios


def parse_choices(value) -> tuple[list[dict], str, str]:
    choices = []
    variations = ""
    correct = ""
    items = value if isinstance(value, list) else ([value] if isinstance(value, dict) else [])
    for item in items:
        if not isinstance(item, dict):
            continue
        for key, raw in item.items():
            folded = fold(str(key))
            if folded.startswith("possible answer"):
                choices.append({"id": str(key).strip(), "role": "possible", "text": text_of(raw)})
            elif folded.startswith("distractor"):
                choices.append({"id": str(key).strip(), "role": "distractor", "text": text_of(raw)})
            elif folded == "choice variations":
                variations = text_of(raw)
            elif folded == "correct answer":
                correct = text_of(raw)
    return choices, variations, correct


def parse_process(value) -> dict:
    merged = merge_dicts(value)
    export = merged.get("export")
    export = export if isinstance(export, dict) else {}
    export_map = {fold(str(key)): raw for key, raw in export.items()}
    candidates, candidates_error = as_positive_int(
        merged.get("candidates scenes per scenario"), "candidates scenes per scenario"
    )
    samples, samples_error = as_positive_int(
        merged.get("samples per scenario"), "samples per scenario"
    )
    return {
        "candidates_per_scenario": candidates,
        "samples_per_scenario": samples,
        "candidates_error": candidates_error,
        "samples_error": samples_error,
        "automatic_minor_fixes": as_bool(merged.get("automatic minor fixes"), True),
        "export_yaml": as_bool(export_map.get("convert markdown to yaml"), False),
        "yaml_template": text_of(export_map.get("yaml template")),
    }


def parse_input(path: Path) -> dict:
    data = load_yaml(path)
    if not isinstance(data, dict):
        fail(f"Input YAML must be a mapping: {path}")
    sections = section_map(data)
    question = merge_dicts(sections.get("question"))
    common, scenarios = parse_scenario_section(sections.get("scenario and variations"))
    diagram = merge_dicts(sections.get("diagram"))
    choices, choice_variations, correct_answer = parse_choices(sections.get("choice items"))
    process = parse_process(sections.get("creation process"))
    need_diagram = as_bool(diagram.get("need diagram"), False)
    return {
        "source_input": str(path),
        "question": {
            "situation": text_of(question.get("situation")),
            "given": text_of(question.get("given")),
            "ask": text_of(question.get("ask")),
        },
        "common_variations": common,
        "scenarios": scenarios,
        "need_diagram": need_diagram,
        "diagram_specification": text_of(diagram.get("diagram specification")),
        "choices": choices,
        "choice_variations": choice_variations,
        "correct_answer": correct_answer,
        "candidates_per_scenario": process["candidates_per_scenario"],
        "samples_per_scenario": process["samples_per_scenario"],
        "candidates_error": process["candidates_error"],
        "samples_error": process["samples_error"],
        "automatic_minor_fixes": process["automatic_minor_fixes"],
        "export_yaml": process["export_yaml"],
        "yaml_template": process["yaml_template"] or DEFAULT_TEMPLATE,
        "yaml_template_blank": not bool(process["yaml_template"]),
        "variation_axes": None,
        "update_count": 0,
    }


def validate_model(model: dict) -> dict:
    errors = []
    warnings = []
    question = model["question"]
    for field in ("situation", "given", "ask"):
        if not question[field]:
            errors.append(f"Question.{field} is empty.")
    if not model["scenarios"]:
        errors.append("No scenarios were found under scenario and variations.")
    for scenario in model["scenarios"]:
        if not scenario["description"]:
            errors.append(f"{scenario['id']} is missing a description.")
    possible = [item for item in model["choices"] if item["role"] == "possible"]
    distractors = [item for item in model["choices"] if item["role"] == "distractor"]
    if not possible:
        errors.append("Choice Items needs at least one possible answer.")
    if not distractors:
        errors.append("Choice Items needs at least one distractor.")
    for item in model["choices"]:
        if not item["text"]:
            errors.append(f"{item['id']} is empty.")
    if not model["choice_variations"]:
        warnings.append("choice variations is empty. Say how the choice symbols change across scenarios.")
    if not model["correct_answer"]:
        warnings.append(
            "correct answer is empty. Propose which possible answer is correct for each variation and wait for confirmation."
        )
    if model["candidates_error"]:
        errors.append(model["candidates_error"])
    if model["samples_error"]:
        errors.append(model["samples_error"])
    if model["need_diagram"] and not model["diagram_specification"]:
        errors.append("need diagram is Yes, and diagram specification is empty.")
    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "correct_answer_blank": not bool(model["correct_answer"]),
        "scenarios": [scenario["id"] for scenario in model["scenarios"]],
        "possible_answers": len(possible),
        "distractors": len(distractors),
        "candidates_per_scenario": model["candidates_per_scenario"],
        "samples_per_scenario": model["samples_per_scenario"],
        "need_diagram": model["need_diagram"],
        "export_yaml": model["export_yaml"],
        "yaml_template": model["yaml_template"] if model["export_yaml"] else "",
    }


def sidecar_from_model(model: dict) -> dict:
    stored = dict(model)
    stored.pop("candidates_error", None)
    stored.pop("samples_error", None)
    stored.pop("yaml_template_blank", None)
    return stored


def load_sidecar(path: Path) -> dict:
    data = load_yaml(path)
    if not isinstance(data, dict):
        fail(f"Bank file must be a mapping: {path}")
    for key in ("scenarios", "choices", "update_count", "candidates_per_scenario"):
        if key not in data:
            fail(f"Bank file is missing {key}: {path}")
    return data


def scenario_by_id(data: dict, scenario_id: str) -> dict:
    for scenario in data["scenarios"]:
        if scenario["id"] == scenario_id:
            return scenario
    fail(f"No scenario named {scenario_id!r}.")
    return {}


def pending_scenes(scenario: dict) -> list[dict]:
    return [scene for scene in scenario["scenes"] if scene.get("status") == "pending"]


def kept_scenes(scenario: dict) -> list[tuple[int, dict]]:
    return [
        (index, scene)
        for index, scene in enumerate(scenario["scenes"])
        if scene.get("status") == "kept"
    ]


def ready_for_selection(data: dict) -> bool:
    return all(pending_scenes(scenario) for scenario in data["scenarios"])


def snapshot(data: dict, path: Path) -> dict:
    rounds_exceeded = int(data["update_count"]) > MAX_UPDATES
    ready = ready_for_selection(data)
    scenarios = []
    for scenario in data["scenarios"]:
        pending = pending_scenes(scenario)
        target = int(data["candidates_per_scenario"])
        needed = target if not pending else 0
        scenarios.append(
            {
                "id": scenario["id"],
                "description": scenario["description"],
                "specifications": scenario["specifications"],
                "variations": scenario["variations"],
                "pending": len(pending),
                "needed": needed,
                "pending_texts": [scene["text"] for scene in pending],
                "scenes": [
                    {"index": index, "text": scene["text"], "status": scene["status"]}
                    for index, scene in enumerate(scenario["scenes"])
                ],
                "rejected": scenario["rejected"],
            }
        )
    blocked = rounds_exceeded and any(item["pending"] == 0 for item in scenarios)
    return {
        "file": str(path),
        "update_count": int(data["update_count"]),
        "candidates_per_scenario": int(data["candidates_per_scenario"]),
        "samples_per_scenario": int(data["samples_per_scenario"]),
        "ready_for_selection": ready,
        "rounds_exceeded": rounds_exceeded,
        "stop": blocked and not ready,
        "correct_answer": data.get("correct_answer", ""),
        "choice_variations": data.get("choice_variations", ""),
        "choices": data.get("choices", []),
        "question": data.get("question", {}),
        "need_diagram": bool(data.get("need_diagram")),
        "automatic_minor_fixes": bool(data.get("automatic_minor_fixes", True)),
        "export_yaml": bool(data.get("export_yaml")),
        "yaml_template": data.get("yaml_template") or DEFAULT_TEMPLATE,
        "variation_axes": data.get("variation_axes"),
        "scenarios": scenarios,
    }


def default_sidecar(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}.mcq.yaml")


def cmd_validate(input_path: Path) -> None:
    model = parse_input(input_path)
    emit(validate_model(model), 0 if validate_model(model)["ok"] else 1)


def cmd_init(input_path: Path, force: bool) -> None:
    destination = default_sidecar(input_path)
    if destination.exists() and not force:
        fail(f"Bank file already exists: {destination}. Ask before using --force.")
    model = parse_input(input_path)
    report = validate_model(model)
    if not report["ok"]:
        emit(report, 1)
    save(destination, sidecar_from_model(model))
    emit(snapshot(load_sidecar(destination), destination))


def cmd_status(path: Path) -> None:
    emit(snapshot(load_sidecar(path), path))


def cmd_receive(path: Path) -> None:
    data = load_sidecar(path)
    data["update_count"] = int(data["update_count"]) + 1
    save(path, data)
    report = snapshot(data, path)
    emit(report, 2 if report["stop"] else 0)


def cmd_add(path: Path, scenario_id: str, texts: list[str]) -> None:
    data = load_sidecar(path)
    scenario = scenario_by_id(data, scenario_id)
    known = {fold(scene["text"]) for scene in scenario["scenes"]}
    known.update(fold(item["text"]) for item in scenario["rejected"] if item.get("text"))
    added = []
    for text in texts:
        cleaned = " ".join(text.split())
        if not cleaned:
            fail("A scene text is empty.")
        if fold(cleaned) in known:
            fail(f"Scene already exists for {scenario_id}: {cleaned}")
        scene = {"text": cleaned, "status": "pending"}
        scenario["scenes"].append(scene)
        known.add(fold(cleaned))
        added.append(cleaned)
    save(path, data)
    report = snapshot(data, path)
    report["added"] = added
    emit(report)


def cmd_remove(path: Path, scenario_id: str, indexes: list[int], reasons: list[str]) -> None:
    data = load_sidecar(path)
    if not indexes and not reasons:
        emit(snapshot(data, path))
    if len(indexes) != len(reasons):
        fail("Each --index needs one --reason.")
    scenario = scenario_by_id(data, scenario_id)
    pending = pending_scenes(scenario)
    for index in indexes:
        if index < 0 or index >= len(pending):
            fail(f"Pending index {index} is outside {scenario_id}.")
    # Remove from the end so earlier pending indexes stay stable.
    for index, reason in sorted(zip(indexes, reasons), reverse=True):
        scene = pending[index]
        if not reason.strip():
            fail("A removal needs a reason.")
        scenario["scenes"].remove(scene)
        scenario["rejected"].append({"text": scene["text"], "reason": reason.strip()})
    save(path, data)
    emit(snapshot(data, path))


def load_json(path: Path):
    if not path.is_file():
        fail(f"JSON file not found: {path}")
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def cmd_set_variations(path: Path, json_path: Path) -> None:
    data = load_sidecar(path)
    raw = load_json(json_path)
    if not isinstance(raw, dict):
        fail("Variation JSON must be an object.")
    common = normalize_axes(raw.get("common", []), "common")
    by_scenario = raw.get("by_scenario", {})
    if not isinstance(by_scenario, dict):
        fail("by_scenario must be an object.")
    normalized = {}
    for scenario in data["scenarios"]:
        if scenario["id"] not in by_scenario:
            fail(f"by_scenario is missing {scenario['id']}.")
        normalized[scenario["id"]] = normalize_axes(by_scenario[scenario["id"]], scenario["id"])
    extra = set(by_scenario) - {scenario["id"] for scenario in data["scenarios"]}
    if extra:
        fail(f"Unknown scenarios in by_scenario: {', '.join(sorted(extra))}.")
    data["variation_axes"] = {"common": common, "by_scenario": normalized}
    save(path, data)
    emit(snapshot(data, path))


def normalize_axes(raw, label: str) -> list[dict]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        fail(f"{label} variation axes must be a list.")
    axes = []
    seen = set()
    for item in raw:
        if not isinstance(item, dict):
            fail(f"{label} has an axis that is not an object.")
        axis_id = text_of(item.get("id"))
        values = item.get("values")
        if not axis_id:
            fail(f"{label} has an axis without an id.")
        if axis_id in seen:
            fail(f"{label} repeats axis {axis_id}.")
        if not isinstance(values, list) or not values or not all(text_of(value) for value in values):
            fail(f"{label} axis {axis_id} needs a non-empty list of values.")
        if "changes_drawing" not in item or not isinstance(item["changes_drawing"], bool):
            fail(f"{label} axis {axis_id} needs changes_drawing true or false.")
        seen.add(axis_id)
        axes.append(
            {
                "id": axis_id,
                "values": [text_of(value) for value in values],
                "changes_drawing": item["changes_drawing"],
            }
        )
    return axes


def require_axes(data: dict) -> dict:
    axes = data.get("variation_axes")
    if not isinstance(axes, dict):
        fail("Variation axes are not set. Confirm the value lists, then run set-variations.", 2)
    return axes


def axes_for(data: dict, scenario_id: str) -> list[dict]:
    axes = require_axes(data)
    return list(axes["common"]) + list(axes["by_scenario"][scenario_id])


def combinations(axes: list[dict]) -> list[dict]:
    if not axes:
        return [{}]
    ids = [axis["id"] for axis in axes]
    pools = [axis["values"] for axis in axes]
    return [dict(zip(ids, combo)) for combo in itertools.product(*pools)]


def drawing_values(axes: list[dict], combo: dict) -> dict:
    return {axis["id"]: combo[axis["id"]] for axis in axes if axis["changes_drawing"]}


def cmd_tally(path: Path) -> None:
    data = load_sidecar(path)
    if any(scene.get("status") == "pending" for scenario in data["scenarios"] for scene in scenario["scenes"]):
        fail("Select kept and backup scenes before computing the tally.", 2)
    rows = []
    total = 0
    for scenario in data["scenarios"]:
        kept = kept_scenes(scenario)
        combos = combinations(axes_for(data, scenario["id"]))
        count = len(kept) * len(combos)
        total += count
        rows.append(
            {
                "scenario": scenario["id"],
                "kept_scenes": len(kept),
                "combinations_per_scene": len(combos),
                "items": count,
                "combinations": combos,
            }
        )
    emit({"file": str(path), "items": total, "scenarios": rows})


def cmd_figures(path: Path) -> None:
    data = load_sidecar(path)
    if not data.get("need_diagram"):
        emit({"file": str(path), "needed": False, "figures": []})
    figures = []
    for scenario in data["scenarios"]:
        axes = axes_for(data, scenario["id"])
        drawing_axes = [axis for axis in axes if axis["changes_drawing"]]
        for index, _scene in kept_scenes(scenario):
            for combo in combinations(drawing_axes):
                figures.append(
                    {
                        "scenario": scenario["id"],
                        "scene_index": index,
                        "drawing": combo,
                    }
                )
    emit({"file": str(path), "needed": True, "figures": figures})


def cmd_sample_slots(path: Path) -> None:
    data = load_sidecar(path)
    slots = []
    per_scenario = int(data["samples_per_scenario"])
    for scenario in data["scenarios"]:
        kept = kept_scenes(scenario)
        if not kept:
            continue
        scene_index = kept[0][0]
        combos = combinations(axes_for(data, scenario["id"]))
        for combo in combos[:per_scenario]:
            slots.append(
                {
                    "scenario": scenario["id"],
                    "scene_index": scene_index,
                    "values": combo,
                }
            )
    emit({"file": str(path), "samples": slots})


def expected_items(data: dict) -> list[dict]:
    expected = []
    for scenario in data["scenarios"]:
        axes = axes_for(data, scenario["id"])
        for index, _scene in kept_scenes(scenario):
            for combo in combinations(axes):
                expected.append(
                    {
                        "scenario": scenario["id"],
                        "scene_index": index,
                        "values": combo,
                        "drawing": drawing_values(axes, combo),
                    }
                )
    return expected


def item_key(item: dict) -> tuple:
    values = item.get("values")
    if not isinstance(values, dict):
        fail("Each item needs a values object.")
    return (
        item.get("scenario"),
        item.get("scene_index"),
        tuple(sorted((str(key), str(value)) for key, value in values.items())),
    )


def cmd_check_items(path: Path, json_path: Path) -> None:
    data = load_sidecar(path)
    raw = load_json(json_path)
    items = raw.get("items") if isinstance(raw, dict) else None
    if not isinstance(items, list):
        fail("Item JSON must be an object with an items list.")
    expected = expected_items(data)
    possible = [choice for choice in data["choices"] if choice["role"] == "possible"]
    choice_count = len(data["choices"])
    errors = []
    seen = {}
    backup_indexes = {
        scenario["id"]: {
            index
            for index, scene in enumerate(scenario["scenes"])
            if scene.get("status") == "backup"
        }
        for scenario in data["scenarios"]
    }
    for position, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"Item {position} is not an object.")
            continue
        key = item_key(item)
        if key in seen:
            errors.append(f"Item {position} repeats {key[0]} scene {key[1]} {dict(key[2])}.")
        seen[key] = position
        if item.get("scenario") in backup_indexes and item.get("scene_index") in backup_indexes[item["scenario"]]:
            errors.append(f"Item {position} uses a backup scene.")
        choices = item.get("choices")
        if not isinstance(choices, list) or len(choices) != choice_count:
            errors.append(f"Item {position} must have {choice_count} choices in the input order.")
        correct = item.get("correct_index")
        if isinstance(correct, bool) or not isinstance(correct, int) or not 0 <= correct < len(possible):
            errors.append(f"Item {position} correct_index must point at a possible answer, not a distractor.")
        symbols = item.get("choice_symbols")
        defined = item.get("defines_symbols")
        if not isinstance(symbols, list) or not isinstance(defined, list):
            errors.append(f"Item {position} needs choice_symbols and defines_symbols lists.")
        elif any(symbol not in defined for symbol in symbols):
            missing = [symbol for symbol in symbols if symbol not in defined]
            errors.append(f"Item {position} does not define {', '.join(missing)}.")
        if data.get("need_diagram") and not text_of(item.get("figure")):
            errors.append(f"Item {position} is missing a figure.")
    expected_keys = {
        (item["scenario"], item["scene_index"], tuple(sorted(item["values"].items())))
        for item in expected
    }
    missing = [key for key in expected_keys if key not in seen]
    extra = [key for key in seen if key not in expected_keys]
    for key in missing:
        errors.append(f"Missing item for {key[0]} scene {key[1]} {dict(key[2])}.")
    for key in extra:
        errors.append(f"Unexpected item for {key[0]} scene {key[1]} {dict(key[2])}.")
    if data.get("need_diagram"):
        figures_for = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            drawing = drawing_values(axes_for(data, item.get("scenario", "")), item.get("values") or {})
            figure_key = (item.get("scenario"), item.get("scene_index"), tuple(sorted(drawing.items())))
            figures_for.setdefault(figure_key, set()).add(text_of(item.get("figure")))
        for figure_key, names in figures_for.items():
            if len(names) > 1:
                errors.append(f"Items that share a figure use different files: {figure_key}.")
    emit(
        {
            "file": str(path),
            "ok": not errors,
            "expected": len(expected),
            "found": len(items),
            "errors": errors,
        },
        0 if not errors else 1,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Multiple-choice bank sidecar")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate")
    validate.add_argument("input")

    init = sub.add_parser("init")
    init.add_argument("--input", required=True)
    init.add_argument("--force", action="store_true")

    for name in ("status", "receive", "tally", "figures", "sample-slots"):
        command = sub.add_parser(name)
        command.add_argument("--file", required=True)

    add = sub.add_parser("add")
    add.add_argument("--file", required=True)
    add.add_argument("--scenario", required=True)
    add.add_argument("--text", action="append", required=True)

    remove = sub.add_parser("remove")
    remove.add_argument("--file", required=True)
    remove.add_argument("--scenario", required=True)
    remove.add_argument("--index", action="append", type=int)
    remove.add_argument("--reason", action="append")

    for name in ("set-variations", "select", "check-items"):
        command = sub.add_parser(name)
        command.add_argument("--file", required=True)
        command.add_argument("--json-file", required=True)
    return parser


def main(argv: list[str] | None = None) -> None:
    configure_stdio()
    args = build_parser().parse_args(argv)
    if args.command == "validate":
        cmd_validate(Path(args.input))
    elif args.command == "init":
        cmd_init(Path(args.input), args.force)
    elif args.command == "status":
        cmd_status(Path(args.file))
    elif args.command == "receive":
        cmd_receive(Path(args.file))
    elif args.command == "add":
        cmd_add(Path(args.file), args.scenario, args.text)
    elif args.command == "remove":
        indexes = args.index or []
        reasons = args.reason or []
        cmd_remove(Path(args.file), args.scenario, indexes, reasons)
    elif args.command == "set-variations":
        cmd_set_variations(Path(args.file), Path(args.json_file))
    elif args.command == "select":
        cmd_select(Path(args.file), Path(args.json_file))
    elif args.command == "tally":
        cmd_tally(Path(args.file))
    elif args.command == "figures":
        cmd_figures(Path(args.file))
    elif args.command == "sample-slots":
        cmd_sample_slots(Path(args.file))
    elif args.command == "check-items":
        cmd_check_items(Path(args.file), Path(args.json_file))
    else:
        fail(f"Unknown command {args.command}.")


def cmd_select(path: Path, json_path: Path) -> None:
    data = load_sidecar(path)
    raw = load_json(json_path)
    if not isinstance(raw, dict):
        fail("Selection JSON must be an object.")
    for scenario in data["scenarios"]:
        choice = raw.get(scenario["id"])
        if not isinstance(choice, dict):
            fail(f"Selection is missing {scenario['id']}.")
        keep = choice.get("keep", [])
        backup = choice.get("backup", [])
        if not isinstance(keep, list) or not isinstance(backup, list):
            fail(f"{scenario['id']} keep and backup must be lists of scene indexes.")
        indexes = list(range(len(scenario["scenes"])))
        chosen = list(keep) + list(backup)
        if sorted(chosen) != indexes:
            fail(
                f"{scenario['id']} must place every scene index in keep or backup. "
                "The user decides how many to keep."
            )
        for index in keep:
            scenario["scenes"][index]["status"] = "kept"
        for index in backup:
            scenario["scenes"][index]["status"] = "backup"
    unknown = set(raw) - {scenario["id"] for scenario in data["scenarios"]}
    if unknown:
        fail(f"Unknown scenarios in selection: {', '.join(sorted(unknown))}.")
    save(path, data)
    emit(snapshot(data, path))


if __name__ == "__main__":
    main()
