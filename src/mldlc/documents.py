"""G0 and G1: the intent and the spec are documents, checked for structure, consistency and unfinished work."""
import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from mldlc.project import Project
from mldlc.stages import CARD_SECTIONS, INTENT_SECTIONS, REENTRY, SPEC_SECTIONS


@dataclass
class Result:
    ok: bool
    problems: list[str] = field(default_factory=list)
    evidence: dict = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def sha256(path: Path) -> str | None:
    """Hash of a file, or None when it does not exist (so a deleted artifact reads as changed)."""
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


_FRONT = re.compile(r"\A---\n(.*?)\n---\n", re.S)
_COMMENT = re.compile(r"<!--.*?-->", re.S)
_BLOCK = re.compile(r"^```yaml (\S+)\n(.*?)^```", re.S | re.M)


def read_doc(path: Path) -> tuple[dict, str]:
    text = path.read_text()
    m = _FRONT.match(text)
    meta = (yaml.safe_load(m.group(1)) or {}) if m else {}
    return meta, (text[m.end():] if m else text)


def sections(body: str) -> dict[str, str]:
    out, current = {}, None
    for line in _COMMENT.sub("", body).splitlines():
        if line.startswith("## "):
            current = line[3:].strip(); out[current] = ""
        elif current is not None:
            out[current] += line + "\n"
    return out


def blocks(body: str) -> dict:
    """The machine-read ```yaml <name> blocks of a document."""
    return {name: yaml.safe_load(text) for name, text in _BLOCK.findall(body)}


def document_problems(path: Path, required: list[str], what: str) -> tuple[dict, str, list[str]]:
    if not path.exists():
        return {}, "", [f"{path.name} does not exist; run `mldlc init`"]
    meta, body = read_doc(path)
    problems = []
    secs = sections(body)
    for name in required:
        if name not in secs:
            problems.append(f"{what}: missing section '## {name}'")
        elif len(secs[name].strip()) < 20:
            problems.append(f"{what}: section '{name}' is empty or too short")
    if re.search(r"\bTODO\b", _COMMENT.sub("", path.read_text())):
        problems.append(f"{what}: unfilled TODO placeholders remain")
    return meta, body, problems


def check_intent(project: Project) -> Result:
    path = project.intent_path
    meta, _, problems = document_problems(path, INTENT_SECTIONS, "intent.md")
    if path.exists():
        if meta.get("project") != project.name:
            problems.append(f"intent.md: front matter project must be '{project.name}'")
        for key in ("owner", "intent_version", "created"):
            if not meta.get(key) or "TODO" in str(meta.get(key)):
                problems.append(f"intent.md: front matter '{key}' is missing")
    return Result(not problems, problems, {"intent_sha256": sha256(path)} if path.exists() else {})


def bounds_problems(where: str, bounds) -> list[str]:
    if not isinstance(bounds, dict) or not ({"min", "max"} & bounds.keys()):
        return [f"{where}: needs a numeric min and/or max"]
    return [f"{where}: {k} must be a number" for k in ("min", "max")
            if k in bounds and not isinstance(bounds[k], (int, float))]


def check_spec(project: Project) -> Result:
    path = project.spec_path
    meta, body, problems = document_problems(path, SPEC_SECTIONS, "spec.md")
    if not path.exists():
        return Result(False, problems)
    notes = []
    if meta.get("project") != project.name:
        problems.append(f"spec.md: front matter project must be '{project.name}'")
    for key in ("spec_version", "intent_version", "created"):
        if not meta.get(key):
            problems.append(f"spec.md: front matter '{key}' is missing")
    if project.intent_path.exists() and meta.get("intent_version") != read_doc(project.intent_path)[0].get("intent_version"):
        problems.append("spec.md: intent_version does not match intent.md; the spec was written for another intent")

    found = blocks(body)
    for name in ("model-inputs", "acceptance", "triggers"):
        if name not in found:
            problems.append(f"spec.md: missing the ```yaml {name} block")
    inputs = found.get("model-inputs") or {}
    problems += _inputs_vs_code(project, inputs, notes)

    metrics = (found.get("acceptance") or {}).get("metrics") or {}
    if "acceptance" in found and not metrics:
        problems.append("spec.md: acceptance needs a 'metrics' mapping")
    for name, bounds in metrics.items():
        if not project.metric_allowed(name):
            problems.append(f"spec.md: acceptance metric '{name}' is not in allowed_metrics ({project.allowed_metrics})")
        problems += bounds_problems(f"spec.md: acceptance.{name}", bounds)
    if project.baseline_metric and metrics:
        floor = (metrics.get(project.baseline_metric) or {}).get("min")
        if not (isinstance(floor, (int, float)) and floor > 0):
            problems.append(f"spec.md: acceptance must require beating the baseline: {project.baseline_metric} min > 0")

    triggers = found.get("triggers")
    if "triggers" in found and not (isinstance(triggers, list) and triggers):
        problems.append("spec.md: triggers must be a non-empty list")
    for t in triggers or []:
        label = f"spec.md: trigger '{t.get('name')}'"
        if not t.get("name") or not project.metric_allowed(str(t.get("metric"))):
            problems.append(f"{label}: needs a name and an allowed metric")
        if "compare_to" in t:
            if not project.metric_allowed(str(t["compare_to"])) or not isinstance(t.get("max_drop"), (int, float)):
                problems.append(f"{label}: compare_to needs an allowed metric and a numeric max_drop")
        else:
            problems += bounds_problems(label, t)
        if t.get("then") not in REENTRY:
            problems.append(f"{label}: 'then' must be one of {sorted(REENTRY)}")
    evidence = {"spec_sha256": sha256(path)}
    if project.intent_path.exists():
        evidence["intent_sha256"] = sha256(project.intent_path)
    return Result(not problems, problems, evidence, notes)


def _inputs_vs_code(project: Project, inputs: dict, notes: list[str]) -> list[str]:
    """Compare the spec's model inputs with the code through the optional hooks module."""
    hooks = project.hooks_module()
    if hooks is None or not hasattr(hooks, "model_inputs"):
        notes.append("no hooks.model_inputs(): the spec's inputs were not compared with the code")
        return []
    problems, code = [], hooks.model_inputs()
    if inputs:
        if inputs.get("target") != code["target"]:
            problems.append(f"spec.md: target '{inputs.get('target')}' differs from the code's '{code['target']}'")
        if set(inputs.get("features") or []) != set(code["features"]):
            problems.append(f"spec.md: model inputs {sorted(inputs.get('features') or [])} differ from the code's {sorted(code['features'])}")
    if hasattr(hooks, "serving_columns") and set(hooks.serving_columns()) != set(code["features"]):
        problems.append("hooks.serving_columns() must equal the model inputs, so columns known only after the event are rejected")
    return problems
