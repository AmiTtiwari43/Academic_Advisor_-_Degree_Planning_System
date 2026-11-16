import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
import django
django.setup()

from decimal import Decimal
from django.contrib.auth.models import User
from django.utils import timezone
from institutions.models import Institution, Department
from accounts.models import Role, InstitutionMembership, AdvisorAssignment
from curriculum.models import (
    Course, Programme, CurriculumVersion, DegreeType, CurriculumStatus,
    RequirementGroup, RequirementGroupType, RequirementGroupCourse, PrerequisiteRule
)
from academic_records.models import (
    AcademicTerm, StudentRecord, TranscriptEntry, TranscriptEntryStatus, VerificationStatus
)
from planning.models import Plan, PlanItem, PlanStatus, PlanVersion, PlanVersionStatus
from career_mapping.models import (
    Skill, SkillCategory, ProficiencyLevel, CareerObjective,
    CareerSkillRequirement, CourseSkillMapping, StudentCareerPreference
)
from notifications.models import Notification, NotificationEventType, DeliveryStatus, ReadStatus

def seed_demo():
    print("--- Seeding Browser Demo Dataset ---")

    # 1. Institution
    inst, _ = Institution.objects.get_or_create(
        code="AGU",
        defaults={
            "name": "Antigravity University",
            "domain": "agu.edu",
            "is_active": True,
        }
    )
    inst.name = "Antigravity University"
    inst.domain = "agu.edu"
    inst.is_active = True
    inst.save()

    dept, _ = Department.objects.get_or_create(
        institution=inst,
        code="CS",
        defaults={"name": "Computer Science & Engineering"}
    )

    # 2. Terms
    terms = {}
    term_configs = [
        ("FA2026", "Fall 2026", "FALL", 2026, "2026-09-01", "2026-12-20"),
        ("SP2027", "Spring 2027", "SPRING", 2027, "2027-01-15", "2027-05-15"),
        ("FA2027", "Fall 2027", "FALL", 2027, "2027-09-01", "2027-12-20"),
        ("SP2028", "Spring 2028", "SPRING", 2028, "2028-01-15", "2028-05-15"),
    ]
    for code, name, season, year, start, end in term_configs:
        t, _ = AcademicTerm.objects.get_or_create(
            institution=inst,
            code=code,
            defaults={"name": name, "season": season, "year": year, "start_date": start, "end_date": end}
        )
        terms[code] = t

    # 3. Programme & Curriculum
    prog, _ = Programme.objects.get_or_create(
        institution=inst,
        code="CS-BS",
        defaults={
            "name": "Bachelor of Science in Computer Science",
            "department": "Computer Science & Engineering",
            "degree_type": DegreeType.BACHELOR,
            "is_active": True,
        }
    )

    curr_ver, _ = CurriculumVersion.objects.get_or_create(
        institution=inst,
        programme=prog,
        version_number=1,
        defaults={
            "status": CurriculumStatus.DRAFT,
            "academic_year": "2026-2027",
            "total_credits_required": Decimal("120.00"),
        }
    )

    # 4. Courses
    courses_data = [
        ("CS101", "Introduction to Programming", "4.00", None),
        ("CS201", "Data Structures & Algorithms", "4.00", {"schema_version": 1, "type": "course_completed", "course_code": "CS101", "min_grade": "C"}),
        ("CS301", "Operating Systems & Concurrency", "4.00", {"schema_version": 1, "type": "course_completed", "course_code": "CS201", "min_grade": "C"}),
        ("CS302", "Database Management Systems", "4.00", {"schema_version": 1, "type": "course_completed", "course_code": "CS201", "min_grade": "C"}),
        ("CS401", "Software Engineering Studio", "4.00", {"schema_version": 1, "type": "course_completed", "course_code": "CS201", "min_grade": "C"}),
        ("CS405", "Cloud Computing & DevOps", "4.00", {"schema_version": 1, "type": "course_completed", "course_code": "CS301", "min_grade": "C"}),
        ("MATH101", "Calculus I", "4.00", None),
        ("MATH102", "Calculus II", "4.00", {"schema_version": 1, "type": "course_completed", "course_code": "MATH101", "min_grade": "C"}),
        ("ENG101", "Academic Writing & Research", "3.00", None),
    ]

    courses = {}
    for code, title, credits, rule in courses_data:
        c, _ = Course.objects.get_or_create(
            institution=inst,
            code=code,
            defaults={"title": title, "credits": Decimal(credits)}
        )
        courses[code] = c

    # Requirement Groups & Prerequisite Rules (added while in DRAFT)
    if curr_ver.status == CurriculumStatus.DRAFT:
        core_group, _ = RequirementGroup.objects.get_or_create(
            institution=inst,
            curriculum_version=curr_ver,
            name="Computer Science Core",
            defaults={
                "group_type": RequirementGroupType.MANDATORY,
                "min_credits": Decimal("23.00"),
                "display_order": 1,
            }
        )
        core_codes = ["CS101", "CS201", "CS301", "MATH101", "MATH102", "ENG101"]
        for code in core_codes:
            RequirementGroupCourse.objects.get_or_create(
                requirement_group=core_group,
                course=courses[code],
                defaults={"is_mandatory": True}
            )

        elec_group, _ = RequirementGroup.objects.get_or_create(
            institution=inst,
            curriculum_version=curr_ver,
            name="CS Major Electives",
            defaults={
                "group_type": RequirementGroupType.ELECTIVE,
                "min_credits": Decimal("8.00"),
                "display_order": 2,
            }
        )
        elec_codes = ["CS302", "CS401", "CS405"]
        for code in elec_codes:
            RequirementGroupCourse.objects.get_or_create(
                requirement_group=elec_group,
                course=courses[code],
                defaults={"is_mandatory": False}
            )

        # Rules
        for code, title, credits, rule in courses_data:
            if rule:
                PrerequisiteRule.objects.get_or_create(
                    institution=inst,
                    curriculum_version=curr_ver,
                    course=courses[code],
                    defaults={"rule_json": rule}
                )

        curr_ver.status = CurriculumStatus.PUBLISHED
        curr_ver.published_at = timezone.now()
        curr_ver.save()

    # 5. Users: Student, Advisor, Coordinator
    def create_or_update_user(username, email, first, last, role_type, is_staff=False):
        u, _ = User.objects.get_or_create(
            username=username,
            defaults={"email": email, "first_name": first, "last_name": last}
        )
        u.set_password("DemoPass123!")
        u.email = email
        u.first_name = first
        u.last_name = last
        u.is_staff = is_staff
        u.is_active = True
        u.save()

        mem, _ = InstitutionMembership.objects.get_or_create(
            institution=inst,
            user=u,
            role=role_type,
            defaults={"is_active": True},
        )
        mem.is_active = True
        mem.save()
        return u, mem

    student_user, stu_mem = create_or_update_user("student_alex", "alex@agu.edu", "Alex", "Rivera", Role.STUDENT)
    advisor_user, adv_mem = create_or_update_user("advisor_alice", "alice@agu.edu", "Alice", "Chen", Role.ADVISOR, is_staff=True)
    coord_user, coord_mem = create_or_update_user("coordinator_cora", "cora@agu.edu", "Cora", "Vance", Role.COORDINATOR, is_staff=True)

    # 6. Student Record & Transcript
    stu_record, _ = StudentRecord.objects.get_or_create(
        institution=inst,
        student=student_user,
        defaults={
            "programme": prog,
            "pinned_curriculum": curr_ver,
            "enrollment_term": terms["FA2026"],
            "cached_cgpa": Decimal("3.80"),
            "cached_total_credits": Decimal("15.00"),
        }
    )
    stu_record.programme = prog
    stu_record.pinned_curriculum = curr_ver
    stu_record.save()

    # Advisor Assignment
    AdvisorAssignment.objects.get_or_create(
        institution=inst,
        advisor=adv_mem,
        student=stu_mem,
        defaults={"is_active": True}
    )

    # Transcripts for student_alex
    transcripts = [
        ("CS101", "FA2026", "A", "4.00"),
        ("MATH101", "FA2026", "B+", "4.00"),
        ("ENG101", "FA2026", "A-", "3.00"),
        ("CS201", "SP2027", "A", "4.00"),
    ]
    for c_code, term_code, grade, cr in transcripts:
        TranscriptEntry.objects.get_or_create(
            institution=inst,
            student_record=stu_record,
            course=courses[c_code],
            defaults={
                "term": terms[term_code],
                "grade": grade,
                "credits_attempted": Decimal(cr),
                "credits_earned": Decimal(cr),
                "status": TranscriptEntryStatus.COMPLETED,
                "verification_status": VerificationStatus.VERIFIED,
                "attempt_number": 1,
            }
        )

    # 7. Degree Plan for student_alex (Submitted for review)
    plan, _ = Plan.objects.get_or_create(
        institution=inst,
        student_record=stu_record,
        name="Alex's Graduation Plan",
        defaults={
            "curriculum_version": curr_ver,
            "is_primary": True,
            "status": PlanStatus.SUBMITTED,
        }
    )
    plan.status = PlanStatus.SUBMITTED
    plan.save()

    PlanItem.objects.filter(plan=plan).delete()
    PlanItem.objects.create(institution=inst, plan=plan, course=courses["CS301"], planned_term=terms["FA2027"], term_index=1, position=0)
    PlanItem.objects.create(institution=inst, plan=plan, course=courses["MATH102"], planned_term=terms["FA2027"], term_index=1, position=1)
    PlanItem.objects.create(institution=inst, plan=plan, course=courses["CS302"], planned_term=terms["SP2028"], term_index=2, position=0)
    PlanItem.objects.create(institution=inst, plan=plan, course=courses["CS401"], planned_term=terms["SP2028"], term_index=2, position=1)

    # Create PlanVersion snapshot
    plan_ver, _ = PlanVersion.objects.get_or_create(
        institution=inst,
        plan=plan,
        version_number=1,
        defaults={
            "status": PlanVersionStatus.SUBMITTED,
            "submitted_by": student_user,
            "submission_note": "Ready for official faculty review for Fall 2027 & Spring 2028.",
            "snapshot_data": {
                "plan_id": str(plan.id),
                "plan_name": plan.name,
                "student_username": student_user.username,
                "curriculum_version_number": 1,
                "items": [
                    {"course_code": "CS301", "course_title": "Operating Systems & Concurrency", "credits": "4.00", "term_code": "FA2027"},
                    {"course_code": "MATH102", "course_title": "Calculus II", "credits": "4.00", "term_code": "FA2027"},
                    {"course_code": "CS302", "course_title": "Database Management Systems", "credits": "4.00", "term_code": "SP2028"},
                    {"course_code": "CS401", "course_title": "Software Engineering Studio", "credits": "4.00", "term_code": "SP2028"},
                ],
                "simulation": {
                    "is_valid_for_submission": True,
                    "total_planned_credits": "16.00",
                    "total_cumulative_credits": "31.00",
                    "projected_graduation_term": "SP2028",
                    "hard_constraints": [],
                    "warnings": [],
                }
            }
        }
    )

    # 8. Career Objectives & Skills
    sk_python, _ = Skill.objects.get_or_create(
        institution=inst,
        code="PYTHON_PROG",
        defaults={"name": "Python Programming", "category": SkillCategory.TECHNICAL, "description": "Core software development in Python"}
    )
    sk_dist, _ = Skill.objects.get_or_create(
        institution=inst,
        code="DISTRIBUTED_SYS",
        defaults={"name": "Distributed Systems", "category": SkillCategory.TECHNICAL, "description": "Consensus, RPC, microservices architecture"}
    )
    sk_cloud, _ = Skill.objects.get_or_create(
        institution=inst,
        code="CLOUD_DEV",
        defaults={"name": "Cloud Infrastructure & DevOps", "category": SkillCategory.TOOL, "description": "Docker, Kubernetes, AWS/GCP pipelines"}
    )

    # Course Skills
    CourseSkillMapping.objects.get_or_create(
        institution=inst, course=courses["CS101"], skill=sk_python,
        defaults={"proficiency_level": ProficiencyLevel.INTERMEDIATE, "coverage_weight": Decimal("0.90")}
    )
    CourseSkillMapping.objects.get_or_create(
        institution=inst, course=courses["CS301"], skill=sk_dist,
        defaults={"proficiency_level": ProficiencyLevel.ADVANCED, "coverage_weight": Decimal("0.85")}
    )
    CourseSkillMapping.objects.get_or_create(
        institution=inst, course=courses["CS405"], skill=sk_cloud,
        defaults={"proficiency_level": ProficiencyLevel.ADVANCED, "coverage_weight": Decimal("0.95")}
    )

    # Objective
    career_obj, _ = CareerObjective.objects.get_or_create(
        institution=inst,
        code="SWE_CLOUD",
        defaults={
            "title": "Cloud Software Engineer",
            "description": "Builds and scales cloud-native distributed microservices.",
            "is_active": True,
        }
    )
    CareerSkillRequirement.objects.get_or_create(
        career_objective=career_obj, skill=sk_python,
        defaults={"min_proficiency": ProficiencyLevel.ADVANCED, "is_critical": True, "display_order": 1}
    )
    CareerSkillRequirement.objects.get_or_create(
        career_objective=career_obj, skill=sk_dist,
        defaults={"min_proficiency": ProficiencyLevel.INTERMEDIATE, "is_critical": True, "display_order": 2}
    )
    CareerSkillRequirement.objects.get_or_create(
        career_objective=career_obj, skill=sk_cloud,
        defaults={"min_proficiency": ProficiencyLevel.INTERMEDIATE, "is_critical": False, "display_order": 3}
    )

    # Student Preference
    StudentCareerPreference.objects.get_or_create(
        institution=inst,
        student_record=stu_record,
        career_objective=career_obj,
        defaults={"priority": 1, "target_term": terms["SP2028"], "notes": "Targeting cloud infrastructure engineering roles"}
    )

    # 9. Notifications
    Notification.objects.get_or_create(
        institution=inst,
        recipient=advisor_user,
        event_type=NotificationEventType.PLAN_SUBMITTED,
        deduplication_key=f"demo-plan-sub-{plan.id}",
        defaults={
            "subject": "New Degree Plan Submitted for Review",
            "preview": "Alex Rivera has submitted their graduation plan for review.",
            "delivery_status": DeliveryStatus.DELIVERED,
            "read_status": ReadStatus.UNREAD,
        }
    )
    Notification.objects.get_or_create(
        institution=inst,
        recipient=student_user,
        event_type=NotificationEventType.ADVISOR_QUEUE_SUMMARY,
        deduplication_key=f"demo-welcome-{student_user.id}",
        defaults={
            "subject": "Academic Term Registration Open",
            "preview": "Registration for upcoming academic terms is now open. Verify your degree plan.",
            "delivery_status": DeliveryStatus.DELIVERED,
            "read_status": ReadStatus.UNREAD,
        }
    )

    print("--- Demo Dataset Successfully Seeded! ---")
    print("Institution: Antigravity University (AGU)")
    print("Credentials (Password for all accounts: DemoPass123!):")
    print("  Student:     student_alex     (Role: STUDENT)")
    print("  Advisor:     advisor_alice    (Role: FACULTY_ADVISOR)")
    print("  Coordinator: coordinator_cora (Role: COORDINATOR)")

if __name__ == "__main__":
    seed_demo()
