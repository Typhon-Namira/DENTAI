import statistics
import time
import tracemalloc
from collections.abc import Callable


def benchmark_cpu(infer: Callable[[], object], warmup: int = 3, iterations: int = 20) -> dict:
    for _ in range(warmup):
        infer()
    tracemalloc.start()
    timings = []
    for _ in range(iterations):
        started = time.perf_counter()
        infer()
        timings.append((time.perf_counter() - started) * 1000)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    timings.sort()
    return {
        "iterations": iterations,
        "p50_ms": statistics.median(timings),
        "p95_ms": timings[max(0, int(iterations * 0.95) - 1)],
        "peak_python_bytes": peak,
    }
