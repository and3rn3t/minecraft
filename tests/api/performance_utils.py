"""
Performance Testing Utilities
Helpers for load testing and performance measurement
"""

import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List


class PerformanceTimer:
    """Context manager for timing operations"""

    def __init__(self, label: str = "Operation"):
        self.label = label
        self.start_time = None
        self.end_time = None
        self.duration = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        self.duration = self.end_time - self.start_time
        return False

    def get_duration(self) -> float:
        """Get duration in seconds"""
        if self.duration is None:
            raise ValueError("Timer not completed")
        return self.duration


def measure_execution_time(func: Callable, *args, **kwargs) -> float:
    """Measure execution time of a function"""
    start = time.perf_counter()
    func(*args, **kwargs)
    end = time.perf_counter()
    return end - start


def run_load_test(func: Callable, num_requests: int = 100, num_threads: int = 10, *args, **kwargs) -> Dict[str, Any]:
    """Run load test on a function"""
    results = {
        "total_requests": num_requests,
        "num_threads": num_threads,
        "durations": [],
        "success_count": 0,
        "error_count": 0,
        "errors": [],
    }

    def run_request():
        try:
            start = time.perf_counter()
            result = func(*args, **kwargs)
            duration = time.perf_counter() - start
            results["durations"].append(duration)
            results["success_count"] += 1
            return result
        except Exception as e:
            results["error_count"] += 1
            results["errors"].append(str(e))
            return None

    start_time = time.perf_counter()

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(run_request) for _ in range(num_requests)]
        for future in as_completed(futures):
            future.result()

    end_time = time.perf_counter()

    # Calculate statistics
    durations: list[float] = results["durations"]
    if durations:
        results["total_time"] = end_time - start_time
        results["avg_duration"] = statistics.mean(durations)
        results["min_duration"] = min(durations)
        results["max_duration"] = max(durations)
        results["median_duration"] = statistics.median(durations)
        results["requests_per_second"] = num_requests / results["total_time"]

        if len(durations) > 1:
            results["std_dev"] = statistics.stdev(durations)
        else:
            results["std_dev"] = 0
    else:
        results["total_time"] = end_time - start_time
        results["avg_duration"] = 0
        results["min_duration"] = 0
        results["max_duration"] = 0
        results["median_duration"] = 0
        results["requests_per_second"] = 0
        results["std_dev"] = 0

    return results


def print_performance_report(results: Dict[str, Any]):
    """Print formatted performance report"""
    separator = "=" * 60
    print("\n" + separator)
    print("Performance Test Results")
    print(separator)
    print(f"Total Requests: {results['total_requests']}")
    print(f"Threads: {results['num_threads']}")
    print(f"Success: {results['success_count']}")
    print(f"Errors: {results['error_count']}")
    print("\nTiming Statistics:")
    print(f"  Total Time: {results['total_time']:.3f}s")
    print(f"  Average: {results['avg_duration']*1000:.2f}ms")
    print(f"  Min: {results['min_duration']*1000:.2f}ms")
    print(f"  Max: {results['max_duration']*1000:.2f}ms")
    print(f"  Median: {results['median_duration']*1000:.2f}ms")
    print(f"  Std Dev: {results['std_dev']*1000:.2f}ms")
    print("\nThroughput:")
    print(f"  Requests/Second: {results['requests_per_second']:.2f}")

    if results["errors"]:
        print(f"\nErrors ({len(results['errors'])}):")
        for error in results["errors"][:10]:  # Show first 10 errors
            print(f"  - {error}")
        if len(results["errors"]) > 10:
            print(f"  ... and {len(results['errors']) - 10} more")
    print(separator + "\n")


def benchmark_endpoint(
    client: Any, method: str, endpoint: str, num_requests: int = 100, num_threads: int = 10, **request_kwargs: Any
) -> Dict[str, Any]:
    """Benchmark an API endpoint"""

    def make_request():
        if method.upper() == "GET":
            return client.get(endpoint, **request_kwargs)
        elif method.upper() == "POST":
            return client.post(endpoint, **request_kwargs)
        elif method.upper() == "PUT":
            return client.put(endpoint, **request_kwargs)
        elif method.upper() == "DELETE":
            return client.delete(endpoint, **request_kwargs)
        else:
            raise ValueError(f"Unsupported method: {method}")

    return run_load_test(make_request, num_requests, num_threads)
