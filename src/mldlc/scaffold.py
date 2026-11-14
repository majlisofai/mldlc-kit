"""``mldlc init`` and ``mldlc skills install``: start a project, and vendor the skills into it."""
import datetime
import shutil
from pathlib import Path

TEMPLATES = Path(__file__).parent / "templates"


def skills_dir() -> Path:
    """The skills shipped with the package, or the repo's skills/ folder in a development checkout."""
    packaged = Path(__file__).parent / "skills"
    return packaged if packaged.exists() else Path(__file__).resolve().parents[2] / "skills"


def _fill(text: str, project: str, baseline_metric: str = "uplift_vs_baseline") -> str:
    for key, value in {"{project}": project, "{date}": str(datetime.date.today()), "{baseline_metric}": baseline_metric}.items():
        text = text.replace(key, value)
    return text


def init_project(directory: Path, name: str | None = None, hooks: bool = False, force: bool = False) -> list[Path]:
    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    name = name or directory.name
    config = directory / "mldlc.yaml"
    if config.exists() and not force:
        raise SystemExit(f"{config} already exists (use --force to overwrite)")
    text = _fill((TEMPLATES / "mldlc.yaml").read_text(), name)
    if hooks:
        text = text.replace("# hooks: mldlc_hooks", "hooks: mldlc_hooks")
    config.write_text(text)
    made = [config]
    life = directory / "lifecycle"
    life.mkdir(exist_ok=True)
    for doc in ("intent.md", "spec.md"):
        if not (life / doc).exists() or force:
            (life / doc).write_text(_fill((TEMPLATES / doc).read_text(), name))
            made.append(life / doc)
    ignore = directory / ".gitignore"
    wanted = ["mlruns/", "mlflow.db", "__pycache__/"]          # what MLflow's default local store writes
    have = ignore.read_text().splitlines() if ignore.exists() else []
    missing = [w for w in wanted if w not in have]
    if missing:
        ignore.write_text("\n".join(have + missing) + "\n")
        made.append(ignore)
    if hooks and (not (directory / "mldlc_hooks.py").exists() or force):
        shutil.copy(TEMPLATES / "hooks.py", directory / "mldlc_hooks.py")
        made.append(directory / "mldlc_hooks.py")
    return made


def install_skills(dest: Path, force: bool = False) -> list[Path]:
    """Copy the skills into ``dest`` (normally ``.claude/skills``). Existing skills are kept unless ``force``."""
    src = skills_dir()
    if not src.exists():
        raise SystemExit(f"skills not found at {src}")
    dest.mkdir(parents=True, exist_ok=True)
    made = []
    for skill in sorted(p for p in src.iterdir() if p.is_dir()):
        target = dest / skill.name
        if target.exists() and not force:
            continue
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(skill, target)
        made.append(target)
    return made
