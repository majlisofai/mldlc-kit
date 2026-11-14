"""G2 to G5, the approval ledger and what makes a gate stale. MLflow is faked; tests/test_e2e.py uses the real one."""
import pytest

from conftest import FakeClient, card_text, intent_text, spec_text, tags_for, write
from mldlc import documents, evidence, gates, ledger, release, stages


def approve_through(project, c, upto="G1"):
    write(project, "intent.md", intent_text()); write(project, "spec.md", spec_text())
    assert gates.approve(project, "G0", "Ana Lima", "", c).ok
    if upto != "G0":
        assert gates.approve(project, "G1", "Ana Lima", "", c).ok


def build_up(project, c, tags=None, metrics=None):
    approve_through(project, c)
    c.add_run("demo-validation", "val1", tags_for(project))
    assert gates.approve(project, "G2", "gate-check", "", c).ok
    c.add_run("demo-train", "run1", tags_for(project, **(tags or {})), metrics or {"accuracy": 0.8, "uplift_vs_baseline": 0.05})
    c.versions["run1"] = 3


def states(project, c):
    return {s.gate: (st, why) for s, st, why in ledger.status(project, c)}


def test_human_gates_cannot_be_approved_by_an_agent(project, client):
    write(project, "intent.md", intent_text())
    for by in ("", "gate-check"):
        with pytest.raises(SystemExit, match="person's approval"):
            gates.approve(project, "G0", by, "", client)
    with pytest.raises(SystemExit, match="promote"):
        gates.approve(project, "G5", "Ana", "", client)


def test_editing_an_approved_artifact_makes_it_and_everything_after_stale(project, client):
    approve_through(project, client)
    assert [st for _, st, _ in ledger.status(project, client)][:2] == ["valid", "valid"]
    write(project, "intent.md", intent_text() + "\nA new constraint was added.\n")
    s = states(project, client)
    assert s["G0"][0] == "stale" and "intent.md changed" in s["G0"][1] and s["G1"][0] == "stale"


def test_a_gate_cannot_be_approved_before_the_one_before_it(project, client):
    write(project, "intent.md", intent_text()); write(project, "spec.md", spec_text())
    result = gates.approve(project, "G1", "Ana Lima", "", client)
    assert not result.ok and "G0 is pending" in result.problems[0]


def test_data_gate_needs_a_passing_validation_on_the_current_data_version(project, client):
    approve_through(project, client)
    assert not gates.run_check(project, "G2", client).ok                                    # no validation run yet
    client.add_run("demo-validation", "v1", tags_for(project, **{"data.version": "old"}))
    assert any("different data version" in p for p in evidence.check_data(project, client).problems)
    client.add_run("demo-validation", "v2", tags_for(project, **{"validation.gate": "fail"}))
    assert any("did not pass" in p for p in evidence.check_data(project, client).problems)
    client.add_run("demo-validation", "v3", tags_for(project))
    assert gates.approve(project, "G2", "gate-check", "", client).ok


def test_changing_the_data_makes_the_data_gate_and_later_gates_stale(project, client):
    build_up(project, client)
    assert gates.approve(project, "G3", "gate-check", "", client).ok
    (project.root / "data.csv").write_text("a,b\n9,9\n")
    s = states(project, client)
    assert s["G2"][0] == "stale" and "data version changed" in s["G2"][1] and s["G3"][0] in ("stale", "blocked")


def test_build_gate_refuses_uncommitted_code_and_needs_a_registered_model(project, client):
    build_up(project, client, tags={"git.dirty": "true"})
    result = evidence.check_build(project, client)
    assert not result.ok and any("uncommitted code" in p for p in result.problems)
    client.add_run("demo-train", "run2", tags_for(project))
    assert any("no registered model" in p for p in evidence.check_build(project, client).problems)
    client.versions["run2"] = 4
    assert evidence.check_build(project, client).evidence["model_version"] == "4"


def test_acceptance_gate_compares_metrics_with_the_spec(project, client):
    build_up(project, client)
    assert gates.approve(project, "G3", "gate-check", "", client).ok
    ok = evidence.check_acceptance(project, client)
    assert ok.ok and any("PASS  accuracy" in n for n in ok.notes)
    client.add_run("demo-train", "run2", tags_for(project), {"accuracy": 0.60, "uplift_vs_baseline": 0.05}); client.versions["run2"] = 4
    bad = evidence.check_acceptance(project, client)
    assert not bad.ok and any("accuracy = 0.6000" in p for p in bad.problems)
    assert states(project, client)["G3"][0] == "stale"                  # a newer run exists than the one G3 approved


