from __future__ import annotations

import json
import random
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def get_pipeline_version() -> str:
    """Get pipeline version from pyproject.toml or git."""
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--always", "--dirty"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
    if pyproject_path.exists():
        content = pyproject_path.read_text(encoding="utf-8")
        for line in content.splitlines():
            if line.strip().startswith("version"):
                parts = line.split("=", 1)
                if len(parts) == 2:
                    version = parts[1].strip().strip('"').strip("'")
                    return version

    return "unknown"


def set_random_seed(seed: int) -> None:
    """Set random seed for deterministic generation."""
    random.seed(seed)

    try:
        import numpy as np
        np.random.seed(seed)
    except ImportError:
        pass


def stamp_version(output_path: Path, extra_metadata: Optional[dict] = None) -> Path:
    """Add version info sidecar to output file.

    Creates a .version.json sidecar file next to the output with:
    - pipeline_version: Version string from get_pipeline_version()
    - timestamp: ISO format UTC timestamp
    - output_file: Name of the output file
    - extra_metadata: Any additional metadata passed in

    Returns path to the version sidecar file.
    """
    version_info = {
        "pipeline_version": get_pipeline_version(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "output_file": output_path.name,
    }

    if extra_metadata:
        version_info["metadata"] = extra_metadata

    sidecar_path = output_path.with_suffix(output_path.suffix + ".version.json")
    sidecar_path.write_text(json.dumps(version_info, indent=2), encoding="utf-8")

    return sidecar_path
