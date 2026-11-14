"""A project is a directory with an ``mldlc.yaml``: where its life-cycle files live, how its MLflow runs
are named, and (optionally) a hooks module that connects the spec to its code."""
import fnmatch
import hashlib
import importlib
import importlib.util
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

CONFIG_NAME = "mldlc.yaml"

# The run tags the gates read. A project logs them with ``mldlc.lineage_tags`` or maps its own names here.
DEFAULT_TAGS = {
    "gate": "validation.gate",            # "pass" on a validation run that passed
    "data_version": "data.version",       # the data version the run used
    "data_verified": "data.verified",     # "true" when the files matched that version at run time
    "git_sha": "git.sha",
    "git_dirty": "git.dirty",             # "false" when the code was committed
}


class ConfigError(SystemExit):
    pass


def find_config(start: Path) -> Path:
    start = start.resolve()
    for folder in [start, *start.parents]:
        if (folder / CONFIG_NAME).exists():
            return folder / CONFIG_NAME
    raise ConfigError(f"no {CONFIG_NAME} in {start} or any parent folder; run `mldlc init` to create one")


@dataclass
class Project:
    root: Path
    name: str
    lifecycle_dir: Path
    training_experiment: str
    model_name: str
    validation_experiment: str | None = None
    tracking_uri: str | None = None
    alias: str = "production"
    data: dict = field(default_factory=lambda: {"type": "none"})
    tags: dict = field(default_factory=lambda: dict(DEFAULT_TAGS))
    baseline_metric: str | None = "uplift_vs_baseline"
    allowed_metrics: list = field(default_factory=lambda: ["*"])
    hooks: str | None = None
    commands: dict = field(default_factory=dict)
    code_paths: list = field(default_factory=lambda: ["."])
    _hooks: object = field(default=None, repr=False, compare=False)

    @classmethod
    def load(cls, path: str | Path | None = None) -> "Project":
        """Load from a directory (searching upward) or from an mldlc.yaml path; default is the cwd."""
        p = Path(path) if path else Path.cwd()
        cfg = p if p.is_file() else find_config(p)
        raw = yaml.safe_load(cfg.read_text()) or {}
        ml = raw.get("mlflow") or {}
        missing = [k for k, v in (("project", raw.get("project")), ("mlflow.training_experiment", ml.get("training_experiment")),
                                  ("mlflow.model_name", ml.get("model_name"))) if not v]
        if missing:
            raise ConfigError(f"{cfg}: missing {', '.join(missing)}")
        root = cfg.parent
        return cls(
            root=root, name=str(raw["project"]), lifecycle_dir=(root / raw.get("lifecycle_dir", "lifecycle")).resolve(),
            training_experiment=ml["training_experiment"], model_name=ml["model_name"],
            validation_experiment=ml.get("validation_experiment"), tracking_uri=ml.get("tracking_uri"),
            alias=ml.get("production_alias", "production"), data=raw.get("data") or {"type": "none"},
            tags={**DEFAULT_TAGS, **(raw.get("evidence_tags") or {})},
            baseline_metric=raw.get("baseline_metric", "uplift_vs_baseline"),
            allowed_metrics=raw.get("allowed_metrics") or ["*"], hooks=raw.get("hooks"),
            commands=raw.get("commands") or {}, code_paths=raw.get("code_paths") or ["."])

    # ------------------------------------------------------------------ artifacts

    @property
    def intent_path(self) -> Path:
        return self.lifecycle_dir / "intent.md"

    @property
    def spec_path(self) -> Path:
        return self.lifecycle_dir / "spec.md"

    @property
    def ledger_path(self) -> Path:
        return self.lifecycle_dir / "gates.yaml"

    def card_path(self, version) -> Path:
        return self.lifecycle_dir / "releases" / f"v{version}.md"

    # ------------------------------------------------------------------ data version

    def data_version(self) -> str | None:
        """An opaque string that changes whenever the data does; None when the project declares no data version."""
        kind = self.data.get("type", "none")
        if kind == "none":
            return None
        if kind == "dvc":
            pointer = (self.root / self.data["path"]).read_text()
            return str(yaml.safe_load(pointer)["outs"][0]["md5"])
        if kind == "file":
            import hashlib
            return hashlib.sha256((self.root / self.data["path"]).read_bytes()).hexdigest()
        if kind == "command":
            out = subprocess.run(self.data["command"], shell=True, cwd=self.root, capture_output=True, text=True, check=True)
            return out.stdout.strip()
        raise ConfigError(f"data.type must be dvc, file, command or none, not {kind!r}")

    # ------------------------------------------------------------------ hooks and metrics

    def hooks_module(self):
        """The project's hooks module, or None. It may define model_inputs(), serving_columns() and smoke_payload().

        Loaded from the project's own file under a unique name, so two projects in one process never share a
        module that happens to have the same name."""
        if not self.hooks:
            return None
        if self._hooks is None:
            file = self.root / (self.hooks.replace(".", "/") + ".py")
            if not file.exists():
                raise ConfigError(f"hooks: {file} does not exist")
            unique = "mldlc_hooks_" + hashlib.sha1(str(file).encode()).hexdigest()[:10]
            spec = importlib.util.spec_from_file_location(unique, file)
            module = importlib.util.module_from_spec(spec)
            if str(self.root) not in sys.path:
                sys.path.insert(0, str(self.root))      # so the hooks can import the project's own modules
            spec.loader.exec_module(module)
            self._hooks = module
        return self._hooks

    def metric_allowed(self, name: str) -> bool:
        return any(fnmatch.fnmatch(name, pattern) for pattern in self.allowed_metrics)
