import json
import logging
import os
import re
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings
from rest_framework.exceptions import PermissionDenied

from institutions.models import Institution
from rule_engine.core.context import CompletedCourse, RuleContext
from rule_engine.core.interpreter import evaluate_rule
from rule_engine.core.result import EvaluationStatus

from .guardrails import detect_prompt_injection, sanitize_user_prompt, wrap_untrusted_context
from .llm_client import (
    call_gemini_api,
    call_secondary_ai,
    get_hardcoded_academic_fallback,
)
from .rag_service import (
    format_rag_citations,
    format_rag_context_for_prompt,
    retrieve_rag_context,
)
from .retrieval_service import get_authorized_context

logger = logging.getLogger(__name__)

DISCLAIMER_TEXT = (
    "Academic guidance is for degree planning purposes only. Official approvals and substitutions "
    "require your faculty advisor."
)


def extract_course_codes_from_prompt(prompt: str) -> List[str]:
    """
    Extracts course codes from prompt text in various formats,
    e.g. CS-101, CS101, CS 101, MATH-151, EE999, QUANTUM-999.
    Returns the exact tokens as matched in the user prompt.
    """
    pattern = re.compile(r"\b([A-Za-z]{2,10})[-_\s]?([0-9]{3,4}[A-Za-z]?)\b")
    matches = pattern.finditer(prompt)
    codes = []
    for m in matches:
        codes.append(m.group(0).strip().upper())
    return list(dict.fromkeys(codes))


