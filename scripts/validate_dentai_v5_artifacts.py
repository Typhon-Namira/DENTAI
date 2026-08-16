"""Release gate for the immutable DENTAI Unified V5 ONNX bundle."""
import argparse
from pathlib import Path

from ai_engine.inference.dentai_unified_v5_onnx import Engine, verify_artifact_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate DENTAI Unified V5 production artifacts")
    parser.add_argument("--artifacts", type=Path, default=Path("model_artifacts/dentai_v5"))
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("artifacts/production/dentai_v5_model_manifest.json"),
    )
    args = parser.parse_args()
    paths = verify_artifact_bundle(args.artifacts, args.manifest)
    Engine(args.artifacts, args.manifest)  # Require all CPU ONNX sessions to load.
    print(f"Validated {len(paths)} frozen DENTAI Unified V5 artifacts and CPU ONNX sessions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