def release_ready(project, client, monkeypatch):
    build_up(project, client)
    assert gates.approve(project, "G3", "gate-check", "", client).ok and gates.approve(project, "G4", "gate-check", "", client).ok
    monkeypatch.setattr(release, "smoke_test", lambda p, v: ([], ["smoke ok"]))
    return project.card_path(3)


def test_release_needs_every_gate_a_model_card_with_the_facts_and_a_working_model(project, client, monkeypatch):
    card = release_ready(project, client, monkeypatch)
    missing = release.check_release(project, None, client)
    assert not missing.ok and any("model card missing" in p for p in missing.problems)
    card.parent.mkdir(parents=True); card.write_text(card_text(run_id="other", data_version="other"))
    assert any("must be stated" in p for p in release.check_release(project, None, client).problems)
    card.write_text(card_text(data_version=project.data_version()))
    monkeypatch.setattr(release, "smoke_test", lambda p, v: (["smoke test failed: boom"], []))
    assert any("smoke test failed" in p for p in release.check_release(project, None, client).problems)
    monkeypatch.setattr(release, "smoke_test", lambda p, v: ([], []))
    assert release.check_release(project, None, client).ok


def test_promote_sets_the_alias_tags_the_version_and_records_who_approved(project, client, monkeypatch):
    card = release_ready(project, client, monkeypatch)
    card.parent.mkdir(parents=True); card.write_text(card_text(data_version=project.data_version()))
    with pytest.raises(SystemExit, match="person's approval"):
        release.promote(project, None, "gate-check", "", client)
    result = release.promote(project, None, "Ana Lima", "go", client)
    assert result.ok and client.alias["production"] == "3"
    assert client.tags[("3", "lifecycle.approved_by")] == "Ana Lima" and ("3", "lifecycle.spec_sha256") in client.tags
    last = ledger.read_ledger(project)[-1]
    assert last["gate"] == "G5" and last["event"] == "promote" and last["by"] == "Ana Lima"
    assert states(project, client)["G5"][0] == "valid"


def test_the_production_alias_is_configurable(project, client, monkeypatch):
    project.alias = "champion"
    card = release_ready(project, client, monkeypatch)
    card.parent.mkdir(parents=True); card.write_text(card_text(data_version=project.data_version()))
    assert release.promote(project, None, "Ana Lima", "", client).ok and client.alias == {"champion": "3"}


def test_rollback_only_returns_to_a_version_that_was_released(project, client, monkeypatch):
    card = release_ready(project, client, monkeypatch)
    card.parent.mkdir(parents=True); card.write_text(card_text(data_version=project.data_version()))
    release.promote(project, None, "Ana Lima", "", client)
    assert not release.rollback(project, "1", "Ana Lima", "bad", client).ok
    with pytest.raises(SystemExit, match="--reason"):
        release.rollback(project, "3", "Ana Lima", "", client)
    assert release.rollback(project, "3", "Ana Lima", "back to the known good model", client).ok
    assert ledger.read_ledger(project)[-1]["event"] == "rollback"


def test_triggers_fire_when_the_world_changes_and_say_where_to_re_enter(project, client):
    write(project, "intent.md", intent_text())
    write(project, "spec.md", spec_text(triggers="- name: drop\n  metric: accuracy\n  compare_to: baseline_accuracy\n  max_drop: 0.1\n  then: data"))
    client.add_run("demo-train", "run1", tags_for(project), {"accuracy": 0.60, "baseline_accuracy": 0.80})
    fired = evidence.evaluate_triggers(project, client)
    assert fired[0]["fired"] is True and fired[0]["then"] == "data" and "drop 0.200" in fired[0]["detail"]
    client.add_run("demo-train", "run2", tags_for(project), {"accuracy": 0.79, "baseline_accuracy": 0.80})
    assert evidence.evaluate_triggers(project, client)[0]["fired"] is False


def test_reentry_names_the_earliest_gate_a_change_can_invalidate():
    assert {k: v[0] for k, v in stages.REENTRY.items()} == {"intent": "G0", "spec": "G1", "data": "G2", "model": "G3", "evaluation": "G4", "release": "G5"}
    assert [s.gate for s in stages.STAGES] == ["G0", "G1", "G2", "G3", "G4", "G5"]
    assert {s.gate for s in stages.STAGES if s.decider == "human"} == {"G0", "G1", "G5"}
