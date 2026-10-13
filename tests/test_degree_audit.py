from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APIClient

from academic_records.models import (
    AcademicTerm,
    Exemption,
    RepeatedCoursePolicy,
    StudentRecord,
    TranscriptEntry,
    TranscriptEntryStatus,
    TransferCredit,
    VerificationStatus,
)
from academic_records.services.context_builder import build_rule_context
from accounts.models import AdvisorAssignment, InstitutionMembership, Role
from curriculum.models import (
    Course,
    CurriculumStatus,
    CurriculumVersion,
    DegreeType,
    PrerequisiteRule,
    Programme,
    RequirementGroup,
    RequirementGroupCourse,
    RequirementGroupType,
)
from degree_audit.services import run_degree_audit
from eligibility.services import check_course_eligibility
from institutions.models import Institution
from rule_engine.core import evaluate_rule


@pytest.fixture
def audit_environment():
    inst = Institution.objects.create(code="AUDIT_U", name="Audit University", domain="audit.edu")
    other_inst = Institution.objects.create(code="OTHER_U", name="Other University", domain="other.edu")

    term_f26 = AcademicTerm.objects.create(
        institution=inst,
        code="FA2026",
        name="Fall 2026",
        season="FALL",
        year=2026,
        start_date="2026-09-01",
        end_date="2026-12-20",
    )
    term_s27 = AcademicTerm.objects.create(
        institution=inst,
        code="SP2027",
        name="Spring 2027",
        season="SPRING",
        year=2027,
        start_date="2027-01-15",
        end_date="2027-05-15",
    )

    prog = Programme.objects.create(
        institution=inst,
        code="BS_CS",
        name="Bachelor of Science in CS",
        degree_type=DegreeType.BACHELOR,
        department="Computer Science",
    )

    version = CurriculumVersion.objects.create(
        institution=inst,
        programme=prog,
        version_number=1,
        academic_year="2026-2027",
        status=CurriculumStatus.DRAFT,
        total_credits_required=Decimal("20.00"),
        min_cgpa_required=Decimal("2.00"),
    )

    # Courses
    cs101 = Course.objects.create(institution=inst, code="CS101", title="Intro to CS", credits=Decimal("4.00"))
    cs102 = Course.objects.create(institution=inst, code="CS102", title="Data Structures", credits=Decimal("4.00"))
    cs201 = Course.objects.create(institution=inst, code="CS201", title="Algorithms", credits=Decimal("4.00"))
    math101 = Course.objects.create(institution=inst, code="MATH101", title="Calculus I", credits=Decimal("4.00"))
    math102 = Course.objects.create(institution=inst, code="MATH102", title="Calculus II", credits=Decimal("4.00"))
    gen101 = Course.objects.create(institution=inst, code="GEN101", title="Writing", credits=Decimal("4.00"))

    # Requirement Groups
    core_group = RequirementGroup.objects.create(
        institution=inst,
        curriculum_version=version,
        name="Major Core",
        group_type=RequirementGroupType.MANDATORY,
        min_credits=Decimal("8.00"),
        min_courses=2,
        display_order=1,
    )
    RequirementGroupCourse.objects.create(requirement_group=core_group, course=cs101, is_mandatory=True)
    RequirementGroupCourse.objects.create(requirement_group=core_group, course=cs102, is_mandatory=True)

    math_group = RequirementGroup.objects.create(
        institution=inst,
        curriculum_version=version,
        name="Math Requirements",
        group_type=RequirementGroupType.MANDATORY,
        min_credits=Decimal("8.00"),
        min_courses=2,
        min_cgpa=Decimal("2.50"),
        display_order=2,
    )
    RequirementGroupCourse.objects.create(requirement_group=math_group, course=math101, is_mandatory=True)
    RequirementGroupCourse.objects.create(requirement_group=math_group, course=math102, is_mandatory=True)

    elective_group = RequirementGroup.objects.create(
        institution=inst,
        curriculum_version=version,
        name="Major Electives",
        group_type=RequirementGroupType.ELECTIVE,
        min_credits=Decimal("4.00"),
        min_courses=1,
        display_order=3,
    )
    RequirementGroupCourse.objects.create(requirement_group=elective_group, course=cs201, is_mandatory=False)
    # Also attach cs102 to elective group to test double-counting prevention!
    RequirementGroupCourse.objects.create(requirement_group=elective_group, course=cs102, is_mandatory=False)

    # Prerequisite Rule: CS102 requires CS101 with min grade C
    rule_cs102 = {
        "schema_version": 1,
        "type": "course_completed",
        "course_code": "CS101",
        "min_grade": "C",
    }
    PrerequisiteRule.objects.create(
        institution=inst,
        curriculum_version=version,
        course=cs102,
        rule_json=rule_cs102,
    )

    # Publish version so students can be pinned to it
    version.status = CurriculumStatus.PUBLISHED
    version.save()

    # Users
    student_user = User.objects.create_user("student_bob", "bob@audit.edu", "pass123")
    InstitutionMembership.objects.create(institution=inst, user=student_user, role=Role.STUDENT)

    advisor_user = User.objects.create_user("advisor_carol", "carol@audit.edu", "pass123")
    adv_mem = InstitutionMembership.objects.create(institution=inst, user=advisor_user, role=Role.ADVISOR)

    coordinator_user = User.objects.create_user("coord_dan", "dan@audit.edu", "pass123")
    InstitutionMembership.objects.create(institution=inst, user=coordinator_user, role=Role.COORDINATOR)

    # Assign advisor_carol to student_bob
    stu_mem = InstitutionMembership.objects.get(institution=inst, user=student_user)
    AdvisorAssignment.objects.create(institution=inst, advisor=adv_mem, student=stu_mem)

    # Student Record
    record = StudentRecord.objects.create(
        institution=inst,
        student=student_user,
        programme=prog,
        pinned_curriculum=version,
        enrollment_term=term_f26,
    )

    return {
        "inst": inst,
        "other_inst": other_inst,
        "term_f26": term_f26,
        "term_s27": term_s27,
        "version": version,
        "courses": {
            "cs101": cs101,
            "cs102": cs102,
            "cs201": cs201,
            "math101": math101,
            "math102": math102,
            "gen101": gen101,
        },
        "groups": {
            "core": core_group,
            "math": math_group,
            "elective": elective_group,
        },
        "users": {
            "student": student_user,
            "advisor": advisor_user,
            "coordinator": coordinator_user,
        },
        "record": record,
    }


