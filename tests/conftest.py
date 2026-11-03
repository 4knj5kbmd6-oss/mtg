"""Every test runs in a temporary copy of tests/fixture, the folder that holds output/, as the scripts expect."""
import importlib.util, shutil, subprocess, sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"


@pytest.fixture(autouse=True)
def project(tmp_path, monkeypatch):
    """the fixture project, copied and made the working directory"""
    home = tmp_path / "project"
    shutil.copytree(ROOT / "tests" / "fixture", home)
    monkeypatch.chdir(home)
    return home


def run(script, *args, stdin=None):
    """a skills/ script run from the working directory, as the owner runs it"""
    return subprocess.run([sys.executable, str(SKILLS / script), *args], input=stdin, capture_output=True, text=True)


def load(script):
    """a skills/ script imported as a module, hyphenated names included"""
    path = SKILLS / script
    spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read(path):
    return Path(path).read_text()


def snapshot():
    """every file under output/ by path, as bytes"""
    return {p: p.read_bytes() for p in sorted(Path("output").rglob("*")) if p.is_file()}
