"""Install each built artifact in a fresh venv and run the shipped examples."""

from __future__ import annotations

import argparse
import os
import subprocess
import tempfile
import venv
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    artifacts = sorted((root / "dist").glob("*.whl")) + sorted((root / "dist").glob("*.tar.gz"))
    if len(artifacts) != 2:
        raise SystemExit("Expected exactly one wheel and one sdist in dist/")
    examples = sorted((root / "examples").glob("*.py"))
    if not examples:
        raise SystemExit("No executable examples found")
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    for artifact in artifacts:
        with tempfile.TemporaryDirectory(prefix=args.package + "-install-") as temporary:
            target = Path(temporary)
            venv.create(target / "venv", with_pip=True)
            python = target / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

            def run(*command: str, python: Path = python, target: Path = target) -> None:
                subprocess.run([str(python), *command], cwd=target, env=env, check=True)

            run("-m", "pip", "install", "--disable-pip-version-check", str(artifact))
            run("-I", "-c", f"import {args.package}; print({args.package}.__file__)")
            for example in examples:
                run("-I", str(example))
            print("CLEAN INSTALL PASSED:", artifact.name, flush=True)


if __name__ == "__main__":
    main()