@pytest.mark.django_db
class TestDegreeAuditScenarios:
    def test_scenario_01_full_degree_completion(self, audit_environment):
        """Scenario 1: Completed all mandatory & elective courses with high grades -> Degree fully satisfied."""
        env = audit_environment
        rec = env["record"]
        c = env["courses"]
        term = env["term_f26"]


        # Complete all: CS101(4), CS102(4), MATH101(4), MATH102(4), CS201(4) = 20 credits
        courses = [c["cs101"], c["cs102"], c["math101"], c["math102"], c["cs201"]]
        for crs in courses:
            TranscriptEntry.objects.create(
                institution=env["inst"],
                student_record=rec,
                course=crs,
                term=term,
                grade="A",
                credits_attempted=Decimal("4.00"),
                credits_earned=Decimal("4.00"),
                status=TranscriptEntryStatus.COMPLETED,
                verification_status=VerificationStatus.VERIFIED,
            )

        report = run_degree_audit(rec)

        assert report.is_credits_satisfied is True
        assert report.is_cgpa_satisfied is True
        assert report.is_degree_satisfied is True
        assert report.total_credits_earned == Decimal("20.00")
        assert report.overall_cgpa == Decimal("4.00")
        for g in report.groups:
            assert g.is_satisfied is True

    def test_scenario_02_mandatory_course_shortfall(self, audit_environment):
        """Scenario 2: Missing mandatory course CS102 -> Core group unsatisfied, remaining mandatory listed."""
        env = audit_environment
        rec = env["record"]
        c = env["courses"]
        term = env["term_f26"]

        # Only complete CS101, missing CS102
        TranscriptEntry.objects.create(
            institution=env["inst"],
            student_record=rec,
            course=c["cs101"],
            term=term,
            grade="B",
            credits_attempted=Decimal("4.00"),
            credits_earned=Decimal("4.00"),
            status=TranscriptEntryStatus.COMPLETED,
            verification_status=VerificationStatus.VERIFIED,
        )

        report = run_degree_audit(rec)

        core_audit = next(g for g in report.groups if g.name == "Major Core")
        assert core_audit.is_satisfied is False
        assert len(core_audit.remaining_mandatory_courses) == 1
        assert core_audit.remaining_mandatory_courses[0]["course_code"] == "CS102"
        assert report.is_degree_satisfied is False

    def test_scenario_03_elective_credits_shortfall(self, audit_environment):
        """Scenario 3: Major Electives requires 4.0 cr, none completed -> Elective group unsatisfied."""
        env = audit_environment
        rec = env["record"]
        c = env["courses"]
        term = env["term_f26"]

        # Complete Core and Math, but NO Electives
        for crs in [c["cs101"], c["cs102"], c["math101"], c["math102"]]:
            TranscriptEntry.objects.create(
                institution=env["inst"],
                student_record=rec,
                course=crs,
                term=term,
                grade="A",
                credits_attempted=Decimal("4.00"),
                credits_earned=Decimal("4.00"),
                status=TranscriptEntryStatus.COMPLETED,
                verification_status=VerificationStatus.VERIFIED,
            )

        report = run_degree_audit(rec)

        elec_audit = next(g for g in report.groups if g.name == "Major Electives")
        assert elec_audit.is_satisfied is False
        assert elec_audit.remaining_credits == Decimal("4.00")
        assert report.is_degree_satisfied is False

    def test_scenario_04_cgpa_below_minimum_threshold(self, audit_environment):
        """Scenario 4: Completed all courses but CGPA is 1.0 (D grades), below 2.0 required -> Degree unsatisfied."""
        env = audit_environment
        rec = env["record"]
        c = env["courses"]
        term = env["term_f26"]

        # Complete courses with D (1.0 grade points)
        for crs in [c["cs101"], c["cs102"], c["math101"], c["math102"], c["cs201"]]:
            TranscriptEntry.objects.create(
                institution=env["inst"],
                student_record=rec,
                course=crs,
                term=term,
                grade="D",
                credits_attempted=Decimal("4.00"),
                credits_earned=Decimal("4.00"),
                status=TranscriptEntryStatus.COMPLETED,
                verification_status=VerificationStatus.VERIFIED,
            )

        report = run_degree_audit(rec)

        assert report.overall_cgpa == Decimal("1.00")
        assert report.is_cgpa_satisfied is False
        assert report.is_degree_satisfied is False

    def test_scenario_05_repeated_course_best_grade_policy(self, audit_environment):
        """Scenario 5: Repeated course with BEST_GRADE policy: attempt 1=F, attempt 2=A -> selects A, 4 cr earned once."""
        env = audit_environment
        rec = env["record"]
        c = env["courses"]
        rec.repeated_course_policy = RepeatedCoursePolicy.BEST_GRADE
        rec.save()

        # Attempt 1: Failed
        TranscriptEntry.objects.create(
            institution=env["inst"],
            student_record=rec,
            course=c["cs101"],
            term=env["term_f26"],
            grade="F",
            credits_attempted=Decimal("4.00"),
            credits_earned=Decimal("0.00"),
            status=TranscriptEntryStatus.FAILED,
            attempt_number=1,
            verification_status=VerificationStatus.VERIFIED,
        )
        # Attempt 2: A
        TranscriptEntry.objects.create(
            institution=env["inst"],
            student_record=rec,
            course=c["cs101"],
            term=env["term_s27"],
            grade="A",
            credits_attempted=Decimal("4.00"),
            credits_earned=Decimal("4.00"),
            status=TranscriptEntryStatus.COMPLETED,
            attempt_number=2,
            verification_status=VerificationStatus.VERIFIED,
        )

        report = run_degree_audit(rec)

        # Total earned credits should be 4.00 (not 8.00)
        assert report.total_credits_earned == Decimal("4.00")
        assert report.overall_cgpa == Decimal("4.00")

    def test_scenario_06_repeated_course_latest_grade_policy(self, audit_environment):
        """Scenario 6: Repeated course with LATEST_GRADE policy: attempt 1=A (term 1), attempt 2=C (term 2) -> selects C (2.00)."""
        env = audit_environment
        rec = env["record"]
        c = env["courses"]
        rec.repeated_course_policy = RepeatedCoursePolicy.LATEST_GRADE
        rec.save()

        TranscriptEntry.objects.create(
            institution=env["inst"],
            student_record=rec,
            course=c["cs101"],
            term=env["term_f26"],
            grade="A",
            credits_attempted=Decimal("4.00"),
            credits_earned=Decimal("4.00"),
            status=TranscriptEntryStatus.COMPLETED,
            attempt_number=1,
            verification_status=VerificationStatus.VERIFIED,
        )
        TranscriptEntry.objects.create(
            institution=env["inst"],
            student_record=rec,
            course=c["cs101"],
            term=env["term_s27"],
            grade="C",
            credits_attempted=Decimal("4.00"),
            credits_earned=Decimal("4.00"),
            status=TranscriptEntryStatus.COMPLETED,
            attempt_number=2,
            verification_status=VerificationStatus.VERIFIED,
        )

        report = run_degree_audit(rec)

        assert report.total_credits_earned == Decimal("4.00")
        assert report.overall_cgpa == Decimal("2.00")

    def test_scenario_07_in_progress_never_counted_as_earned(self, audit_environment):
        """Scenario 7: IN_PROGRESS entry provides in_progress_credits but NEVER earned_credits."""
        env = audit_environment
        rec = env["record"]
        c = env["courses"]

        TranscriptEntry.objects.create(
            institution=env["inst"],
            student_record=rec,
            course=c["cs101"],
            term=env["term_f26"],
            grade="",
            credits_attempted=Decimal("4.00"),
            credits_earned=Decimal("0.00"),
            status=TranscriptEntryStatus.IN_PROGRESS,
            verification_status=VerificationStatus.VERIFIED,
        )

        report = run_degree_audit(rec)

        assert report.total_credits_earned == Decimal("0.00")
        assert report.total_credits_in_progress == Decimal("4.00")
        core_audit = next(g for g in report.groups if g.name == "Major Core")
        assert core_audit.earned_credits == Decimal("0.00")
        assert core_audit.in_progress_credits == Decimal("4.00")
        assert core_audit.is_satisfied is False

    def test_scenario_08_unverified_entries_never_counted(self, audit_environment):
        """Scenario 8: UNVERIFIED transcript entries are completely ignored from audit and CGPA."""
        env = audit_environment
        rec = env["record"]
        c = env["courses"]

        TranscriptEntry.objects.create(
            institution=env["inst"],
            student_record=rec,
            course=c["cs101"],
            term=env["term_f26"],
            grade="A",
            credits_attempted=Decimal("4.00"),
            credits_earned=Decimal("4.00"),
            status=TranscriptEntryStatus.COMPLETED,
            verification_status=VerificationStatus.UNVERIFIED,
        )

        report = run_degree_audit(rec)

        assert report.total_credits_earned == Decimal("0.00")
        assert report.overall_cgpa == Decimal("0.00")
        core_audit = next(g for g in report.groups if g.name == "Major Core")
        assert core_audit.is_satisfied is False

    def test_scenario_09_transfer_credits_fulfill_requirements(self, audit_environment):
        """Scenario 9: Verified transfer credit satisfies requirement without affecting CGPA."""
        env = audit_environment
        rec = env["record"]

        TransferCredit.objects.create(
            institution=env["inst"],
            student_record=rec,
            course_code="CS101",
            source_institution="Community College",
            credits=Decimal("4.00"),
            grade="CR",
            is_verified=True,
        )

        report = run_degree_audit(rec)

        assert report.total_credits_earned == Decimal("4.00")
        assert report.overall_cgpa == Decimal("0.00")  # Transfer credits do not affect GPA
        core_audit = next(g for g in report.groups if g.name == "Major Core")
        assert any(c["course_code"] == "CS101" for c in core_audit.allocated_courses)

    def test_scenario_10_course_exemption_waives_mandatory_slot(self, audit_environment):
        """Scenario 10: Exemption waives mandatory CS101 requirement (0 remaining mandatory)."""
        env = audit_environment
        rec = env["record"]
        c = env["courses"]

        Exemption.objects.create(
            institution=env["inst"],
            student_record=rec,
            course=c["cs101"],
            reason="Prior professional experience approved by dean",
            approved_by=env["users"]["coordinator"],
        )

        report = run_degree_audit(rec)

        core_audit = next(g for g in report.groups if g.name == "Major Core")
        # CS101 was waived, so only CS102 remains mandatory
        remaining_codes = [m["course_code"] for m in core_audit.remaining_mandatory_courses]
        assert "CS101" not in remaining_codes
        assert "CS102" in remaining_codes
        assert any(c["course_code"] == "CS101" and c["status"] == "EXEMPTED" for c in core_audit.allocated_courses)

    def test_scenario_11_no_double_counting_across_groups(self, audit_environment):
        """Scenario 11: CS102 is attached to both Core and Electives. It satisfies Core, cannot also satisfy Electives."""
        env = audit_environment
        rec = env["record"]
        c = env["courses"]

        # Complete CS101 and CS102
        for crs in [c["cs101"], c["cs102"]]:
            TranscriptEntry.objects.create(
                institution=env["inst"],
                student_record=rec,
                course=crs,
                term=env["term_f26"],
                grade="A",
                credits_attempted=Decimal("4.00"),
                credits_earned=Decimal("4.00"),
                status=TranscriptEntryStatus.COMPLETED,
                verification_status=VerificationStatus.VERIFIED,
            )

        report = run_degree_audit(rec)

        core_audit = next(g for g in report.groups if g.name == "Major Core")
        elec_audit = next(g for g in report.groups if g.name == "Major Electives")

        assert core_audit.is_satisfied is True
        # CS102 cannot be double-counted to satisfy Major Electives!
        assert elec_audit.is_satisfied is False
        assert elec_audit.earned_credits == Decimal("0.00")


