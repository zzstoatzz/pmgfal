"""integration tests for git provider support."""

import subprocess
import tempfile
from pathlib import Path

import pytest

# repos known to exist on each provider with lexicons
GIT_PROVIDER_REPOS = [
    pytest.param(
        "https://github.com/bluesky-social/atproto.git",
        id="github-full-url",
    ),
    pytest.param(
        "bluesky-social/atproto",
        id="github-shorthand",
    ),
    # tangled repos can be added here when available
    # pytest.param(
    #     "https://tangled.sh/someone/lexicons.git",
    #     id="tangled-full-url",
    # ),
]


@pytest.mark.parametrize("source", GIT_PROVIDER_REPOS)
def test_clone_and_generate(source: str) -> None:
    """test cloning and generating from various git sources."""
    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp) / "output"
        result = subprocess.run(
            ["uv", "run", "pmgfal", source, "-o", str(output_dir), "--no-cache"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, f"failed: {result.stderr}"
        assert output_dir.exists()
        py_files = list(output_dir.glob("*.py"))
        assert len(py_files) > 0, "no python files generated"


def test_shorthand_fallback_on_nonexistent() -> None:
    """test that shorthand tries providers in order and fails gracefully."""
    result = subprocess.run(
        [
            "uv",
            "run",
            "pmgfal",
            "nonexistent-owner-12345/nonexistent-repo-67890",
            "-o",
            "/tmp/test",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 1
    output = result.stdout + result.stderr
    assert "trying github" in output
    assert "trying tangled" in output
    assert "could not find" in output


def test_invalid_source_not_directory() -> None:
    """test error on invalid local path."""
    result = subprocess.run(
        ["uv", "run", "pmgfal", "/nonexistent/path/to/lexicons", "-o", "/tmp/test"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    output = result.stdout + result.stderr
    assert "not a directory" in output
