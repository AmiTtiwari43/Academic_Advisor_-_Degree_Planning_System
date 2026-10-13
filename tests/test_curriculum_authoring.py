from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import InstitutionMembership, Role
from curriculum.models import (
    Course,
    CurriculumImmutabilityError,
    CurriculumStatus,
    CurriculumVersion,
    DegreeType,
    PrerequisiteRule,
    Programme,
    RequirementGroup,
    RequirementGroupCourse,
    RequirementGroupType,
)
from curriculum.services import (
    assign_student_to_curriculum,
    clone_curriculum_version,
    compare_curriculum_versions,
    get_publish_preview,
    publish_curriculum_version,
    validate_curriculum_version,
)
from institutions.models import Institution
from rule_engine.core import CompletedCourse, RuleContext, evaluate_rule


@pytest.fixture
def institution_alpha(db):
    return Institution.objects.create(
        name="Alpha University",
        code="ALPHA",
        domain="alpha.edu",
    )


@pytest.fixture
def institution_beta(db):
    return Institution.objects.create(
        name="Beta Institute",
        code="BETA",
        domain="beta.edu",
    )


@pytest.fixture
def coordinator_alpha(db, institution_alpha):
    user = User.objects.create_user(
        username="coord_alpha", email="coord@alpha.edu", password="Password123!"
    )
    InstitutionMembership.objects.create(
        user=user,
        institution=institution_alpha,
        role=Role.COORDINATOR,
        is_active=True,
    )
    return user


@pytest.fixture
def student_alpha(db, institution_alpha):
    user = User.objects.create_user(
        username="student_alpha", email="student@alpha.edu", password="Password123!"
    )
    InstitutionMembership.objects.create(
        user=user,
        institution=institution_alpha,
        role=Role.STUDENT,
        is_active=True,
    )
    return user


@pytest.fixture
def student_beta(db, institution_beta):
    user = User.objects.create_user(
        username="student_beta", email="student@beta.edu", password="Password123!"
    )
    InstitutionMembership.objects.create(
        user=user,
        institution=institution_beta,
        role=Role.STUDENT,
        is_active=True,
    )
    return user


@pytest.fixture
def sample_curriculum(db, institution_alpha, coordinator_alpha):
    prog = Programme.objects.create(
        institution=institution_alpha,
        code="BS-CS",
        name="Bachelor of Science in Computer Science",
        degree_type=DegreeType.BACHELOR,
        department="Computer Science",
    )
    ver = CurriculumVersion.objects.create(
        institution=institution_alpha,
        programme=prog,
        version_number=1,
        academic_year="2026-2027",
        status=CurriculumStatus.DRAFT,
        total_credits_required=Decimal("120.00"),
        min_cgpa_required=Decimal("2.000"),
    )
    c1 = Course.objects.create(
        institution=institution_alpha,
        code="CS-101",
        title="Intro to CS",
        credits=Decimal("4.00"),
    )
    c2 = Course.objects.create(
        institution=institution_alpha,
        code="CS-201",
        title="Data Structures",
        credits=Decimal("4.00"),
    )
    grp = RequirementGroup.objects.create(
        institution=institution_alpha,
        curriculum_version=ver,
        name="Core Computer Science",
        group_type=RequirementGroupType.MANDATORY,
        min_credits=Decimal("8.00"),
    )
    RequirementGroupCourse.objects.create(
        requirement_group=grp, course=c1, is_mandatory=True, display_order=1
    )
    RequirementGroupCourse.objects.create(
        requirement_group=grp, course=c2, is_mandatory=True, display_order=2
    )

    # Valid prerequisite: CS-201 requires CS-101 with min grade C
    rule_doc = {
        "schema_version": 1,
        "type": "course_completed",
        "course_code": "CS-101",
        "min_grade": "C",
    }
    PrerequisiteRule.objects.create(
        institution=institution_alpha,
        curriculum_version=ver,
        course=c2,
        rule_json=rule_doc,
    )
    return {
        "programme": prog,
        "version": ver,
        "courses": [c1, c2],
        "group": grp,
    }