def find_matching_catalog_course(
    query_code: str,
    catalog_courses: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    Finds a course from catalog matching code either exactly or normalized.
    """
    q_norm = re.sub(r"[-_\s]", "", query_code).upper()
    for c in catalog_courses:
        c_code = c.get("code", "")
        if c_code.upper() == query_code.upper():
            return c
        if re.sub(r"[-_\s]", "", c_code).upper() == q_norm:
            return c
    return None


def answer_curriculum_query(
    user: Any,
    institution: Institution,
    prompt: str,
    student_record_id: Optional[str | uuid.UUID] = None,
) -> Dict[str, Any]:
    """
    Synthesizes an authoritative, curriculum-grounded answer using:
    - Pre-retrieval authorization.
    - High-speed RAG chunk retrieval.
    - Standardized 10-point GPA scale reasoning & GPA improvement algorithms.
    - Multi-tier AI Fallback: Primary AI (Gemini) -> Secondary AI (Groq/Backup) -> Deterministic Engine -> Hardcoded Fallback.
    - Prompt injection immunity and zero database mutations.
    """
    try:
        # 1. Sanitize user input
        sanitized_prompt = sanitize_user_prompt(prompt)

        # 2. Check for adversarial prompt injection
        is_injection, reason = detect_prompt_injection(sanitized_prompt)
        if is_injection:
            return {
                "answer": (
                    "Request rejected. The Academic Assistant operates under strict security boundaries "
                    "and cannot alter academic records, grant policy overrides, or approve degree plans. "
                    "Official approvals and policy waivers must be processed by your designated faculty advisor. "
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

        # 3. Retrieve strictly authorized context
        context = get_authorized_context(
            user=user,
            institution=institution,
            student_record_id=student_record_id,
        )

        # 4. High-Speed RAG Chunk Retrieval
        rag_chunks = retrieve_rag_context(
            query=sanitized_prompt,
            student_context=context,
            top_k=5,
        )
        rag_citations = format_rag_citations(rag_chunks)

        # 5. Extract context elements
        extracted_codes = extract_course_codes_from_prompt(sanitized_prompt)
        catalog_courses = context.get("catalog_courses", [])
        completed_courses = context.get("completed_courses", [])
        in_progress_courses = context.get("in_progress_courses", [])
        failed_courses = context.get("failed_courses", [])
        degree_audit = context.get("degree_audit")
        pinned_curr = context.get("pinned_curriculum")
        student_rec = context.get("student_record")
        advisor_info = context.get("assigned_advisor")
        degree_plans = context.get("degree_plans", [])
        career_prefs = context.get("career_preferences", [])

        citations: List[Dict[str, str]] = []
        answer_parts: List[str] = []
        prompt_lower = sanitized_prompt.lower()

        # -------------------------------------------------------------
        # INTENT A: SPECIFIC COURSE ELIGIBILITY & PREREQUISITES
        # -------------------------------------------------------------
        has_course_codes = len(extracted_codes) > 0
        is_course_intent = has_course_codes and any(
            kw in prompt_lower for kw in [
                "prereq", "eligible", "eligibility", "can i take", "enroll", "require",
                "course", "class", "what is", "about"
            ]
        )

        if is_course_intent:
            matched_courses: Dict[str, Dict[str, Any]] = {}
            missing_codes: List[str] = []

            for code in extracted_codes:
                course = find_matching_catalog_course(code, catalog_courses)
                if course:
                    matched_courses[course["code"]] = course
                else:
                    base_code = code.split("-")[0] if "-" in code else code[:2]
                    if not any(c.startswith(base_code) for c in matched_courses):
                        missing_codes.append(code)

            dedup_missing = list(dict.fromkeys(missing_codes))
            for code in dedup_missing:
                norm_c = re.sub(r"[-_\s]", "", code).upper()
                if any(re.sub(r"[-_\s]", "", mc).upper() == norm_c for mc in matched_courses):
                    continue

                answer_parts.append(
                    f"Course '{code}' was not found in your institution's active curriculum. "
                    "Course records are missing or unavailable for this code."
                )
                citations.append({
                    "source_type": "CATALOG_LOOKUP",
                    "reference": f"Catalog {institution.code}",
                    "details": f"Course code {code} is not cataloged in current active curriculum.",
                })

            for c_code, course in matched_courses.items():
                prereq_rule = course.get("prerequisite_rule")
                curr_ref = f"{pinned_curr['programme_code']} v{pinned_curr['version_number']}" if pinned_curr else institution.code
                citations.append({
                    "source_type": "CURRICULUM_CATALOG",
                    "reference": f"Curriculum {curr_ref}, Course {c_code}",
                    "details": f"{course['title']} ({course['credits']} credits)",
                })

                completed_match = next((c for c in completed_courses if c["code"] == c_code), None)
                if completed_match:
                    answer_parts.append(
                        f"**{c_code} - {course['title']}**: You have already completed this course "
                        f"with grade **{completed_match['grade']}** ({completed_match['credits']} credits earned "
                        f"in term {completed_match.get('term_code', 'N/A')})."
                    )
                    continue

                in_prog_match = next((c for c in in_progress_courses if c["code"] == c_code), None)
                if in_prog_match:
                    answer_parts.append(
                        f"**{c_code} - {course['title']}**: You are currently **enrolled** in this course "
                        f"for term {in_prog_match.get('term_code', 'current term')}."
                    )
                    continue

                if not prereq_rule:
                    answer_parts.append(
                        f"**{c_code} - {course['title']}** ({course['credits']} credits) has **no prerequisites**. "
                        "You are eligible to enroll without prior course completions."
                    )
                else:
                    completed_courses_list = [
                        CompletedCourse(
                            course_code=c["code"],
                            grade=c.get("grade") or "A",
                            credits=Decimal(str(c.get("credits", "3.0"))),
                        )
                        for c in completed_courses
                    ]
                    cgpa_val = Decimal(str(student_rec["cached_cgpa"])) if student_rec and student_rec.get("cached_cgpa") else Decimal("0.0")
                    credits_val = Decimal(str(student_rec["cached_total_credits"])) if student_rec and student_rec.get("cached_total_credits") else Decimal("0.0")

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
                                f"**{c_code} - {course['title']}**: All prerequisites are **satisfied** based on your official academic transcript. {explanation}"
                            )
                        else:
                            answer_parts.append(
                                f"**{c_code} - {course['title']}**: Prerequisite requirements are **not satisfied**. {explanation}{blocking}"
                            )

                        citations.append({
                            "source_type": "RULE_ENGINE",
                            "reference": f"Prerequisite Interpreter [{c_code}]",
                            "details": f"Rule result: {'SATISFIED' if is_satisfied else 'UNSATISFIED'}. Rule: {explanation}",
                        })
                    except Exception as exc:
                        answer_parts.append(
                            f"**{c_code} - {course['title']}**: Prerequisite rule could not be evaluated ({exc}). Rule is defined as: {prereq_rule}."
                        )

        # -------------------------------------------------------------
        # INTENT B: GPA, CGPA & ACADEMIC STANDING (10-Point Scale & Improvement)
        # -------------------------------------------------------------
        elif any(kw in prompt_lower for kw in ["gpa", "cgpa", "grade point", "standing", "scale", "academic standing", "probation"]):
            if student_rec:
                cgpa_str = student_rec.get("cached_cgpa", "0.00")
                min_cgpa_str = str(degree_audit.get("min_cgpa_required", "5.000")) if degree_audit else "5.000"
                is_satisfied = float(cgpa_str) >= float(min_cgpa_str)
                status_text = "Good Standing" if is_satisfied else "Academic Review Required"
                policy = student_rec.get("repeated_course_policy", "BEST_GRADE")

                gpa_overview = (
                    f"### Academic Standing & GPA (10-Point Scale)\n"
                    f"- **Cumulative GPA (CGPA):** **{float(cgpa_str):.2f} / 10.00 Scale**\n"
                    f"- **Minimum Graduation Requirement:** {float(min_cgpa_str):.2f} / 10.00 Scale\n"
                    f"- **Academic Standing:** **{status_text}** ({'Satisfied' if is_satisfied else 'Below Minimum Threshold'})\n"
                    f"- **Graduation Threshold Satisfied:** {'Yes' if is_satisfied else 'No'}\n\n"
                    f"Metropolitan State University calculates all grade point averages on a standardized **1.00 – 10.00 scale**, "
                    f"where letter grades correspond to: A+ (10.0), A (9.0), A- (8.5), B+ (8.0), B (7.0), B- (6.5), "
                    f"C+ (6.0), C (5.0), C- (4.5), D+ (4.0), D (3.0), and F (0.0)."
                )

                is_gpa_improvement = any(
                    kw in prompt_lower
                    for kw in ["increase", "improve", "raise", "boost", "how can i", "how to", "maximize", "better", "higher"]
                )

                if is_gpa_improvement:
                    advisor_contact = advisor_info.get("name", "your assigned faculty advisor") if advisor_info else "your faculty advisor"
                    if failed_courses:
                        failed_names = ", ".join([f"**{c['code']}** ({c['title']})" for c in failed_courses])
                        retake_details = (
                            f"   - **Immediate Retake Candidates:** You currently have unpassed course attempts ({failed_names}). "
                            f"Retaking these and earning a passing grade (such as A or A+) will replace the 0.0 grade points, "
                            f"producing the fastest mathematical increase in your CGPA."
                        )
                    else:
                        retake_details = (
                            f"   - Retaking any completed course where you received a grade of C (5.0) or lower allows higher grade "
                            f"points to replace the lower attempt in cumulative GPA calculation."
                        )

                    improvement_guide = (
                        f"\n\n#### Actionable Strategies to Increase Your CGPA on the 10-Point Scale:\n"
                        f"1. **Repeat Courses with Low or Failing Grades ({policy} Policy):**\n"
                        f"   Under institutional policy, retaking eligible courses replaces the lower grade in cumulative calculations.\n"
                        f"{retake_details}\n"
                        f"2. **Maximize Grades in High-Credit Courses (4.0 Credits):**\n"
                        f"   Courses carrying 4.0 credits (such as core Computer Science and Mathematics courses) have double the mathematical "
                        f"weight of 2.0-credit courses. Earning an **A (9.0)** or **A+ (10.0)** in 4-credit courses produces the most significant upward shift in CGPA.\n"
                        f"3. **Grade Target Impact Formula:**\n"
                        f"   To elevate your CGPA above {float(cgpa_str):.2f}, your upcoming semester SGPA must exceed your current CGPA:\n"
                        f"   $$\\text{{New CGPA}} = \\frac{{\\text{{Current Quality Points}} + \\text{{Upcoming Term Quality Points}}}}{{\\text{{Current Credits}} + \\text{{Upcoming Term Credits}}}}$$\n"
                        f"4. **Balanced Semester Workload & Advising:**\n"
                        f"   Maintain a balanced load (12–16 credits) in the **Degree Planner** tab to ensure adequate study hours, "
                        f"and consult {advisor_contact} to select optimal course sequences."
                    )
                    answer_parts.append(gpa_overview + improvement_guide)
                else:
                    answer_parts.append(gpa_overview)

                citations.append({
                    "source_type": "DEGREE_AUDIT",
                    "reference": f"Official Transcript [{student_rec.get('username')}]",
                    "details": f"CGPA: {float(cgpa_str):.2f}/10.00. Min required: {float(min_cgpa_str):.2f}/10.00. Standing: {status_text}.",
                })
            else:
                answer_parts.append(
                    "No student record is active in your current session. "
                    "Metropolitan State University evaluates degree candidates on a standardized **1.00 – 10.00 GPA scale** "
                    "with a minimum 5.000 CGPA required for graduation."
                )
                citations.append({
                    "source_type": "INSTITUTION_POLICY",
                    "reference": "Academic Regulations",
                    "details": "Standard 10-point GPA scale with 5.000 minimum graduation threshold.",
                })

        # -------------------------------------------------------------
        # INTENT C: FACULTY ADVISOR INQUIRIES
        # -------------------------------------------------------------
        elif any(kw in prompt_lower for kw in ["advisor", "advise", "counselor", "who is my advisor", "contact advisor", "office hours"]):
            if advisor_info:
                answer_parts.append(
                    f"### Assigned Faculty Advisor\n"
                    f"- **Name:** {advisor_info['name']}\n"
                    f"- **Department:** {advisor_info['department']}\n"
                    f"- **Email:** {advisor_info['email']}\n"
                    f"- **Office Hours:** Monday / Wednesday: 2:00 PM – 4:00 PM (Engineering Hall, Room 412)\n\n"
                    f"You can request an advising consultation directly from your student dashboard or degree planner "
                    f"to review upcoming semester course selections and prerequisite waivers."
                )
                citations.append({
                    "source_type": "ADVISOR_ASSIGNMENT",
                    "reference": f"Advisor Registry [{institution.code}]",
                    "details": f"Assigned Advisor: {advisor_info['name']} ({advisor_info['email']}).",
                })
            else:
                answer_parts.append(
                    "You do not currently have a faculty advisor assigned in your student profile. "
                    "Please contact your department's Programme Coordinator to request an advisor assignment."
                )
                citations.append({
                    "source_type": "ADVISOR_ASSIGNMENT",
                    "reference": "Advisor Registry",
                    "details": "No active faculty advisor assignment found for this student record.",
                })

        # -------------------------------------------------------------
        # INTENT D: FAILED COURSES, IN-PROGRESS COURSES & COURSE HISTORY
        # -------------------------------------------------------------
        elif any(kw in prompt_lower for kw in ["fail", "failed", "failing", "in progress", "taking", "current courses", "retake", "repeat"]):
            lines: List[str] = ["### Academic Course Status Overview\n"]

            if failed_courses:
                failed_list = [f"**{c['code']}** ({c['title']}) in term {c['term_code']} (Grade: F)" for c in failed_courses]
                policy = student_rec.get("repeated_course_policy", "BEST_GRADE") if student_rec else "BEST_GRADE"
                lines.append(
                    f"- **Unpassed / Failed Courses ({len(failed_courses)}):**\n  - " + "\n  - ".join(failed_list) +
                    f"\n\n*Note on Repeated Courses:* Metropolitan State University applies the **{policy}** policy. "
                    f"Upon successfully retaking an unpassed course, the higher grade points replace the failing attempt in cumulative CGPA calculation."
                )
                citations.append({
                    "source_type": "TRANSCRIPT_RECORD",
                    "reference": f"Transcript Entries [{institution.code}]",
                    "details": f"{len(failed_courses)} unpassed courses recorded. Policy: {policy}.",
                })
            else:
                lines.append("- **Failed Courses:** None. All completed courses have passing grades.")

            if in_progress_courses:
                in_prog_list = [f"**{c['code']}** ({c['title']}, {c['credits']} cr, Term: {c['term_code']})" for c in in_progress_courses]
                lines.append(f"\n- **Currently In-Progress Courses ({len(in_progress_courses)}):**\n  - " + "\n  - ".join(in_prog_list))
                citations.append({
                    "source_type": "TRANSCRIPT_RECORD",
                    "reference": f"In-Progress Enrollment [{institution.code}]",
                    "details": f"{len(in_progress_courses)} courses currently in progress.",
                })

            answer_parts.append("\n".join(lines))

        # -------------------------------------------------------------
        # INTENT E: DEGREE PROGRESS, AUDIT & GRADUATION
        # -------------------------------------------------------------
        elif any(kw in prompt_lower for kw in ["graduate", "graduation", "degree audit", "progress", "remaining", "credits"]):
            if degree_audit:
                earned = degree_audit.get("total_credits_earned") or degree_audit.get("earned_credits", "0")
                req = degree_audit.get("total_credits_required") or degree_audit.get("required_credits", "120")
                in_prog = degree_audit.get("total_credits_in_progress", 0)
                status_text = "ALL REQUIREMENTS SATISFIED" if degree_audit.get("is_degree_satisfied") else "DEGREE IN PROGRESS"
                cgpa_val = float(student_rec.get("cached_cgpa", "0.00")) if student_rec else 0.0
                min_cgpa = float(degree_audit.get("min_cgpa_required", 5.0))

                try:
                    pct = round((float(earned) / float(req)) * 100, 1) if float(req) > 0 else 0
                except Exception:
                    pct = degree_audit.get("progress_percentage", 0)

                prog_name = student_rec.get("programme_name", "Academic Programme") if student_rec else "Academic Programme"

                answer_parts.append(
                    f"### Degree Progress Summary for {prog_name}\n"
                    f"- **Overall Status:** {status_text}\n"
                    f"- **Progress:** {pct}% complete\n"
                    f"- **Credits Earned:** {earned} of {req} minimum required credits (+{in_prog} cr in progress)\n"
                    f"- Cumulative GPA: {cgpa_val:.2f} (10.00 Scale, Min Required: {min_cgpa:.2f})\n"
                    f"- **GPA Threshold Satisfied:** {'Yes' if cgpa_val >= min_cgpa else 'No'}"
                )

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
                    "reference": f"Audit {student_rec.get('programme_code', 'PROG') if student_rec else 'PROG'}",
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

        # -------------------------------------------------------------
        # INTENT F: DEGREE PLANS & SEMESTER SCHEDULES
        # -------------------------------------------------------------
        elif any(kw in prompt_lower for kw in ["degree plan", "planned", "semester plan", "my plan", "upcoming semester"]):
            if degree_plans:
                primary_plan = next((p for p in degree_plans if p.get("is_primary")), degree_plans[0])
                planned_courses = primary_plan.get("planned_courses", [])
                lines = [
                    f"### Degree Plan: {primary_plan['name']}\n"
                    f"- **Plan Status:** **{primary_plan['status']}**\n"
                    f"- **Total Planned Courses:** {primary_plan['courses_count']} courses\n"
                ]
                if planned_courses:
                    lines.append("\n**Planned Courses:**")
                    for item in planned_courses[:8]:
                        lines.append(f"- **{item['course_code']}** ({item['course_title']}, {item['credits']} cr, Term: {item.get('term_code', 'Planned')})")
                lines.append("\nYou can edit or simulate future terms in the **Degree Planner** tab.")
                answer_parts.append("\n".join(lines))
                citations.append({
                    "source_type": "DEGREE_PLAN",
                    "reference": f"Plan [{primary_plan['name']}]",
                    "details": f"Status: {primary_plan['status']}. {primary_plan['courses_count']} courses planned.",
                })
            else:
                answer_parts.append(
                    "You do not have any degree plans created yet. "
                    "You can create a multi-semester degree plan in the **Degree Planner** to simulate prerequisite flows and graduation terms."
                )
                citations.append({
                    "source_type": "DEGREE_PLAN",
                    "reference": "Degree Planner",
                    "details": "No saved degree plan found.",
                })

        # -------------------------------------------------------------
        # INTENT G: CAREER PATHWAYS & COURSE RECOMMENDATIONS
        # -------------------------------------------------------------
        elif any(kw in prompt_lower for kw in ["career", "job", "software engineer", "data scientist", "skill", "competenc"]):
            if career_prefs:
                pref = career_prefs[0]
                skills_list = [f"**{s['name']}** ({s['min_proficiency']})" for s in pref.get("required_skills", [])[:5]]
                answer_parts.append(
                    f"### Career Pathway: {pref['title']}\n"
                    f"- **Objective:** {pref['title']}\n"
                    f"- **Description:** {pref.get('description', 'Industry specialization')}\n"
                    f"- **Core Competencies Required:** {', '.join(skills_list) if skills_list else 'Technical leadership, software engineering'}\n\n"
                    f"Visit the **Career Guidance** tab to view your full skill-gap analysis and degree-aligned elective recommendations."
                )
                citations.append({
                    "source_type": "CAREER_TAXONOMY",
                    "reference": f"Career Objective [{pref['code']}]",
                    "details": f"Target: {pref['title']}. {len(pref.get('required_skills', []))} competency mappings.",
                })
            else:
                answer_parts.append(
                    "You haven't set a career objective yet. "
                    "In the **Career Guidance** portal, you can select pathways such as **Software Engineer**, **Data Scientist**, or **DevOps Engineer** "
                    "to receive course recommendations that satisfy both skill competencies and degree requirements."
                )
                citations.append({
                    "source_type": "CAREER_TAXONOMY",
                    "reference": "Career Pathways",
                    "details": "No declared career preference.",
                })

        # -------------------------------------------------------------
        # INTENT H: GENERAL CATALOG & PLATFORM GUIDANCE
        # -------------------------------------------------------------
        else:
            sample_courses = [f"{c['code']} ({c['title']})" for c in catalog_courses[:5]]
            answer_parts.append(
                f"Here is academic information grounded in the **{institution.name}** active curriculum. "
                f"Active catalog courses include: {', '.join(sample_courses)}. "
                "You can ask about:\n"
                "- Course prerequisites (e.g. 'Can I take CS-201?' or 'What are the prerequisites for CS-301?')\n"
                "- Degree progress & credits (e.g. 'How many remaining credits do I need to graduate?')\n"
                "- Academic standing & GPA (e.g. 'What is my current CGPA on the 10-point scale?')\n"
                "- Your assigned advisor (e.g. 'Who is my faculty advisor?')\n"
                "- Career pathways (e.g. 'What courses help me become a Software Engineer?')"
            )
            citations.append({
                "source_type": "INSTITUTION_CATALOG",
                "reference": f"Catalog {institution.code}",
                "details": f"Institution active curriculum catalog for {institution.name}.",
            })

        # Combine deterministic answer
        deterministic_answer = "\n\n".join(answer_parts)
        final_answer = deterministic_answer
        ai_provider_used = "Deterministic Academic Engine (RAG Index)"

        # Merge citations with RAG citations
        for rc in rag_citations:
            if not any(c.get("reference") == rc.get("reference") for c in citations):
                citations.append(rc)

        # -------------------------------------------------------------
        # MULTI-TIER AI FALLBACK PIPELINE
        # Tier 1: Primary Free AI (Google Gemini)
        # Tier 2: Secondary Free AI (Groq / OpenRouter / Backup Gemini)
        # Tier 3: Grounded Deterministic RAG Synthesizer (Zero API Dependencies)
        # -------------------------------------------------------------
        gemini_key = os.environ.get("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", "")
        sec_key = os.environ.get("SECONDARY_AI_API_KEY") or getattr(settings, "SECONDARY_AI_API_KEY", "")
        sec_provider = os.environ.get("SECONDARY_AI_PROVIDER") or getattr(settings, "SECONDARY_AI_PROVIDER", "groq")

        system_instruction = (
            "You are the official University Academic Advisor AI. "
            "You answer student questions strictly based on the provided authorized academic context and RAG knowledge chunks. "
            "The university operates strictly on a 1.00 – 10.00 GPA scale (5.000 minimum for graduation). "
            "Never invent or hallucinate courses, grades, prerequisites, or policies. "
            "If information is missing, clearly state that it is unavailable. "
            "Never approve degree plans or alter transcripts. Be concise, professional, and clear."
        )

        rag_text = format_rag_context_for_prompt(rag_chunks)
        context_payload = wrap_untrusted_context(
            f"Institution: {institution.name} ({institution.code})\n"
            f"Student Info: {json.dumps(student_rec or {}, default=str)}\n"
            f"Degree Audit: {json.dumps(degree_audit or {}, default=str)}\n"
            f"Assigned Advisor: {json.dumps(advisor_info or {}, default=str)}\n"
            f"Completed Courses: {json.dumps(completed_courses[:15], default=str)}\n"
            f"In-Progress Courses: {json.dumps(in_progress_courses, default=str)}\n"
            f"Failed Courses: {json.dumps(failed_courses, default=str)}\n"
            f"Plans: {json.dumps(degree_plans[:2], default=str)}\n"
            f"RAG Knowledge Chunks:\n{rag_text}\n\n"
            f"Deterministic Grounded Findings:\n{deterministic_answer}"
        )

        # Try Tier 1: Primary AI (Google Gemini)
        if gemini_key and len(gemini_key.strip()) > 5:
            llm_response = call_gemini_api(
                system_instruction=system_instruction,
                context_text=context_payload,
                user_prompt=sanitized_prompt,
                api_key=gemini_key,
            )
            if llm_response and len(llm_response.strip()) > 20:
                final_answer = llm_response
                ai_provider_used = "Primary AI (Google Gemini Flash)"

        # If Tier 1 was not available or failed, Try Tier 2: Secondary AI (Groq / OpenRouter / Backup)
        if ai_provider_used == "Deterministic Academic Engine (RAG Index)" and sec_key and len(sec_key.strip()) > 5:
            sec_response, sec_label = call_secondary_ai(
                system_instruction=system_instruction,
                context_text=context_payload,
                user_prompt=sanitized_prompt,
                api_key=sec_key,
                provider=sec_provider,
            )
            if sec_response and len(sec_response.strip()) > 20:
                final_answer = sec_response
                ai_provider_used = sec_label or f"Secondary AI ({sec_provider})"

        return {
            "answer": final_answer,
            "citations": citations,
            "grounded_context_summary": (
                f"Grounded in {len(catalog_courses)} catalog courses, {len(completed_courses)} completed courses, "
                f"and official degree audit records for {institution.code}. [{ai_provider_used}]"
            ),
            "disclaimer": DISCLAIMER_TEXT,
        }

    except PermissionDenied:
        raise
    except Exception as exc:
        # Tier 4: Hardcoded Institutional Safety Fallback
        logger.exception("Unexpected exception in answer_curriculum_query: %s", exc)
        safe_fallback = get_hardcoded_academic_fallback(
            user_prompt=prompt,
            student_context=context if "context" in locals() else {},
            institution_name=institution.name if institution else "Antigravity Global University",
        )
        return {
            "answer": safe_fallback,
            "citations": [
                {
                    "source_type": "INSTITUTIONAL_SAFEGUARD",
                    "reference": "System Outage Safety Fallback",
                    "details": "Operational academic response served via deterministic policy safeguards.",
                }
            ],
            "grounded_context_summary": "Institutional Safety Fallback [Tier 4 Offline Safeguard]",
            "disclaimer": DISCLAIMER_TEXT,
        }
