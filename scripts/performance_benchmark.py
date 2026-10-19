"""
Phase 10 Performance & Query Count Benchmarking Suite.
Measures real performance metrics against PostgreSQL 16 on seeded academic data:
1. Individual student degree audit latency (median, p95).
2. Cohort degree audit processing runtime.
3. Database query counts on critical endpoints.
"""

import os
import sys
import time
from pathlib import Path

import django
import numpy as np

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from django.conf import settings

if "testserver" not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append("testserver")

from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from academic_records.models import StudentRecord
from degree_audit.services import run_degree_audit


def benchmark_single_student_audit():
    print("\n--- 1. Individual Degree Audit Latency Benchmark ---")
    record = StudentRecord.objects.filter(pinned_curriculum__isnull=False).first()
    if not record:
        print("No student record with pinned curriculum found. Skipping.")
        return None

    # Warm-up run
    run_degree_audit(record)

    latencies_ms = []
    iterations = 100
    for _ in range(iterations):
        t0 = time.perf_counter()
        run_degree_audit(record)
        t1 = time.perf_counter()
        latencies_ms.append((t1 - t0) * 1000)

    median_ms = float(np.median(latencies_ms))
    p95_ms = float(np.percentile(latencies_ms, 95))
    min_ms = float(np.min(latencies_ms))
    max_ms = float(np.max(latencies_ms))

    print(f"Iterations: {iterations}")
    print("Target:     < 200.0 ms")
    print(f"Min:        {min_ms:.2f} ms")
    print(f"Median:     {median_ms:.2f} ms")
    print(f"p95:        {p95_ms:.2f} ms")
    print(f"Max:        {max_ms:.2f} ms")
    print(f"Status:     {'PASSED' if p95_ms < 200.0 else 'FAILED'}")

    return {"median_ms": median_ms, "p95_ms": p95_ms}


def benchmark_cohort_audit():
    print("\n--- 2. Cohort Degree Audit Processing Runtime ---")
    cohort = list(StudentRecord.objects.filter(pinned_curriculum__isnull=False)[:50])
    cohort_size = len(cohort)
    if cohort_size == 0:
        print("Cohort is empty. Skipping.")
        return None

    print(f"Auditing cohort of {cohort_size} students...")
    t0 = time.perf_counter()
    for idx, student in enumerate(cohort, start=1):
        run_degree_audit(student)
        if idx % 10 == 0 or idx == cohort_size:
            pct = (idx / cohort_size) * 100
            print(f"  Progress: {idx}/{cohort_size} ({pct:.0f}%) completed...")
    t1 = time.perf_counter()

    total_time_s = t1 - t0
    rate = cohort_size / total_time_s
    avg_per_student_ms = (total_time_s / cohort_size) * 1000

    print(f"Cohort Size:            {cohort_size} students")
    print(f"Total Runtime:          {total_time_s:.2f} s")
    print(f"Throughput:             {rate:.1f} students/sec")
    print(f"Average Latency:        {avg_per_student_ms:.2f} ms/student")

    return {"total_time_s": total_time_s, "throughput": rate}


def benchmark_query_counts():
    print("\n--- 3. Database Query Counts on Key Endpoints ---")
    client = APIClient()

    # Find coordinator user for analytics
    coord_record = StudentRecord.objects.first()
    if not coord_record:
        print("No records available for query count benchmark.")
        return

    user = coord_record.student
    client.force_authenticate(user=user)

    endpoints = [
        ("Student Record Detail", f"/api/v1/student-records/{coord_record.id}/"),
        ("Student Degree Audit", f"/api/v1/student-records/{coord_record.id}/audit/"),
        ("Active Curricula List", "/api/v1/curricula/"),
        ("Notifications List", "/api/v1/notifications/"),
    ]

    print(f"{'Endpoint':<35} | {'Query Count':<12} | {'Response Time':<14} | {'Status'}")
    print("-" * 75)

    for name, path in endpoints:
        with CaptureQueriesContext(connection) as ctx:
            t0 = time.perf_counter()
            resp = client.get(path)
            t1 = time.perf_counter()

        q_count = len(ctx.captured_queries)
        duration_ms = (t1 - t0) * 1000
        print(f"{name:<35} | {q_count:<12} | {duration_ms:.2f} ms{'':<7} | HTTP {resp.status_code}")


def main():
    print("=================================================================")
    print("Academic Advisor & Degree Planning System - Performance Benchmark")
    print("=================================================================")
    benchmark_single_student_audit()
    benchmark_cohort_audit()
    benchmark_query_counts()
    print("\n=================================================================")
    print("Benchmark Completed Successfully.")
    print("=================================================================")


if __name__ == "__main__":
    main()