@pytest.mark.django_db
class TestCurriculumAuthoringWorkflow:
    def test_full_authoring_validation_preview_and_publish(
        self, sample_curriculum, coordinator_alpha
    ):
        ver = sample_curriculum["version"]

        # 1. Validation Report
        report = validate_curriculum_version(ver)
        assert report.is_valid is True
        assert len(report.errors) == 0

        # 2. Preview
        preview = get_publish_preview(ver)
        assert preview["can_publish"] is True
        assert preview["total_unique_courses"] == 2
        assert preview["total_requirement_groups"] == 1
        assert preview["total_prerequisite_rules"] == 1

        # 3. Publish
        published_v = publish_curriculum_version(ver, coordinator_alpha)
        assert published_v.status == CurriculumStatus.PUBLISHED
        assert published_v.published_by == coordinator_alpha
        assert published_v.published_at is not None

        # Re-publishing fails
        with pytest.raises(ValidationError):
            publish_curriculum_version(published_v, coordinator_alpha)


@pytest.mark.django_db
class TestCurriculumImmutabilityGuards:
    def test_published_version_rejects_modifications_and_deletes(
        self, sample_curriculum, coordinator_alpha
    ):
        ver = sample_curriculum["version"]
        grp = sample_curriculum["group"]

        # Publish the curriculum
        published_v = publish_curriculum_version(ver, coordinator_alpha)

        # 1. ORM save() rejection on version structural field
        published_v.total_credits_required = Decimal("130.00")
        with pytest.raises(CurriculumImmutabilityError):
            published_v.save()

        # 2. ORM delete() rejection on version
        with pytest.raises(CurriculumImmutabilityError):
            published_v.delete()

        # 3. ORM save() and delete() on RequirementGroup
        grp.min_credits = Decimal("10.00")
        with pytest.raises(CurriculumImmutabilityError):
            grp.save()
        with pytest.raises(CurriculumImmutabilityError):
            grp.delete()

        # 4. ORM save() on RequirementGroupCourse
        rgc = grp.group_courses.first()
        rgc.is_mandatory = False
        with pytest.raises(CurriculumImmutabilityError):
            rgc.save()
        with pytest.raises(CurriculumImmutabilityError):
            rgc.delete()

        # 5. ORM save() on PrerequisiteRule
        rule = published_v.prerequisite_rules.first()
        rule.description = "New description"
        with pytest.raises(CurriculumImmutabilityError):
            rule.save()
        with pytest.raises(CurriculumImmutabilityError):
            rule.delete()

    def test_api_layer_rejects_modifications_to_published_curriculum(
        self, sample_curriculum, coordinator_alpha
    ):
        client = APIClient()
        client.force_authenticate(user=coordinator_alpha)

        ver = sample_curriculum["version"]
        publish_curriculum_version(ver, coordinator_alpha)

        # PATCH published curriculum -> 400
        patch_res = client.patch(
            f"/api/v1/curricula/{ver.id}/",
            {"total_credits_required": 140.0},
            format="json",
        )
        assert patch_res.status_code == status.HTTP_400_BAD_REQUEST

        # DELETE published curriculum -> 400
        del_res = client.delete(f"/api/v1/curricula/{ver.id}/")
        assert del_res.status_code == status.HTTP_400_BAD_REQUEST

        # POST new requirement group to published curriculum -> 400
        post_grp_res = client.post(
            "/api/v1/requirement-groups/",
            {
                "curriculum_version": str(ver.id),
                "name": "Electives",
                "group_type": "ELECTIVE",
                "min_credits": 12.0,
            },
            format="json",
        )
        assert post_grp_res.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestCurriculumValidationRejections:
    def test_circular_requirement_group_rejected(self, sample_curriculum):
        ver = sample_curriculum["version"]
        g1 = sample_curriculum["group"]

        # Create child group g2
        g2 = RequirementGroup.objects.create(
            institution=ver.institution,
            curriculum_version=ver,
            parent=g1,
            name="Sub Group",
            group_type=RequirementGroupType.MANDATORY,
            min_credits=Decimal("0.00"),
        )
        # Create cycle by pointing g1's parent to g2
        g1.parent = g2
        g1.save()

        report = validate_curriculum_version(ver)
        assert report.is_valid is False
        assert any(e.code == "CYCLIC_REQUIREMENT_GROUP" for e in report.errors)

    def test_credit_shortfall_rejected(self, sample_curriculum):
        ver = sample_curriculum["version"]
        grp = sample_curriculum["group"]
        # Required is 8, let's bump min_credits to 20 when only 8 available
        grp.min_credits = Decimal("20.00")
        grp.save()

        report = validate_curriculum_version(ver)
        assert report.is_valid is False
        assert any(e.code == "INSUFFICIENT_AVAILABLE_CREDITS" for e in report.errors)

    def test_circular_prerequisites_detected(self, sample_curriculum):
        ver = sample_curriculum["version"]
        c1 = sample_curriculum["courses"][0]  # CS-101
        # CS-201 already requires c1 in sample_curriculum.
        # Now add rule: c1 requires CS-201!
        cycle_rule = {
            "schema_version": 1,
            "type": "course_completed",
            "course_code": "CS-201",
            "min_grade": "C",
        }
        PrerequisiteRule.objects.create(
            institution=ver.institution,
            curriculum_version=ver,
            course=c1,
            rule_json=cycle_rule,
        )

        report = validate_curriculum_version(ver)
        assert report.is_valid is False
        assert any(e.code == "CIRCULAR_PREREQUISITE" for e in report.errors)

    def test_duplicate_programme_code_rejected(self, institution_alpha):
        Programme.objects.create(
            institution=institution_alpha,
            code="BS-MATH",
            name="Mathematics",
        )
        with pytest.raises(IntegrityError):
            Programme.objects.create(
                institution=institution_alpha,
                code="BS-MATH",
                name="Duplicate Mathematics",
            )


