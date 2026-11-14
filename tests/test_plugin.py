"""The plugin and the Python package must describe the same release."""
import json
import tomllib
from pathlib import Path

import mldlc
from mldlc import stages

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads((ROOT / path).read_text())


def test_the_plugin_lists_exactly_the_skills_that_exist():
    listed = [Path(p).name for p in load(".claude-plugin/plugin.json")["skills"]]
    assert sorted(listed) == sorted(stages.SKILL_NAMES)
    for p in load(".claude-plugin/plugin.json")["skills"]:
        assert (ROOT / p / "SKILL.md").exists(), p


def test_versions_agree_everywhere():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    plugin = load(".claude-plugin/plugin.json")["version"]
    market = load(".claude-plugin/marketplace.json")["plugins"][0]["version"]
    assert pyproject == plugin == market == mldlc.__version__


def test_the_marketplace_points_at_this_plugin():
    entry = load(".claude-plugin/marketplace.json")["plugins"][0]
    assert entry["name"] == load(".claude-plugin/plugin.json")["name"] == "mldlc" and entry["source"] == "./"


def test_the_wheel_ships_the_skills():
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert config["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"] == {"skills": "mldlc/skills"}


def test_the_license_is_mit_everywhere_it_is_declared():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    assert project["license"] == "MIT" and load(".claude-plugin/plugin.json")["license"] == "MIT"
    text = (ROOT / "LICENSE").read_text()
    assert text.startswith("MIT License") and "Copyright (c) 2026 The Majlis of AI" in text


def test_the_published_urls_agree():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    url = "https://github.com/majlisofai/mldlc-kit"
    assert project["urls"]["Repository"] == load(".claude-plugin/plugin.json")["repository"] == url
    assert url in (ROOT / "README.md").read_text() or "majlisofai/mldlc-kit" in (ROOT / "README.md").read_text()