@pytest.mark.django_db
class TestEligibilityEngineParity:
    def test_eligibility_service_matches_pure_python_engine(self, audit_environment):
        """Asserts that check_course_eligibility produces exact same verdict as direct evaluate_rule."""
        env = audit_environment
        rec = env["record"]
        cs102 = env["courses"]["cs102"]
        cs101 = env["courses"]["cs101"]

        # Case A: Without CS101 -> Unsatisfied
        result_a = check_course_eligibility(rec, cs102)
        assert result_a.eligible is False
        assert result_a.status == "UNSATISFIED"
        assert len(result_a.blocking_reasons) > 0

        # Direct pure-Python engine call
        rule = PrerequisiteRule.objects.get(course=cs102, curriculum_version=rec.pinned_curriculum)
        ctx_a = build_rule_context(rec)
        engine_res_a = evaluate_rule(rule.rule_json, ctx_a)
        assert result_a.eligible == engine_res_a.eligible
        assert result_a.status == engine_res_a.status.value
        assert result_a.blocking_reasons == list(engine_res_a.blocking_reasons)

        # Case B: With CS101 completed with grade B -> Satisfied
        TranscriptEntry.objects.create(
            institution=env["inst"],
            student_record=rec,
            course=cs101,
            term=env["term_f26"],
            grade="B",
            credits_attempted=Decimal("4.00"),
            credits_earned=Decimal("4.00"),
            status=TranscriptEntryStatus.COMPLETED,
            verification_status=VerificationStatus.VERIFIED,
        )

        result_b = check_course_eligibility(rec, cs102)
        ctx_b = build_rule_context(rec)
        engine_res_b = evaluate_rule(rule.rule_json, ctx_b)

        assert result_b.eligible is True
        assert result_b.status == "SATISFIED"
        assert result_b.eligible == engine_res_b.eligible
        assert result_b.status == engine_res_b.status.value


