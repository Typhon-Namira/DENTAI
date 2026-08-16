"""Build deterministic Tooth V2 manifests from locally audited gold annotations."""

from __future__ import annotations

import argparse
from pathlib import Path

from ai_engine.data.tooth_v2 import Source, load_sources, write_corpus


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data/splits/tooth_v2"))
    parser.add_argument("--seed", type=int, default=47)
    args = parser.parse_args()
    sources = [
        Source(
            "dentex_hf_7b27ccc8",
            Path("data/canonical/dentex/hf-7b27ccc8/instances.json"),
            Path("data/raw/dentex/hf-7b27ccc8/extracted/training_data"),
            "CC-BY-NC-SA-4.0 / RESEARCH_ONLY",
            "hf-7b27ccc8",
        ),
        Source(
            "akudental_git_92e2cc3",
            Path("data/canonical/akudental/git-92e2cc3/instances.json"),
            Path("data/raw/akudental/current/source_repo/AKUDENTAL/images"),
            "CC-BY-NC-SA-4.0 / RESEARCH_ONLY",
            "git-92e2cc3ae5eebc9de509311a3edefb7106fca7dd",
        ),
    ]
    records = load_sources(sources)
    summary = write_corpus(records, args.output, seed=args.seed)
    print(summary)


if __name__ == "__main__":
    main()
