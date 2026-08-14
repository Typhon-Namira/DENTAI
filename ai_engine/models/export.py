from pathlib import Path
from typing import Any


def export_onnx(model: Any, sample_input: Any, destination: Path, *, opset: int = 18) -> Path:
    """Export plumbing only. A trained, validated checkpoint must be supplied by the caller."""
    import torch

    destination.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        model,
        sample_input,
        destination,
        opset_version=opset,
        input_names=["image"],
        output_names=["output"],
        dynamic_axes={"image": {0: "batch"}, "output": {0: "batch"}},
    )
    return destination


def validate_onnx(path: Path) -> None:
    import onnx

    model = onnx.load(path)
    onnx.checker.check_model(model)


def parity_max_abs(reference: Any, candidate: Any) -> float:
    import numpy as np

    return float(np.max(np.abs(np.asarray(reference) - np.asarray(candidate))))
