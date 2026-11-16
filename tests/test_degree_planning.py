from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APIClient

from academic_records.models import (
    AcademicTerm,
    StudentRecord,
    TranscriptEntry,
    TranscriptEntryStatus,
    VerificationStatus,
)
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
from institutions.models import Institution
from planning.models import (
    PlanStatus,
    PlanVersionImmutabilityError,
    PlanVersionStatus,
)
from planning.services.plan_management_service import (
    PlanConcurrencyError,
    PlanValidationError,
    add_course_to_plan,
    create_plan,
    move_course_in_plan,
    update_plan,
)
from planning.services.simulation_service import simulate_plan
from planning.services.snapshot_service import (
    create_plan_version_snapshot,
)
from planning.services.what_if_service import simulate_what_if


@pytest.fixture
def planning_environment():
    inst = Institution.objects.create(name="Planning Institute", code="PLAN_U", domain="plan.edu")
    other_inst = Institution.objects.create(name="Other Institute", code="OTHER_U", domain="otherplan.edu")

    # Academic Terms
    term_f26 = AcademicTerm.objects.create(
        institution=inst,
        code="FA2026",
        name="Fall 2026",
        season="FALL",
        year=2026,
        start_date="2026-08-25",
        end_date="2026-12-15",
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
    term_f27 = AcademicTerm.objects.create(
        institution=inst,
        code="FA2027",
        name="Fall 2027",
        season="FALL",
        year=2027,
        start_date="2027-08-25",
        end_date="2027-12-15",
    )

    prog = Programme.objects.create(
        institution=inst,
        code="BS_CS",
        name="Bachelor of Science in Computer Science",
        degree_type=DegreeType.BACHELOR,
    )

    other_prog = Programme.objects.create(
        institution=inst,
        code="BS_DS",
        name="Bachelor of Science in Data Science",
        degree_type=DegreeType.BACHELOR,
    )

    # CS Curriculum Version
    ver_cs = CurriculumVersion.objects.create(
        institution=inst,
        programme=prog,
        version_number=1,
        academic_year="2026-2027",
        status=CurriculumStatus.DRAFT,
        total_credits_required=Decimal("16.00"),
        min_cgpa_required=Decimal("5.00"),
    )

    # Courses
    cs101 = Course.objects.create(institution=inst, code="CS101", title="Intro to CS", credits=Decimal("4.00"))
    cs102 = Course.objects.create(institution=inst, code="CS102", title="Data Structures", credits=Decimal("4.00"))
    cs201 = Course.objects.create(institution=inst, code="CS201", title="Algorithms", credits=Decimal("4.00"))
    math101 = Course.objects.create(institution=inst, code="MATH101", title="Calculus I", credits=Decimal("4.00"))
    outside_crs = Course.objects.create(institution=inst, code="PHYS101", title="Physics", credits=Decimal("4.00"))

    # Requirement Groups
    core_group = RequirementGroup.objects.create(
        institution=inst,
        curriculum_version=ver_cs,
        name="Major Core",
        group_type=RequirementGroupType.MANDATORY,
        min_credits=Decimal("12.00"),
        min_courses=3,
        display_order=1,
    )
    RequirementGroupCourse.objects.create(requirement_group=core_group, course=cs101, is_mandatory=True)
    RequirementGroupCourse.objects.create(requirement_group=core_group, course=cs102, is_mandatory=True)
    RequirementGroupCourse.objects.create(requirement_group=core_group, course=cs201, is_mandatory=True)

    math_group = RequirementGroup.objects.create(
        institution=inst,
        curriculum_version=ver_cs,
        name="Math Core",
        group_type=RequirementGroupType.MANDATORY,
        min_credits=Decimal("4.00"),
        min_courses=1,
        display_order=2,
    )
    RequirementGroupCourse.objects.create(requirement_group=math_group, course=math101, is_mandatory=True)

    # Prerequisite: CS102 requires CS101
    PrerequisiteRule.objects.create(
        institution=inst,
        curriculum_version=ver_cs,
        course=cs102,
        rule_json={"schema_version": 1, "type": "course_completed", "course_code": "CS101", "min_grade": "C"},
    )
    # Prerequisite: CS201 requires CS102
    PrerequisiteRule.objects.create(
        institution=inst,
        curriculum_version=ver_cs,
        course=cs201,
        rule_json={"schema_version": 1, "type": "course_completed", "course_code": "CS102", "min_grade": "C"},
    )

    ver_cs.status = CurriculumStatus.PUBLISHED
    ver_cs.save()

    # Data Science Alternative Curriculum Version for What-If Testing
    ver_ds = CurriculumVersion.objects.create(
        institution=inst,
        programme=other_prog,
        version_number=1,
        academic_year="2026-2027",
        status=CurriculumStatus.DRAFT,
        total_credits_required=Decimal("12.00"),
        min_cgpa_required=Decimal("6.00"),
    )
    ds_group = RequirementGroup.objects.create(
        institution=inst,
        curriculum_version=ver_ds,
        name="Data Science Core",
        group_type=RequirementGroupType.MANDATORY,
        min_credits=Decimal("8.00"),
        min_courses=2,
        display_order=1,
    )
    RequirementGroupCourse.objects.create(requirement_group=ds_group, course=cs101, is_mandatory=True)
    RequirementGroupCourse.objects.create(requirement_group=ds_group, course=math101, is_mandatory=True)
    ver_ds.status = CurriculumStatus.PUBLISHED
    ver_ds.save()

    # Users
    student_user = User.objects.create_user("student_alice", "alice@plan.edu", "pass123")
    student_mem = InstitutionMembership.objects.create(institution=inst, user=student_user, role=Role.STUDENT)

    advisor_user = User.objects.create_user("advisor_dan", "dan@plan.edu", "pass123")
    adv_mem = InstitutionMembership.objects.create(institution=inst, user=advisor_user, role=Role.ADVISOR)

    unassigned_advisor = User.objects.create_user("advisor_stranger", "stranger@plan.edu", "pass123")
    InstitutionMembership.objects.create(institution=inst, user=unassigned_advisor, role=Role.ADVISOR)

    other_inst_user = User.objects.create_user("other_user", "other@otherplan.edu", "pass123")
    InstitutionMembership.objects.create(institution=other_inst, user=other_inst_user, role=Role.STUDENT)

    # Assign Advisor Dan to Alice
    AdvisorAssignment.objects.create(
        institution=inst,
        advisor=adv_mem,
        student=student_mem,
        is_active=True,
    )

    # Student Record
    record = StudentRecord.objects.create(
        institution=inst,
        student=student_user,
        programme=prog,
        pinned_curriculum=ver_cs,
        enrollment_term=term_f26,
    )

    return {
        "inst": inst,
        "other_inst": other_inst,
        "terms": {
            "f26": term_f26,
            "s27": term_s27,
            "f27": term_f27,
        },
        "version_cs": ver_cs,
        "version_ds": ver_ds,
        "courses": {
            "cs101": cs101,
            "cs102": cs102,
            "cs201": cs201,
            "math101": math101,
            "outside": outside_crs,
        },
        "users": {
            "student": student_user,
            "advisor": advisor_user,
            "unassigned_advisor": unassigned_advisor,
            "other_inst_user": other_inst_user,
        },
        "record": record,
    }


@pytest.mark.django_db
class TestDegreePlanningAndSimulation:
    def test_plan_lifecycle_and_zero_record_mutations(self, planning_environment):
        """
        Lifecycle: create plan -> add courses with missing prereq -> simulate (infeasible) ->
        fix schedule -> simulate (feasible) -> submit version -> assert official records untouched.
        """
        env = planning_environment
        rec = env["record"]
        c = env["courses"]
        t = env["terms"]
        user = env["users"]["student"]

        # Snapshot before starting
        transcript_count_before = TranscriptEntry.objects.filter(student_record=rec).count()
        rec_credits_before = rec.cached_total_credits
        rec_pinned_curriculum_before = rec.pinned_curriculum_id

        # 1. Create draft plan
        plan = create_plan(student_record=rec, name="Alice 4-Year Plan", is_primary=True)
        assert plan.status == PlanStatus.DRAFT
        assert plan.row_version == 1

        # 2. Add courses out of order: CS102 in Term 1 (Missing CS101 prerequisite!)
        item_cs102 = add_course_to_plan(plan, c["cs102"], t["f26"], term_index=1)
        assert plan.row_version == 2

        # 3. Simulate plan -> Infeasible with named prerequisite deficiency
        sim_1 = simulate_plan(plan)
        assert sim_1.is_valid_for_submission is False
        assert len(sim_1.hard_constraints) > 0
        assert sim_1.hard_constraints[0].code == "PREREQUISITE_UNSATISFIED"
        assert "CS101" in sim_1.hard_constraints[0].message

        # Cannot submit infeasible plan
        with pytest.raises(PlanValidationError) as exc_info:
            create_plan_version_snapshot(plan, submitted_by=user)
        assert "Cannot submit plan with unresolved hard constraints" in str(exc_info.value)

        # 4. Fix plan schedule: Move CS102 to Term 2, Add CS101 in Term 1, Add CS201 in Term 3, Math in Term 1
        move_course_in_plan(plan, item_cs102.id, target_term=t["s27"], target_term_index=2)
        add_course_to_plan(plan, c["cs101"], t["f26"], term_index=1)
        add_course_to_plan(plan, c["math101"], t["f26"], term_index=1)
        add_course_to_plan(plan, c["cs201"], t["f27"], term_index=3)

        # 5. Re-simulate -> Valid for submission!
        sim_2 = simulate_plan(plan)
        assert sim_2.is_valid_for_submission is True
        assert len(sim_2.hard_constraints) == 0
        assert sim_2.projected_graduation_term == "FA2027"

        # 6. Submit plan version
        version_1 = create_plan_version_snapshot(plan, submitted_by=user, submission_note="Initial ready plan")
        assert version_1.version_number == 1
        assert version_1.status == PlanVersionStatus.SUBMITTED
        assert len(version_1.snapshot_data["items"]) == 4

        # 7. CRITICAL ASSERTION: Official student record and transcript entries are 100% UNTOUCHED!
        rec.refresh_from_db()
        assert TranscriptEntry.objects.filter(student_record=rec).count() == transcript_count_before
        assert rec.cached_total_credits == rec_credits_before
        assert rec.pinned_curriculum_id == rec_pinned_curriculum_before

    def test_course_outside_pinned_curriculum_rejected(self, planning_environment):
        """Attempting to add a course not offered in the pinned curriculum version is rejected."""
        env = planning_environment
        rec = env["record"]
        outside_crs = env["courses"]["outside"]
        plan = create_plan(student_record=rec, name="Draft Plan")

        with pytest.raises(PlanValidationError) as exc_info:
            add_course_to_plan(plan, outside_crs, env["terms"]["f26"], term_index=1)
        assert "is not offered in pinned curriculum version" in str(exc_info.value)

    def test_submitted_snapshots_are_strictly_immutable(self, planning_environment):
        """Attempts to mutate snapshot_data or delete a submitted PlanVersion are rejected."""
        env = planning_environment
        rec = env["record"]
        c = env["courses"]
        t = env["terms"]
        user = env["users"]["student"]

        plan = create_plan(student_record=rec, name="Submitted Plan")
        add_course_to_plan(plan, c["cs101"], t["f26"], term_index=1)
        version = create_plan_version_snapshot(plan, submitted_by=user)

        # Attempt to modify snapshot_data
        version.snapshot_data = {"tampered": True}
        with pytest.raises(PlanVersionImmutabilityError):
            version.save()

        # Attempt to delete snapshot
        with pytest.raises(PlanVersionImmutabilityError):
            version.delete()

    def test_optimistic_concurrency_conflict_returns_409(self, planning_environment):
        """Concurrent updates with mismatched row_version raise PlanConcurrencyError and return 409."""
        env = planning_environment
        rec = env["record"]
        plan = create_plan(student_record=rec, name="Concurrent Plan")
        assert plan.row_version == 1

        # Session A updates with expected_row_version=1 -> Succeeds, increments to 2
        update_plan(plan, expected_row_version=1, name="Updated by Session A")
        assert plan.row_version == 2

        # Session B attempts update with stale expected_row_version=1 -> Fails with 409
        with pytest.raises(PlanConcurrencyError):
            update_plan(plan, expected_row_version=1, name="Stale Session B update")

    def test_what_if_simulation_against_alternative_curriculum(self, planning_environment):
        """What-if simulation audits against another curriculum without altering student's pinned version."""
        env = planning_environment
        rec = env["record"]
        c = env["courses"]
        t = env["terms"]
        ver_ds = env["version_ds"]

        # Student has completed CS101
        TranscriptEntry.objects.create(
            institution=env["inst"],
            student_record=rec,
            course=c["cs101"],
            term=t["f26"],
            grade="A",
            credits_attempted=Decimal("4.00"),
            credits_earned=Decimal("4.00"),
            status=TranscriptEntryStatus.COMPLETED,
            verification_status=VerificationStatus.VERIFIED,
        )

        # Create a plan adding MATH101
        plan = create_plan(student_record=rec, name="What-If Test Plan")
        add_course_to_plan(plan, c["math101"], t["s27"], term_index=1)

        result = simulate_what_if(rec, target_curriculum=ver_ds, plan=plan)

        assert result["target_curriculum"]["programme_code"] == "BS_DS"
        assert result["plan_simulation"] is not None
        # Pinned curriculum on record is still BS_CS
        rec.refresh_from_db()
        assert rec.pinned_curriculum.programme.code == "BS_CS"

    def test_plan_api_permissions_and_scoping(self, planning_environment):
        """API: Students see only own plans, advisors see assigned advisee plans, cross-tenant denied."""
        env = planning_environment
        rec = env["record"]
        plan = create_plan(student_record=rec, name="Alice API Plan")

        client = APIClient()

        # 1. Student Alice accesses own plan -> 200
        client.force_authenticate(user=env["users"]["student"])
        resp = client.get(f"/api/v1/plans/{plan.id}/")
        assert resp.status_code == status.HTTP_200_OK

        # 2. Advisor Dan (assigned) accesses Alice's plan -> 200
        client.force_authenticate(user=env["users"]["advisor"])
        resp = client.get(f"/api/v1/plans/{plan.id}/")
        assert resp.status_code == status.HTTP_200_OK

        # 3. Unassigned Advisor accesses Alice's plan -> 404
        client.force_authenticate(user=env["users"]["unassigned_advisor"])
        resp = client.get(f"/api/v1/plans/{plan.id}/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

        # 4. Other Institution user accesses plan -> 404 (zero existence leakage)
        client.force_authenticate(user=env["users"]["other_inst_user"])
        resp = client.get(f"/api/v1/plans/{plan.id}/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_client_supplied_eligibility_values_ignored(self, planning_environment):
        """API ignores client-forged eligibility or simulation results in request payload."""
        env = planning_environment
        rec = env["record"]
        plan = create_plan(student_record=rec, name="Tamper Test Plan")

        client = APIClient()
        client.force_authenticate(user=env["users"]["student"])

        # Client sends forged `is_valid_for_submission=True` or forged status in update
        resp = client.put(
            f"/api/v1/plans/{plan.id}/",
            {
                "expected_row_version": 1,
                "name": "Tampered Plan",
                "is_valid_for_submission": True,  # Disallowed client override
                "status": "APPROVED",             # Disallowed client override
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        plan.refresh_from_db()
        assert plan.status == PlanStatus.DRAFT  # Server kept DRAFT status
