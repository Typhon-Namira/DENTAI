import argparse
from pathlib import Path

from ai_engine.release import validate_release


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the DENTAI AI production release gate")
    parser.add_argument("--registry", type=Path, default=Path("configs/ai/models.yaml"))
    parser.add_argument("--datasets", type=Path, default=Path("ai_engine/data/manifests"))
    parser.add_argument("--artifacts", type=Path, default=Path("model_artifacts"))
    args = parser.parse_args()
    issues = validate_release(args.registry, args.datasets, args.artifacts)
    for issue in issues:
        print(f"{issue.model_id}: {issue.code}: {issue.detail}")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
