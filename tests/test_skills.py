"""The skills are instructions, so test the facts they rely on: names, gates, commands, and that they stay generic."""
import re

import pytest
import yaml

from mldlc import cli, scaffold, stages

SKILLS = scaffold.skills_dir()
SUBCOMMANDS = set(next(a for a in cli.build_parser()._actions if a.dest == "cmd").choices)


def skill(name):
    text = (SKILLS / name / "SKILL.md").read_text()
    return yaml.safe_load(text.split("---\n")[1]), text


def test_the_skills_on_disk_are_exactly_the_documented_ones():
    assert sorted(d.name for d in SKILLS.iterdir() if d.is_dir()) == sorted(stages.SKILL_NAMES)


@pytest.mark.parametrize("name", stages.SKILL_NAMES)
def test_skill_is_well_formed(name):
    front, text = skill(name)                      # parsing the frontmatter fails on an unquoted ': ' in a value
    assert front["name"] == name
    assert 80 < len(front["description"]) < 600 and "Use " in front["description"]
    assert isinstance(front["argument-hint"], str), "argument-hint must be a quoted string, not a YAML list"
    assert "allowed-tools" in front and text.count("---\n") >= 2


@pytest.mark.parametrize("stage", stages.STAGES, ids=lambda s: s.gate)
def test_stage_skill_names_its_gate(stage):
    _, text = skill(stage.skill)
    assert stage.gate in text and (f"mldlc check {stage.gate}" in text or stage.gate in ("G4", "G5"))


@pytest.mark.parametrize("name", stages.SKILL_NAMES)
def test_every_command_a_skill_runs_exists(name):
    _, text = skill(name)
    for cmd in re.findall(r"`?mldlc (?:-C <folder> )?([a-z]+)", text):
        assert cmd in SUBCOMMANDS or cmd in ("init",), f"{name}: unknown command `mldlc {cmd}`"


@pytest.mark.parametrize("name", stages.SKILL_NAMES)
def test_skills_are_generic(name):
    _, text = skill(name)
    for lab_specific in (r"mlkit", r"projects/", r"make <team>", r"Pandera", r"\bDVC\b", r"\bf1\b", r"\bspl\b", r"steward"):
        assert not re.search(lab_specific, text), f"{name} mentions {lab_specific!r}, which belongs to one project, not to the kit"


def test_human_gates_are_never_approved_by_gate_check_in_the_skills():
    for stage in stages.STAGES:
        _, text = skill(stage.skill)
        approvals = re.findall(r"mldlc approve " + stage.gate + r" --by (\S+)", text)
        if stage.decider == "human":
            assert all(a != "gate-check" for a in approvals), stage.gate
        elif stage.gate != "G5":
            assert approvals and all(a == "gate-check" for a in approvals), stage.gate


def test_the_orchestrator_lists_every_stage_and_the_iteration_skill():
    _, text = skill("mldlc")
    for stage in stages.STAGES:
        assert f"`{stage.skill}`" in text and stage.gate in text
    assert f"`{stages.OPERATE_SKILL}`" in text and f"`{stages.ITERATE_SKILL}`" in text


def test_change_request_asset_is_the_template():
    asset = (SKILLS / "mldlc-iterate" / "assets" / "change-request.md").read_text()
    assert asset == (scaffold.TEMPLATES / "change-request.md").read_text()
    assert {"project", "opened", "kind", "reenters", "status"} <= set(yaml.safe_load(asset.split("---\n")[1]))
