import numpy as np


def bootstrap_confidence_interval(
    values: np.ndarray, *, resamples: int = 2000, confidence: float = 0.95, seed: int = 47
) -> dict[str, float | int | str]:
    """Case-level percentile bootstrap; callers must supply one value per independent case."""
    values = np.asarray(values, dtype=float)
    if values.ndim != 1 or not len(values):
        raise ValueError("bootstrap requires a non-empty vector of independent case values")
    rng = np.random.default_rng(seed)
    estimates = np.mean(rng.choice(values, size=(resamples, len(values)), replace=True), axis=1)
    alpha = (1 - confidence) / 2
    return {
        "estimate": float(values.mean()),
        "ci_low": float(np.quantile(estimates, alpha)),
        "ci_high": float(np.quantile(estimates, 1 - alpha)),
        "method": "case-level percentile bootstrap",
        "resamples": resamples,
    }


def brier_score(probabilities: np.ndarray, labels: np.ndarray) -> float:
    probabilities, labels = np.asarray(probabilities, float), np.asarray(labels, float)
    if probabilities.shape != labels.shape:
        raise ValueError("probabilities and labels must have identical shapes")
    return float(np.mean((probabilities - labels) ** 2))


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
