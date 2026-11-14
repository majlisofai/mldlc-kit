"""mldlc: a gated ML development life cycle. The CLI is `mldlc`; a project's own code uses the helpers below."""
import os

# MLflow prints a hint aimed at AI assistants on import; it is noise in a CLI whose output people read.
os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

from mldlc.evidence import lineage_tags, record_validation
from mldlc.project import Project

__all__ = ["Project", "lineage_tags", "record_validation"]
__version__ = "0.1.0"
