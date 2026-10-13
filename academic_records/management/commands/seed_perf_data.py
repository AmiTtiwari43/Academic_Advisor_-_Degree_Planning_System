import time
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from academic_records.models import (
    AcademicTerm,
    StudentRecord,
    TranscriptEntry,
    TranscriptEntryStatus,
    VerificationStatus,
)
from accounts.models import InstitutionMembership, Role
from curriculum.models import (
    Course,
    CurriculumStatus,
    CurriculumVersion,
    DegreeType,
    Programme,
    RequirementGroup,
    RequirementGroupCourse,
    RequirementGroupType,
)
from institutions.models import Institution


class Command(BaseCommand):
    help = "Seed performance dataset (students, realistic curriculum with >= 150 courses, transcript entries) for benchmarking audit."

    def add_arguments(self, parser):
        parser.add_argument("--students", type=int, default=100, help="Number of students to seed (default: 100)")
        parser.add_argument("--courses", type=int, default=150, help="Number of courses in curriculum (default: 150)")

    def handle(self, *args, **options):
        num_students = options["students"]
        num_courses = options["courses"]

        self.stdout.write(f"Seeding performance data: {num_students} students, {num_courses} courses...")
        start_t = time.time()

        with transaction.atomic():
            inst, _ = Institution.objects.get_or_create(
                code="PERF_INST",
                defaults={"name": "Performance Benchmark Institute"},
            )

            # Terms
            term_fall, _ = AcademicTerm.objects.get_or_create(
                institution=inst,
                code="FA2026",
                defaults={
                    "name": "Fall 2026",
                    "season": "FALL",
                    "year": 2026,
                    "start_date": "2026-09-01",
                    "end_date": "2026-12-20",
                },
            )
            term_spring, _ = AcademicTerm.objects.get_or_create(
                institution=inst,
                code="SP2027",
                defaults={
                    "name": "Spring 2027",
                    "season": "SPRING",
                    "year": 2027,
                    "start_date": "2027-01-15",
                    "end_date": "2027-05-15",
                },
            )

            # Programme
            prog, _ = Programme.objects.get_or_create(
                institution=inst,
                code="BSCS_PERF",
                defaults={
                    "name": "B.S. in Computer Science (Perf)",
                    "degree_type": DegreeType.BACHELOR,
                    "department": "Computer Science",
                },
            )

            # Curriculum Version
            version, _ = CurriculumVersion.objects.get_or_create(
                institution=inst,
                programme=prog,
                version_number=1,
                defaults={
                    "academic_year": "2026-2027",
                    "status": CurriculumStatus.DRAFT,
                    "total_credits_required": Decimal("120.00"),
                    "min_cgpa_required": Decimal("2.00"),
                },
            )

            # Ensure courses exist (>= 150 courses)
            courses_to_create = []
            existing_codes = set(
                Course.objects.filter(institution=inst).values_list("code", flat=True)
            )
            for i in range(1, num_courses + 1):
                code = f"CS_{i:03d}"
                if code not in existing_codes:
                    courses_to_create.append(
                        Course(
                            institution=inst,
                            code=code,
                            title=f"Computer Science Topic {i}",
                            credits=Decimal("4.00"),
                        )
                    )
            if courses_to_create:
                Course.objects.bulk_create(courses_to_create, ignore_conflicts=True)

            all_courses = list(Course.objects.filter(institution=inst).order_by("code"))

            # Create requirement groups if not existing
            core_group, _ = RequirementGroup.objects.get_or_create(
                institution=inst,
                curriculum_version=version,
                name="Core CS Requirements",
                defaults={
                    "group_type": RequirementGroupType.MANDATORY,
                    "min_credits": Decimal("40.00"),
                    "min_courses": 10,
                    "display_order": 1,
                },
            )
            elective_group, _ = RequirementGroup.objects.get_or_create(
                institution=inst,
                curriculum_version=version,
                name="CS Advanced Electives",
                defaults={
                    "group_type": RequirementGroupType.ELECTIVE,
                    "min_credits": Decimal("40.00"),
                    "min_courses": 10,
                    "display_order": 2,
                },
            )

            # Attach courses to groups
            rg_courses = []
            if not core_group.group_courses.exists():
                for c in all_courses[:20]:
                    rg_courses.append(
                        RequirementGroupCourse(
                            requirement_group=core_group,
                            course=c,
                            is_mandatory=True,
                        )
                    )
                for c in all_courses[20:100]:
                    rg_courses.append(
                        RequirementGroupCourse(
                            requirement_group=elective_group,
                            course=c,
                            is_mandatory=False,
                        )
                    )
                RequirementGroupCourse.objects.bulk_create(rg_courses, ignore_conflicts=True)

            # Publish version if not published
            if version.status != CurriculumStatus.PUBLISHED:
                version.status = CurriculumStatus.PUBLISHED
                version.save()

            # Seed Students and Transcript Entries
            grades = ["A", "A-", "B+", "B", "B-", "C+", "C"]
            records_created = 0
            transcripts_to_create = []

            for s_idx in range(1, num_students + 1):
                username = f"perf_student_{s_idx:04d}"
                user, _ = User.objects.get_or_create(
                    username=username,
                    defaults={
                        "email": f"{username}@perf.edu",
                        "first_name": "Perf",
                        "last_name": f"Student{s_idx}",
                    },
                )
                InstitutionMembership.objects.get_or_create(
                    institution=inst,
                    user=user,
                    role=Role.STUDENT,
                )
                rec, created = StudentRecord.objects.get_or_create(
                    institution=inst,
                    student=user,
                    defaults={
                        "programme": prog,
                        "pinned_curriculum": version,
                        "enrollment_term": term_fall,
                    },
                )
                if created:
                    records_created += 1
                    # Attach ~30-40 completed transcript entries
                    for c_idx, c in enumerate(all_courses[:35]):
                        transcripts_to_create.append(
                            TranscriptEntry(
                                institution=inst,
                                student_record=rec,
                                course=c,
                                term=term_fall if c_idx % 2 == 0 else term_spring,
                                grade=grades[c_idx % len(grades)],
                                credits_attempted=Decimal("4.00"),
                                credits_earned=Decimal("4.00"),
                                status=TranscriptEntryStatus.COMPLETED,
                                verification_status=VerificationStatus.VERIFIED,
                                attempt_number=1,
                            )
                        )

            if transcripts_to_create:
                TranscriptEntry.objects.bulk_create(transcripts_to_create, ignore_conflicts=True)

        elapsed = time.time() - start_t
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded performance data in {elapsed:.2f}s: "
                f"{len(all_courses)} courses, {num_students} students, "
                f"{len(transcripts_to_create)} transcript entries."
            )
        )