@pytest.mark.django_db
class TestStudentCurriculumAssignment:
    def test_assign_to_published_version_succeeds(
        self, sample_curriculum, student_alpha, coordinator_alpha
    ):
        ver = sample_curriculum["version"]
        publish_curriculum_version(ver, coordinator_alpha)

        assignment = assign_student_to_curriculum(
            student=student_alpha,
            curriculum_version=ver,
            assigned_by=coordinator_alpha,
        )
        assert assignment.is_active is True
        assert assignment.student == student_alpha
        assert assignment.curriculum_version == ver

    def test_assign_to_draft_version_rejected(
        self, sample_curriculum, student_alpha, coordinator_alpha
    ):
        ver = sample_curriculum["version"]
        assert ver.status == CurriculumStatus.DRAFT

        with pytest.raises(ValidationError):
            assign_student_to_curriculum(
                student=student_alpha,
                curriculum_version=ver,
                assigned_by=coordinator_alpha,
            )

    def test_assign_cross_institution_rejected(
        self, sample_curriculum, student_beta, coordinator_alpha
    ):
        ver = sample_curriculum["version"]
        publish_curriculum_version(ver, coordinator_alpha)

        # student_beta belongs to institution_beta, ver belongs to institution_alpha
        with pytest.raises(ValidationError):
            assign_student_to_curriculum(
                student=student_beta,
                curriculum_version=ver,
                assigned_by=coordinator_alpha,
            )


