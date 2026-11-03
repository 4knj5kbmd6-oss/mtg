"""Every test runs in a temporary copy of tests/fixture, the folder that holds output/, as the scripts expect.
lib/ and every skills/ folder are on sys.path, so a test imports a script by its name."""
import shutil, subprocess, sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "lib"), *sorted(str(p) for p in (ROOT / "skills").iterdir() if p.is_dir())]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    """urllib, in a test and in every run() subprocess, goes through a proxy that refuses, so no test reaches a server"""
    for name in ("http_proxy", "https_proxy"): monkeypatch.setenv(name, "http://127.0.0.1:9")


@pytest.fixture(autouse=True)
def project(tmp_path, monkeypatch):
    """the fixture project, copied and made the working directory"""
    home = tmp_path / "project"
    shutil.copytree(ROOT / "tests" / "fixture", home)
    monkeypatch.chdir(home)
    return home


def run(script, *args, stdin=None):
    """a script, by its path from the repo root, run from the working directory as the owner runs it"""
    return subprocess.run([sys.executable, str(ROOT / script), *args], input=stdin, capture_output=True, text=True)


def read(path):
    return Path(path).read_text()


def snapshot():
    """every file under output/ by path, as bytes"""
    return {p: p.read_bytes() for p in sorted(Path("output").rglob("*")) if p.is_file()}
