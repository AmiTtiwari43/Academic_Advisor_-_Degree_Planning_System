import re
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional

from institutions.models import Institution
from rule_engine.core.context import CompletedCourse, RuleContext
from rule_engine.core.interpreter import evaluate_rule
from rule_engine.core.result import EvaluationStatus

from .guardrails import detect_prompt_injection, sanitize_user_prompt
from .retrieval_service import get_authorized_context

DISCLAIMER_TEXT = (
    "AI responses are grounded strictly in your institution's published curriculum "
    "and official degree audit records. The assistant cannot make exceptions, approve "
    "degree plans, or modify academic records. Always verify academic plans with your official advisor."
)


def extract_course_codes_from_prompt(prompt: str) -> List[str]:
    """
    Extracts course codes from prompt text, e.g. CS101, MATH-201, BIO_100.
    """
    pattern = re.compile(r"\b([A-Z]{2,5})[-_\s]?([0-9]{3,4}[A-Z]?)\b", re.IGNORECASE)
    matches = pattern.findall(prompt)
    codes = []
    for dept, num in matches:
        codes.append(f"{dept.upper()}{num.upper()}")
    return list(dict.fromkeys(codes))


def answer_curriculum_query(
    user: Any,
    institution: Institution,
    prompt: str,
    student_record_id: Optional[str | uuid.UUID] = None,
) -> Dict[str, Any]:
    """
    Synthesizes an authoritative, curriculum-grounded answer.
    Guarantees:
    - Pre-retrieval authorization.
    - Prompt injection immunity.
    - Zero database mutations.
    - Authoritative rule-engine citations.
    """
    # 1. Sanitize user input
    sanitized_prompt = sanitize_user_prompt(prompt)

    # 2. Check for adversarial prompt injection
    is_injection, reason = detect_prompt_injection(sanitized_prompt)
    if is_injection:
        return {
            "answer": (
                "Request rejected. The Academic Assistant operates under strict security boundaries "
                "and cannot alter academic records, grant policy overrides, or bypass curriculum rules. "
                f"Adversarial instruction detected: {reason}."
            ),
            "citations": [
                {
                    "source_type": "SECURITY_POLICY",
                    "reference": "System Safety Boundary",
                    "details": "Platform security strictly prohibits instruction injection and state mutations.",
                }
            ],
            "grounded_context_summary": "Security guardrails triggered.",
            "disclaimer": DISCLAIMER_TEXT,
        }

    # 3. Retrieve strictly authorized context (permission filter executed BEFORE access)
    context = get_authorized_context(
        user=user,
        institution=institution,
        student_record_id=student_record_id,
    )

    # 4. Analyze intent and ground in authoritative records
    course_codes = extract_course_codes_from_prompt(sanitized_prompt)
    catalog_courses = {c["code"].upper(): c for c in context.get("catalog_courses", [])}
    completed_codes = {c["code"].upper(): c for c in context.get("completed_courses", [])}
    degree_audit = context.get("degree_audit")
    pinned_curr = context.get("pinned_curriculum")

    citations: List[Dict[str, str]] = []
    answer_parts: List[str] = []

    # Case A: User queries specific course(s) / prerequisites
    if course_codes:
        for code in course_codes:
            course = catalog_courses.get(code)
            if not course:
                answer_parts.append(
                    f"Course '{code}' was not found in your institution's active curriculum. "
                    "Sources are missing or unavailable for this course code."
                )
                citations.append({
                    "source_type": "CATALOG_LOOKUP",
                    "reference": f"Catalog {institution.code}",
                    "details": f"Course code {code} is not cataloged in current active curriculum.",
                })
                continue

            prereq_rule = course.get("prerequisite_rule")
            curr_ref = f"{pinned_curr['programme_code']} v{pinned_curr['version_number']}" if pinned_curr else institution.code
            citations.append({
                "source_type": "CURRICULUM_CATALOG",
                "reference": f"Curriculum {curr_ref}, Course {code}",
                "details": f"{course['title']} ({course['credits']} credits)",
            })

            if not prereq_rule:
                answer_parts.append(
                    f"**{code} - {course['title']}** ({course['credits']} credits) has no prerequisites listed. "
                    "You are eligible to enroll without prior course completions."
                )
            else:
                completed_courses_list = [
                    CompletedCourse(
                        course_code=c["code"],
                        grade=c.get("grade") or "A",
                        credits=Decimal(str(c.get("credits", "3.0"))),
                    )
                    for c in context.get("completed_courses", [])
                ]
                cgpa_val = Decimal(str(context["student_record"]["cached_cgpa"])) if context.get("student_record") and context["student_record"].get("cached_cgpa") else Decimal("0.0")
                credits_val = Decimal(str(context["student_record"]["cached_total_credits"])) if context.get("student_record") and context["student_record"].get("cached_total_credits") else Decimal("0.0")

                rule_eval_context = RuleContext(
                    completed_courses=completed_courses_list,
                    cgpa=cgpa_val,
                    total_credits=credits_val,
                )

                try:
                    eval_result = evaluate_rule(prereq_rule, rule_eval_context)
                    is_satisfied = (eval_result.status == EvaluationStatus.SATISFIED)
                    blocking = f" Blocking reasons: {'; '.join(eval_result.blocking_reasons)}" if eval_result.blocking_reasons else ""
                    explanation = eval_result.node_results.explanation if eval_result.node_results and eval_result.node_results.explanation else ("All conditions satisfied." if is_satisfied else "Prerequisite conditions not met.")

                    if is_satisfied:
                        answer_parts.append(
                            f"**{code} - {course['title']}**: All prerequisites are **satisfied** based on your official academic transcript. {explanation}"
                        )
                    else:
                        answer_parts.append(
                            f"**{code} - {course['title']}**: Prerequisite requirements are **not satisfied**. {explanation}{blocking}"
                        )

                    citations.append({
                        "source_type": "RULE_ENGINE",
                        "reference": f"Prerequisite Interpreter [{code}]",
                        "details": f"Rule result: {'SATISFIED' if is_satisfied else 'UNSATISFIED'}. Rule: {explanation}",
                    })
                except Exception as exc:
                    answer_parts.append(
                        f"**{code} - {course['title']}**: Prerequisite rule could not be evaluated ({exc}). Rule is defined as: {prereq_rule}."
                    )

    # Case B: Degree progress / graduation / remaining requirements
    elif any(kw in sanitized_prompt.lower() for kw in ["graduate", "graduation", "degree audit", "progress", "remaining", "credits"]):
        if degree_audit:
            earned = degree_audit.get("total_credits_earned") or degree_audit.get("earned_credits", "0")
            req = degree_audit.get("total_credits_required") or degree_audit.get("required_credits", "120")
            status_text = "SATISFIED" if degree_audit.get("is_degree_satisfied") else "IN_PROGRESS"
            try:
                pct = round((float(earned) / float(req)) * 100, 1) if float(req) > 0 else 0
            except Exception:
                pct = degree_audit.get("progress_percentage", 0)

            prog_name = context.get("student_record", {}).get("programme_name", "Academic Programme")

            answer_parts.append(
                f"### Degree Progress Summary for {prog_name}\n"
                f"- **Overall Status:** {status_text}\n"
                f"- **Progress:** {pct}% complete\n"
                f"- **Credits Earned:** {earned} of {req} minimum required credits\n"
                f"- Cumulative GPA: {context.get('student_record', {}).get('cached_cgpa', '0.00')}"
            )

            # Remaining mandatory courses
            remaining_mandatory: List[str] = []
            for g in degree_audit.get("groups", []):
                for rmc in g.get("remaining_mandatory_courses", []):
                    if isinstance(rmc, dict):
                        remaining_mandatory.append(rmc.get("course_code") or rmc.get("code") or "")
                    elif isinstance(rmc, str):
                        remaining_mandatory.append(rmc)
            remaining_mandatory = [c for c in remaining_mandatory if c]
            if remaining_mandatory:
                courses_str = ", ".join(remaining_mandatory[:8])
                answer_parts.append(f"\n**Remaining Mandatory Courses ({len(remaining_mandatory)}):** {courses_str}")

            citations.append({
                "source_type": "DEGREE_AUDIT",
                "reference": f"Audit {context.get('student_record', {}).get('programme_code', 'PROG')}",
                "details": f"{earned}/{req} credits completed ({pct}%). Overall: {status_text}.",
            })
        else:
            answer_parts.append(
                "No official degree audit is currently available for this record. "
                "Please verify that an active curriculum is pinned to your student profile."
            )
            citations.append({
                "source_type": "DEGREE_AUDIT",
                "reference": "Audit Unavailable",
                "details": "Student record is not pinned to a published curriculum version.",
            })

    # Case C: General catalog inquiry
    else:
        sample_courses = [f"{c['code']} ({c['title']})" for c in context.get("catalog_courses", [])[:5]]
        answer_parts.append(
            f"Here is academic information grounded in the **{institution.name}** active curriculum. "
            f"Available sample courses include: {', '.join(sample_courses)}. "
            "You can ask about prerequisites for a specific course (e.g. 'What are the prerequisites for CS301?') "
            "or check your degree progress (e.g. 'How many remaining credits do I need to graduate?')."
        )
        citations.append({
            "source_type": "INSTITUTION_CATALOG",
            "reference": f"Catalog {institution.code}",
            "details": f"Institution active curriculum catalog for {institution.name}.",
        })

    full_answer = "\n\n".join(answer_parts)

    return {
        "answer": full_answer,
        "citations": citations,
        "grounded_context_summary": (
            f"Grounded in {len(catalog_courses)} catalog courses, {len(completed_codes)} completed courses, "
            f"and official degree audit records for {institution.code}."
        ),
        "disclaimer": DISCLAIMER_TEXT,
    }