@pytest.mark.django_db
class TestMultiTenantIsolation:
    def test_coordinator_cannot_access_foreign_institution_curriculum(
        self, sample_curriculum, coordinator_alpha, institution_beta
    ):
        # Create a programme and curriculum in beta
        prog_beta = Programme.objects.create(
            institution=institution_beta,
            code="BA-ENG",
            name="English",
        )
        ver_beta = CurriculumVersion.objects.create(
            institution=institution_beta,
            programme=prog_beta,
            version_number=1,
            academic_year="2026-2027",
            status=CurriculumStatus.DRAFT,
        )

        client = APIClient()
        client.force_authenticate(user=coordinator_alpha)

        # coordinator_alpha requesting ver_beta -> 404 (zero existence leakage)
        res = client.get(f"/api/v1/curricula/{ver_beta.id}/")
        assert res.status_code == status.HTTP_404_NOT_FOUND

        # coordinator_alpha modifying prog_beta -> 404
        patch_res = client.patch(
            f"/api/v1/programmes/{prog_beta.id}/",
            {"name": "Hacked English"},
            format="json",
        )
        assert patch_res.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestRuleHarnessAndEngineParity:
    def test_rule_harness_matches_pure_python_engine_call(self, coordinator_alpha):
        client = APIClient()
        client.force_authenticate(user=coordinator_alpha)

        rule_ast = {
            "schema_version": 1,
            "type": "all_of",
            "conditions": [
                {
                    "type": "course_completed",
                    "course_code": "CS-101",
                    "min_grade": "C",
                },
                {
                    "type": "credits_completed",
                    "min_credits": 15.0,
                },
                {
                    "type": "cgpa_min",
                    "value": 2.5,
                },
            ],
        }

        context_payload = {
            "student_id": "STUDENT-123",
            "completed_courses": [
                {
                    "course_code": "CS-101",
                    "grade": "B",
                    "credits": 4.0,
                    "term": "Fall 2025",
                }
            ],
            "total_credits": 16.0,
            "cumulative_gpa": 3.2,
        }

        # 1. API Call to Test Harness
        res = client.post(
            "/api/v1/rules/test-harness/",
            {"rule_json": rule_ast, "context": context_payload},
            format="json",
        )
        assert res.status_code == status.HTTP_200_OK, f"Failed with {res.data}"
        data = res.data
        assert data["status"] == "SATISFIED"
        assert data["is_satisfied"] is True
        assert len(data["blocking_reasons"]) == 0

        # 2. Direct Rule Engine Call with identical context
        direct_ctx = RuleContext(
            completed_courses=[
                CompletedCourse(
                    course_code="CS-101",
                    grade="B",
                    credits=Decimal("4.0"),
                    term="Fall 2025",
                ),
            ],
            total_credits=Decimal("16.0"),
            cgpa=Decimal("3.2"),
        )
        direct_res = evaluate_rule(rule_ast, direct_ctx)

        # 3. Assert Exact Parity
        assert data["status"] == direct_res.status.value
        assert data["eligible"] == direct_res.eligible
        assert data["blocking_reasons"] == list(direct_res.blocking_reasons)
        assert data["execution_tree"]["node_path"] == direct_res.node_results.node_path


@pytest.mark.django_db
class TestCurriculumCloningAndComparison:
    def test_clone_version_copies_tree_and_rules(self, sample_curriculum, coordinator_alpha):
        v1 = sample_curriculum["version"]
        # Publish v1
        publish_curriculum_version(v1, coordinator_alpha)

        # Clone to v2
        v2 = clone_curriculum_version(
            source_version=v1,
            user=coordinator_alpha,
            target_academic_year="2027-2028",
        )
        assert v2.version_number == 2
        assert v2.academic_year == "2027-2028"
        assert v2.status == CurriculumStatus.DRAFT
        assert v2.requirement_groups.count() == 1
        assert v2.prerequisite_rules.count() == 1

        # Assert course memberships copied
        v2_grp = v2.requirement_groups.first()
        assert v2_grp.group_courses.count() == 2

        # Assert comparison diff
        diff = compare_curriculum_versions(v1, v2)
        assert diff["metadata"]["v1"]["version_number"] == 1
        assert diff["metadata"]["v2"]["version_number"] == 2
        assert diff["courses"]["common_count"] == 2
