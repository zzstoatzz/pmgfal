"""pydantic model generator for atproto lexicons."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
from pathlib import Path

from pmgfal._pmgfal import __version__, generate

__all__ = ["__version__", "generate", "main", "get_cache_dir"]


def get_cache_dir() -> Path:
    """get the user cache directory for pmgfal."""
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Caches"
    elif sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "pmgfal"


def hash_lexicons(lexicon_dir: Path, prefix: str | None = None) -> str:
    """compute a hash of all lexicon files in a directory."""
    hasher = hashlib.sha256()

    # include version in hash so cache invalidates on upgrades
    hasher.update(__version__.encode())

    # include prefix in hash
    if prefix:
        hasher.update(prefix.encode())

    # hash all json files in sorted order for determinism
    json_files = sorted(lexicon_dir.rglob("*.json"))
    for path in json_files:
        hasher.update(path.name.encode())
        hasher.update(path.read_bytes())

    return hasher.hexdigest()[:16]


def main(args: list[str] | None = None) -> int:
    """cli entry point."""
    parser = argparse.ArgumentParser(
        prog="pmgfal",
        description="pydantic model generator for atproto lexicons",
    )
    parser.add_argument(
        "lexicon_dir",
        nargs="?",
        type=Path,
        help="directory containing lexicon json files (default: ./lexicons or .)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("./generated"),
        help="output directory (default: ./generated)",
    )
    parser.add_argument(
        "-p",
        "--prefix",
        type=str,
        default=None,
        help="namespace prefix filter (e.g. 'fm.plyr')",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="force regeneration, ignoring cache",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    parsed = parser.parse_args(args)

    # auto-detect lexicon directory
    if parsed.lexicon_dir is None:
        if Path("./lexicons").is_dir():
            lexicon_dir = Path("./lexicons")
        else:
            lexicon_dir = Path(".")
    else:
        lexicon_dir = parsed.lexicon_dir

    if not lexicon_dir.is_dir():
        print(f"error: not a directory: {lexicon_dir}", file=sys.stderr)
        return 1

    try:
        # compute hash of lexicons
        lexicon_hash = hash_lexicons(lexicon_dir, parsed.prefix)
        cache_dir = get_cache_dir() / lexicon_hash

        # check cache
        if not parsed.no_cache and cache_dir.exists():
            # cache hit - copy cached files to output
            parsed.output.mkdir(parents=True, exist_ok=True)
            cached_files = list(cache_dir.glob("*.py"))
            for cached in cached_files:
                dest = parsed.output / cached.name
                shutil.copy2(cached, dest)
            print(f"cache hit ({lexicon_hash}) - copied {len(cached_files)} file(s):")
            for f in cached_files:
                print(f"  {parsed.output / f.name}")
            return 0

        # cache miss - generate
        files = generate(
            str(lexicon_dir),
            str(parsed.output),
            parsed.prefix,
        )

        # store in cache
        cache_dir.mkdir(parents=True, exist_ok=True)
        for f in files:
            shutil.copy2(f, cache_dir / Path(f).name)

        print(f"generated {len(files)} file(s) (cached as {lexicon_hash}):")
        for f in files:
            print(f"  {f}")
        return 0
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