@pytest.mark.django_db
class TestAcademicRecordsPermissionsAndIsolation:
    def test_student_can_only_view_own_record(self, audit_environment):
        env = audit_environment
        client = APIClient()

        # Student Bob logs in
        client.force_authenticate(user=env["users"]["student"])
        response = client.get(f"/api/v1/student-records/{env['record'].id}/")
        assert response.status_code == status.HTTP_200_OK

        # Another student Eve created
        eve = User.objects.create_user("student_eve", "eve@audit.edu", "pass123")
        InstitutionMembership.objects.create(institution=env["inst"], user=eve, role=Role.STUDENT)
        rec_eve = StudentRecord.objects.create(
            institution=env["inst"],
            student=eve,
            programme=env["record"].programme,
            pinned_curriculum=env["version"],
            enrollment_term=env["term_f26"],
        )

        # Bob attempts to view Eve's record -> 404 (zero existence leakage)
        res_cross_student = client.get(f"/api/v1/student-records/{rec_eve.id}/")
        assert res_cross_student.status_code == status.HTTP_404_NOT_FOUND

    def test_advisor_sees_assigned_student_denied_unassigned(self, audit_environment):
        env = audit_environment
        client = APIClient()

        # Advisor Carol logs in
        client.force_authenticate(user=env["users"]["advisor"])

        # Carol is assigned to Bob -> 200 OK
        res_assigned = client.get(f"/api/v1/student-records/{env['record'].id}/")
        assert res_assigned.status_code == status.HTTP_200_OK

        # Unassigned student Frank created
        frank = User.objects.create_user("student_frank", "frank@audit.edu", "pass123")
        InstitutionMembership.objects.create(institution=env["inst"], user=frank, role=Role.STUDENT)
        rec_frank = StudentRecord.objects.create(
            institution=env["inst"],
            student=frank,
            programme=env["record"].programme,
            pinned_curriculum=env["version"],
            enrollment_term=env["term_f26"],
        )

        # Carol attempts to view unassigned Frank -> 404
        res_unassigned = client.get(f"/api/v1/student-records/{rec_frank.id}/")
        assert res_unassigned.status_code == status.HTTP_404_NOT_FOUND

    def test_cross_institution_isolation(self, audit_environment):
        env = audit_environment
        client = APIClient()

        foreign_user = User.objects.create_user("foreign_coord", "foreign@other.edu", "pass123")
        InstitutionMembership.objects.create(institution=env["other_inst"], user=foreign_user, role=Role.COORDINATOR)

        client.force_authenticate(user=foreign_user)
        # Attempt to access student record from AUDIT_U -> 404
        response = client.get(f"/api/v1/student-records/{env['record'].id}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_api_audit_and_eligibility_endpoints(self, audit_environment):
        env = audit_environment
        client = APIClient()
        client.force_authenticate(user=env["users"]["student"])

        # Test audit endpoint
        audit_res = client.get(f"/api/v1/student-records/{env['record'].id}/audit/")
        assert audit_res.status_code == status.HTTP_200_OK
        data = audit_res.json()
        assert "is_degree_satisfied" in data
        assert "total_credits_earned" in data
        assert len(data["groups"]) == 3

        # Test eligibility endpoint
        cs102_id = env["courses"]["cs102"].id
        elig_res = client.get(f"/api/v1/student-records/{env['record'].id}/eligibility/{cs102_id}/")
        assert elig_res.status_code == status.HTTP_200_OK
        elig_data = elig_res.json()
        assert "eligible" in elig_data
        assert "status" in elig_data
