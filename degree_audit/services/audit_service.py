from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any

from academic_records.models import StudentRecord, TranscriptEntryStatus, VerificationStatus
from academic_records.services.context_builder import build_rule_context
from curriculum.models import RequirementGroupType


@dataclass
class GroupAuditDetail:
    group_id: str
    name: str
    group_type: str
    min_credits: Decimal
    min_courses: int
    min_cgpa: Decimal | None
    earned_credits: Decimal = Decimal("0.00")
    in_progress_credits: Decimal = Decimal("0.00")
    remaining_credits: Decimal = Decimal("0.00")
    is_satisfied: bool = False
    cgpa_satisfied: bool = True
    allocated_courses: list[dict[str, Any]] = field(default_factory=list)
    remaining_mandatory_courses: list[dict[str, Any]] = field(default_factory=list)
    in_progress_courses: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DegreeAuditReport:
    student_id: str
    student_username: str
    programme_code: str
    programme_name: str
    version_number: int
    academic_year: str
    total_credits_required: Decimal
    total_credits_earned: Decimal
    total_credits_in_progress: Decimal
    remaining_credits_required: Decimal
    overall_cgpa: Decimal
    min_cgpa_required: Decimal
    is_credits_satisfied: bool
    is_cgpa_satisfied: bool
    is_degree_satisfied: bool
    groups: list[GroupAuditDetail] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_degree_audit(
    student_record: StudentRecord,
    simulated_context: Any = None,
    target_curriculum: Any = None,
    is_simulation: bool = False,
) -> DegreeAuditReport:
    """
    Authoritative degree audit against the student's pinned curriculum version.
    Strict Allocation Rules:
    1. Only verified completed entries and verified transfer credits count as earned.
    2. In-progress courses are tracked separately and never counted as earned.
    3. Unverified or failed attempts do not count as earned.
    4. Each completed course is allocated to at most ONE requirement group (no double counting).
    5. Mandatory group courses are fulfilled first, followed by electives and category groups.
    """
    curriculum = target_curriculum or student_record.pinned_curriculum
    context = simulated_context or build_rule_context(student_record)

    # 1. Build pool of completed courses available for allocation
    # Track which course codes have been allocated to avoid double-counting
    allocated_course_codes: set[str] = set()

    completed_pool: dict[str, dict[str, Any]] = {}
    for cc in context.completed_courses:
        if cc.status == "completed":
            completed_pool[cc.course_code] = {
                "course_code": cc.course_code,
                "credits": cc.credits,
                "grade": cc.grade,
                "source": "TRANSCRIPT",
            }

    # Add verified transfer credits to pool
    for tc in context.transfer_credits:
        if tc.verified and tc.course_code not in completed_pool:
            completed_pool[tc.course_code] = {
                "course_code": tc.course_code,
                "credits": tc.credits,
                "grade": tc.grade or "CR",
                "source": "TRANSFER",
            }

    # Set of exempted course codes
    exempted_codes = {ex.course_code for ex in context.exemptions if ex.verified}

    # Map of in-progress entries
    in_progress_entries = student_record.transcript_entries.select_related(
        "course"
    ).filter(
        status=TranscriptEntryStatus.IN_PROGRESS,
        verification_status__in=[
            VerificationStatus.VERIFIED,
            VerificationStatus.OFFICIAL_SEALED,
        ],
    )
    in_progress_pool = {
        entry.course.code: {
            "course_code": entry.course.code,
            "title": entry.course.title,
            "credits": entry.credits_attempted,
        }
        for entry in in_progress_entries
    }

    # 2. Fetch all requirement groups for the pinned version
    groups_qs = (
        curriculum.requirement_groups.prefetch_related(
            "group_courses__course", "children"
        )
        .order_by("display_order", "id")
        .all()
    )
    groups = list(groups_qs)

    group_audits: list[GroupAuditDetail] = []

    # PASS 1: Mandatory courses fulfillment across all groups
    group_mandatory_map: dict[str, list[dict[str, Any]]] = {}
    group_allocated_map: dict[str, list[dict[str, Any]]] = {}
    group_earned_credits_map: dict[str, Decimal] = {}

    for g in groups:
        g_id = str(g.id)
        group_mandatory_map[g_id] = []
        group_allocated_map[g_id] = []
        group_earned_credits_map[g_id] = Decimal("0.00")

        # Check all mandatory attached courses
        mandatory_gcs = [gc for gc in g.group_courses.all() if gc.is_mandatory]
        for gc in mandatory_gcs:
            code = gc.course.code
            if code in exempted_codes:
                # Waived by exemption
                group_allocated_map[g_id].append(
                    {
                        "course_code": code,
                        "title": gc.course.title,
                        "credits": gc.course.credits,
                        "grade": "EXEMPT",
                        "is_mandatory": True,
                        "status": "EXEMPTED",
                    }
                )
            elif code in completed_pool and code not in allocated_course_codes:
                item = completed_pool[code]
                allocated_course_codes.add(code)
                group_earned_credits_map[g_id] += item["credits"]
                group_allocated_map[g_id].append(
                    {
                        "course_code": code,
                        "title": gc.course.title,
                        "credits": item["credits"],
                        "grade": item["grade"],
                        "is_mandatory": True,
                        "status": "COMPLETED",
                    }
                )
            else:
                # Missing mandatory course
                group_mandatory_map[g_id].append(
                    {
                        "course_code": code,
                        "title": gc.course.title,
                        "credits": gc.course.credits,
                    }
                )

    # PASS 2: Elective and Category Course Allocation
    for g in groups:
        g_id = str(g.id)
        target_credits = Decimal(str(g.min_credits))

        # Attached elective courses
        elective_gcs = [gc for gc in g.group_courses.all() if not gc.is_mandatory]
        for gc in elective_gcs:
            code = gc.course.code
            if group_earned_credits_map[g_id] >= target_credits:
                break
            if code in completed_pool and code not in allocated_course_codes:
                item = completed_pool[code]
                allocated_course_codes.add(code)
                group_earned_credits_map[g_id] += item["credits"]
                group_allocated_map[g_id].append(
                    {
                        "course_code": code,
                        "title": gc.course.title,
                        "credits": item["credits"],
                        "grade": item["grade"],
                        "is_mandatory": False,
                        "status": "COMPLETED",
                    }
                )

        # For CREDIT_CATEGORY or general groups with credit deficits:
        # Check any unallocated completed courses matching the group category
        if group_earned_credits_map[g_id] < target_credits and (
            g.group_type == RequirementGroupType.CREDIT_CATEGORY
            or not g.group_courses.exists()
        ):
            for code, item in list(completed_pool.items()):
                if code not in allocated_course_codes:
                    allocated_course_codes.add(code)
                    group_earned_credits_map[g_id] += item["credits"]
                    group_allocated_map[g_id].append(
                        {
                            "course_code": code,
                            "title": code,
                            "credits": item["credits"],
                            "grade": item["grade"],
                            "is_mandatory": False,
                            "status": "COMPLETED",
                        }
                    )
                    if group_earned_credits_map[g_id] >= target_credits:
                        break

    # PASS 3: Calculate In-Progress credits and Final group status
    for g in groups:
        g_id = str(g.id)
        earned = group_earned_credits_map[g_id]
        min_cr = Decimal(str(g.min_credits))
        min_courses = g.min_courses
        min_cgpa = Decimal(str(g.min_cgpa)) if g.min_cgpa is not None else None

        remaining_mandatory = group_mandatory_map[g_id]
        allocated = group_allocated_map[g_id]

        # Calculate in-progress credits for this group
        in_progress_credits = Decimal("0.00")
        group_in_progress_courses: list[dict[str, Any]] = []

        # Check if missing mandatory courses are in progress
        for rem in remaining_mandatory:
            code = rem["course_code"]
            if code in in_progress_pool:
                ip_item = in_progress_pool[code]
                in_progress_credits += Decimal(str(ip_item["credits"]))
                group_in_progress_courses.append(ip_item)

        # Check attached elective courses in progress
        for gc in g.group_courses.all():
            code = gc.course.code
            if (
                code in in_progress_pool
                and code not in [c["course_code"] for c in group_in_progress_courses]
            ):
                ip_item = in_progress_pool[code]
                in_progress_credits += Decimal(str(ip_item["credits"]))
                group_in_progress_courses.append(ip_item)

        remaining_cr = max(Decimal("0.00"), min_cr - earned)

        # Check CGPA satisfaction for group
        group_cgpa_sat = True
        if min_cgpa is not None and (context.cgpa is None or context.cgpa < min_cgpa):
            group_cgpa_sat = False

        is_sat = (
            len(remaining_mandatory) == 0
            and earned >= min_cr
            and len(allocated) >= min_courses
            and group_cgpa_sat
        )

        group_audits.append(
            GroupAuditDetail(
                group_id=g_id,
                name=g.name,
                group_type=g.group_type,
                min_credits=min_cr,
                min_courses=min_courses,
                min_cgpa=min_cgpa,
                earned_credits=earned,
                in_progress_credits=in_progress_credits,
                remaining_credits=remaining_cr,
                is_satisfied=is_sat,
                cgpa_satisfied=group_cgpa_sat,
                allocated_courses=allocated,
                remaining_mandatory_courses=remaining_mandatory,
                in_progress_courses=group_in_progress_courses,
            )
        )

    # Overall Summary
    total_required = Decimal(str(curriculum.total_credits_required))
    total_earned = context.total_credits or Decimal("0.00")
    total_in_progress = sum(
        (Decimal(str(item["credits"])) for item in in_progress_pool.values()),
        Decimal("0.00"),
    )
    rem_required = max(Decimal("0.00"), total_required - total_earned)

    min_cgpa_req = Decimal(str(curriculum.min_cgpa_required))
    cgpa_sat = context.cgpa is not None and context.cgpa >= min_cgpa_req
    credits_sat = total_earned >= total_required

    # Degree is satisfied only if:
    # 1. Total credits requirement met
    # 2. Overall CGPA requirement met
    # 3. All requirement groups are satisfied
    all_groups_sat = all(bool(ga.is_satisfied) for ga in group_audits)
    degree_sat = credits_sat and cgpa_sat and all_groups_sat

    overall_cgpa_val = context.cgpa if context.cgpa is not None else Decimal("0.00")

    # Update cached totals on student record if different (and not in simulation mode)
    if not is_simulation and (
        student_record.cached_total_credits != total_earned
        or student_record.cached_cgpa != overall_cgpa_val
    ):
        student_record.cached_total_credits = total_earned
        student_record.cached_cgpa = overall_cgpa_val
        student_record.save(update_fields=["cached_total_credits", "cached_cgpa"])

    return DegreeAuditReport(
        student_id=str(student_record.student_id),
        student_username=student_record.student.username,
        programme_code=curriculum.programme.code,
        programme_name=curriculum.programme.name,
        version_number=curriculum.version_number,
        academic_year=curriculum.academic_year,
        total_credits_required=total_required,
        total_credits_earned=total_earned,
        total_credits_in_progress=total_in_progress,
        remaining_credits_required=rem_required,
        overall_cgpa=overall_cgpa_val,
        min_cgpa_required=min_cgpa_req,
        is_credits_satisfied=credits_sat,
        is_cgpa_satisfied=cgpa_sat,
        is_degree_satisfied=degree_sat,
        groups=group_audits,
    )
