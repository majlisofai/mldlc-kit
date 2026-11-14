"""G0 and G1: the documents, and how the spec is tied to the code."""
import pytest

from conftest import FEATURES, intent_text, spec_text, write
from mldlc import documents, scaffold, stages


def test_templates_contain_every_required_section():
    for name, required in (("intent.md", stages.INTENT_SECTIONS), ("spec.md", stages.SPEC_SECTIONS), ("model_card.md", stages.CARD_SECTIONS)):
        text = (scaffold.TEMPLATES / name).read_text()
        for section in required:
            assert f"## {section}\n" in text, (name, section)
    # init fills {project}, {date} and {baseline_metric}; the rendered file is what has to parse
    rendered = scaffold._fill((scaffold.TEMPLATES / "spec.md").read_text(), "demo")
    assert {"model-inputs", "acceptance", "triggers"} <= set(documents.blocks(rendered))


def test_fresh_templates_fail_until_filled(tmp_path):
    scaffold.init_project(tmp_path / "p", name="p", hooks=True)
    from mldlc.project import Project
    proj = Project.load(tmp_path / "p")
    assert any("TODO" in p for p in documents.check_intent(proj).problems)
    assert any("TODO" in p for p in documents.check_spec(proj).problems)


def test_a_complete_intent_and_spec_pass(project):
    write(project, "intent.md", intent_text()); write(project, "spec.md", spec_text())
    assert documents.check_intent(project).ok
    result = documents.check_spec(project)
    assert result.ok, result.problems
    assert set(result.evidence) == {"spec_sha256", "intent_sha256"}


@pytest.mark.parametrize("kwargs,fragment", [
    ({"features": FEATURES[:-1]}, "differ from the code"),
    ({"target": "z"}, "differs from the code"),
    ({"intent_version": 2}, "intent_version does not match"),
    ({"acceptance": "metrics:\n  accuracy: {min: 0.8}"}, "must require beating the baseline"),
    ({"acceptance": "metrics:\n  uplift_vs_baseline: {min: fast}"}, "must be a number"),
    ({"triggers": "- name: t\n  metric: accuracy\n  min: 0.5\n  then: nowhere"}, "'then' must be one of"),
    ({"triggers": "- name: t\n  metric: accuracy\n  then: model"}, "needs a numeric min and/or max"),
])
def test_spec_mistakes_are_caught(project, kwargs, fragment):
    write(project, "intent.md", intent_text()); write(project, "spec.md", spec_text(**kwargs))
    assert any(fragment in p for p in documents.check_spec(project).problems), documents.check_spec(project).problems


def test_metric_names_can_be_restricted(project):
    project.allowed_metrics = ["accuracy", "uplift_vs_baseline"]
    write(project, "intent.md", intent_text())
    write(project, "spec.md", spec_text(acceptance="metrics:\n  uplift_vs_baseline: {min: 0.02}\n  made_up: {min: 1}"))
    assert any("'made_up' is not in allowed_metrics" in p for p in documents.check_spec(project).problems)


def test_baseline_rule_can_be_switched_off(project):
    project.baseline_metric = None
    write(project, "intent.md", intent_text()); write(project, "spec.md", spec_text(acceptance="metrics:\n  accuracy: {min: 0.8}"))
    assert documents.check_spec(project).ok


def test_without_hooks_the_inputs_are_not_compared_and_the_check_says_so(project):
    project.hooks = None
    write(project, "intent.md", intent_text()); write(project, "spec.md", spec_text(features=["anything"]))
    result = documents.check_spec(project)
    assert result.ok and any("not compared with the code" in n for n in result.notes)


def test_serving_columns_must_equal_the_inputs(project):
    (project.root / "hooks.py").write_text((project.root / "hooks.py").read_text().replace('return ["tenure", "spend"]', 'return ["tenure", "spend", "outcome"]'))
    project._hooks = None
    write(project, "intent.md", intent_text()); write(project, "spec.md", spec_text())
    assert any("serving_columns() must equal the model inputs" in p for p in documents.check_spec(project).problems)


def test_two_projects_never_share_a_hooks_module(tmp_path):
    from mldlc.project import Project
    made = []
    for name, target in (("a", "ya"), ("b", "yb")):
        d = tmp_path / name; d.mkdir()
        (d / "hooks.py").write_text(f'def model_inputs():\n    return {{"target": "{target}", "features": []}}\n')
        (d / "mldlc.yaml").write_text(f"project: {name}\nmlflow:\n  training_experiment: t\n  model_name: m\nhooks: hooks\n")
        made.append(Project.load(d))
    assert [p.hooks_module().model_inputs()["target"] for p in made] == ["ya", "yb"]
