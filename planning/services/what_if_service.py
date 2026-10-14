from typing import Any

from academic_records.models import StudentRecord
from curriculum.models import CurriculumVersion
from degree_audit.services.audit_service import run_degree_audit
from planning.models import Plan
from planning.services.simulation_service import simulate_plan


def simulate_what_if(
    student_record: StudentRecord,
    target_curriculum: CurriculumVersion,
    plan: Plan | None = None,
) -> dict[str, Any]:
    """
    Evaluates what-if degree audit and multi-semester planning outcomes against an
    alternative curriculum version without modifying official academic records.
    """
    current_pinned_curriculum = student_record.pinned_curriculum

    # 1. Authoritative audit on current pinned curriculum (simulation mode: zero DB writes)
    current_audit = run_degree_audit(
        student_record,
        target_curriculum=current_pinned_curriculum,
        is_simulation=True,
    )

    # 2. What-if audit against target curriculum version
    what_if_audit = run_degree_audit(
        student_record,
        target_curriculum=target_curriculum,
        is_simulation=True,
    )

    # 3. Optional plan simulation against target curriculum
    plan_simulation = None
    if plan:
        plan_simulation = simulate_plan(
            plan,
            alternative_curriculum=target_curriculum,
        ).to_dict()

    return {
        "student_username": student_record.student.username,
        "current_curriculum": {
            "version_id": str(current_pinned_curriculum.id),
            "version_number": current_pinned_curriculum.version_number,
            "programme_code": current_pinned_curriculum.programme.code,
            "programme_name": current_pinned_curriculum.programme.name,
            "audit": current_audit.to_dict(),
        },
        "target_curriculum": {
            "version_id": str(target_curriculum.id),
            "version_number": target_curriculum.version_number,
            "programme_code": target_curriculum.programme.code,
            "programme_name": target_curriculum.programme.name,
            "audit": what_if_audit.to_dict(),
        },
        "plan_simulation": plan_simulation,
    }
