import numpy as np


def segmentation_metrics(predicted: np.ndarray, expected: np.ndarray) -> dict[str, float]:
    predicted, expected = predicted.astype(bool), expected.astype(bool)
    intersection = np.logical_and(predicted, expected).sum()
    union = np.logical_or(predicted, expected).sum()
    denominator = predicted.sum() + expected.sum()
    return {
        "dice": float(2 * intersection / denominator) if denominator else 1.0,
        "iou": float(intersection / union) if union else 1.0,
    }


def expected_calibration_error(
    probabilities: np.ndarray, labels: np.ndarray, bins: int = 10
) -> float:
    edges = np.linspace(0, 1, bins + 1)
    error = 0.0
    for lower, upper in zip(edges[:-1], edges[1:], strict=True):
        selected = (probabilities >= lower) & (probabilities < upper)
        if selected.any():
            error += selected.mean() * abs(probabilities[selected].mean() - labels[selected].mean())
    return float(error)
