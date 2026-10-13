import statistics
import time

from django.core.management.base import BaseCommand

from academic_records.models import StudentRecord
from degree_audit.services import run_degree_audit


class Command(BaseCommand):
    help = "Benchmark single-student degree audit service latency, reporting median and p95 (target < 200 ms)."

    def add_arguments(self, parser):
        parser.add_argument("--iterations", type=int, default=50, help="Number of audit iterations (default: 50)")

    def handle(self, *args, **options):
        iterations = options["iterations"]
        self.stdout.write(f"Benchmarking run_degree_audit across {iterations} executions...")

        students = list(
            StudentRecord.objects.filter(
                institution__code="PERF_INST"
            ).select_related("pinned_curriculum__programme", "student")[:10]
        )

        if not students:
            # Fall back to any student record
            students = list(
                StudentRecord.objects.select_related(
                    "pinned_curriculum__programme", "student"
                ).all()[:10]
            )

        if not students:
            self.stderr.write("No StudentRecord found! Run 'python manage.py seed_perf_data' first.")
            return

        # Warm-up run
        run_degree_audit(students[0])

        durations_ms: list[float] = []

        for i in range(iterations):
            student = students[i % len(students)]
            t0 = time.perf_counter()
            _ = run_degree_audit(student)
            t1 = time.perf_counter()
            durations_ms.append((t1 - t0) * 1000.0)

        median_ms = statistics.median(durations_ms)
        p95_ms = sorted(durations_ms)[int(len(durations_ms) * 0.95)]
        mean_ms = statistics.mean(durations_ms)
        min_ms = min(durations_ms)
        max_ms = max(durations_ms)

        target_ms = 200.0
        status_str = "PASSED" if median_ms < target_ms and p95_ms < target_ms else "FAILED"

        self.stdout.write("==================================================")
        self.stdout.write("  Degree Audit Latency Benchmark Results")
        self.stdout.write("==================================================")
        self.stdout.write(f"  Iterations:     {iterations}")
        self.stdout.write(f"  Min:            {min_ms:.2f} ms")
        self.stdout.write(f"  Mean:           {mean_ms:.2f} ms")
        self.stdout.write(f"  Median:         {median_ms:.2f} ms (Target < {target_ms} ms)")
        self.stdout.write(f"  p95:            {p95_ms:.2f} ms (Target < {target_ms} ms)")
        self.stdout.write(f"  Max:            {max_ms:.2f} ms")
        self.stdout.write(f"  Status:         {status_str}")
        self.stdout.write("==================================================")

        if median_ms >= target_ms or p95_ms >= target_ms:
            self.stderr.write(f"Warning: Audit latency exceeded target {target_ms} ms!")
        else:
            self.stdout.write(self.style.SUCCESS("Audit performance meets SLA target < 200 ms!"))
