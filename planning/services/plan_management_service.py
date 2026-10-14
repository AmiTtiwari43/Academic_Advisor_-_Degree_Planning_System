import uuid

from django.db import transaction
from django.db.models import F, Max

from academic_records.models import AcademicTerm, StudentRecord
from curriculum.models import Course, CurriculumVersion
from planning.models import Plan, PlanItem, PlanStatus


class PlanConcurrencyError(Exception):
    """Raised when plan row_version does not match expected version (optimistic lock conflict)."""
    pass


class PlanValidationError(Exception):
    """Raised when plan operations violate curriculum boundaries or structural limits."""
    pass


def create_plan(
    student_record: StudentRecord,
    name: str = "Primary Academic Plan",
    is_primary: bool = True,
    curriculum_version: CurriculumVersion | None = None,
) -> Plan:
    """
    Creates a new degree plan for a student record.
    Defaults to the student's pinned curriculum version.
    """
    target_version = curriculum_version or student_record.pinned_curriculum
    if not target_version:
        raise PlanValidationError("Student record does not have a pinned curriculum version.")

    with transaction.atomic():
        if is_primary:
            Plan.objects.filter(
                student_record=student_record,
                is_primary=True,
            ).update(is_primary=False)

        plan = Plan.objects.create(
            institution=student_record.institution,
            student_record=student_record,
            curriculum_version=target_version,
            name=name,
            is_primary=is_primary,
            status=PlanStatus.DRAFT,
            row_version=1,
        )
        return plan


def update_plan(
    plan: Plan,
    expected_row_version: int,
    name: str | None = None,
    is_primary: bool | None = None,
) -> Plan:
    """
    Updates plan attributes with optimistic concurrency validation.
    """
    if plan.row_version != expected_row_version:
        raise PlanConcurrencyError(
            f"Plan was modified by another session (current v{plan.row_version}, expected v{expected_row_version}). Please refresh."
        )

    with transaction.atomic():
        if is_primary and not plan.is_primary:
            Plan.objects.filter(
                student_record=plan.student_record,
                is_primary=True,
            ).update(is_primary=False)
            plan.is_primary = True

        if name is not None:
            plan.name = name

        plan.row_version = plan.row_version + 1
        plan.save(update_fields=["name", "is_primary", "row_version", "updated_at"])
        return plan


def add_course_to_plan(
    plan: Plan,
    course: Course,
    planned_term: AcademicTerm,
    term_index: int,
    position: int | None = None,
    expected_row_version: int | None = None,
    notes: str = "",
) -> PlanItem:
    """
    Adds a course to a planned semester with curriculum boundary and concurrency verification.
    """
    if expected_row_version is not None and plan.row_version != expected_row_version:
        raise PlanConcurrencyError(
            f"Plan was modified by another session (current v{plan.row_version}, expected v{expected_row_version}). Please refresh."
        )

    # 1. Verify course belongs to plan's pinned curriculum version
    in_curriculum = plan.curriculum_version.requirement_groups.filter(
        group_courses__course=course
    ).exists()
    if not in_curriculum:
        raise PlanValidationError(
            f"Course {course.code} is not offered in pinned curriculum version v{plan.curriculum_version.version_number}."
        )

    # 2. Check for duplicate course in plan
    if PlanItem.objects.filter(plan=plan, course=course).exists():
        raise PlanValidationError(
            f"Course {course.code} is already included in this plan."
        )

    with transaction.atomic():
        # Determine position if not explicitly supplied
        if position is None:
            max_pos = PlanItem.objects.filter(
                plan=plan, planned_term=planned_term
            ).aggregate(Max("position"))["position__max"]
            pos = 0 if max_pos is None else max_pos + 1
        else:
            pos = position

        item = PlanItem.objects.create(
            institution=plan.institution,
            plan=plan,
            course=course,
            planned_term=planned_term,
            term_index=term_index,
            position=pos,
            notes=notes,
        )

        # Increment plan row version
        Plan.objects.filter(id=plan.id).update(row_version=F("row_version") + 1)
        plan.refresh_from_db()
        return item


def remove_course_from_plan(
    plan: Plan,
    plan_item_id: str | uuid.UUID,
    expected_row_version: int | None = None,
) -> None:
    """
    Removes a planned course item from the plan.
    """
    if expected_row_version is not None and plan.row_version != expected_row_version:
        raise PlanConcurrencyError(
            f"Plan was modified by another session (current v{plan.row_version}, expected v{expected_row_version}). Please refresh."
        )

    with transaction.atomic():
        item = PlanItem.objects.filter(plan=plan, id=plan_item_id).first()
        if not item:
            raise PlanValidationError(f"Plan item {plan_item_id} not found in plan.")

        item.delete()
        Plan.objects.filter(id=plan.id).update(row_version=F("row_version") + 1)
        plan.refresh_from_db()


def move_course_in_plan(
    plan: Plan,
    plan_item_id: str | uuid.UUID,
    target_term: AcademicTerm,
    target_term_index: int,
    target_position: int = 0,
    expected_row_version: int | None = None,
) -> PlanItem:
    """
    Moves a planned course to a new term or reorders within a term.
    """
    if expected_row_version is not None and plan.row_version != expected_row_version:
        raise PlanConcurrencyError(
            f"Plan was modified by another session (current v{plan.row_version}, expected v{expected_row_version}). Please refresh."
        )

    with transaction.atomic():
        item = PlanItem.objects.filter(plan=plan, id=plan_item_id).first()
        if not item:
            raise PlanValidationError(f"Plan item {plan_item_id} not found in plan.")

        item.planned_term = target_term
        item.term_index = target_term_index
        item.position = target_position
        item.save(update_fields=["planned_term", "term_index", "position", "updated_at"])

        Plan.objects.filter(id=plan.id).update(row_version=F("row_version") + 1)
        plan.refresh_from_db()
        return item
