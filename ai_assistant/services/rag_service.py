"""
Retrieval-Augmented Generation (RAG) Service for Academic Advisor System.

Provides high-speed, in-memory semantic & keyword chunk retrieval grounded in:
1. Standardized 1.00 – 10.00 GPA grading regulations & GPA improvement strategies.
2. Official institutional degree requirements, prerequisite structures, and repeated-course policies.
3. Live, authorized student academic records (transcripts, degree audit, advisor assignments, plans).
"""

import math
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class RAGChunk:
    chunk_id: str
    category: str  # "POLICY", "CATALOG", "PROGRAMME", "STUDENT_CONTEXT", "GPA_STRATEGY"
    title: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0


# -----------------------------------------------------------------------------
# STATIC INSTITUTIONAL KNOWLEDGE BASE (POLICIES, 10-POINT SCALE, GPA STRATEGY)
# -----------------------------------------------------------------------------

STATIC_POLICY_CHUNKS = [
    RAGChunk(
        chunk_id="policy_gpa_scale_10pt",
        category="POLICY",
        title="1.00 – 10.00 Scale Grading Regulations",
        content=(
            "The institution standardizes all academic evaluations on a 1.00 – 10.00 GPA Scale. "
            "Letter grades and grade points: A+ = 10.0, A = 9.0, A- = 8.5, B+ = 8.0, B = 7.0, B- = 6.5, "
            "C+ = 6.0, C = 5.0, C- = 4.5, D+ = 4.0, D = 3.0, F = 0.0. "
            "Passing grade threshold for prerequisites is C (5.0) or higher. "
            "Minimum Cumulative GPA (CGPA) required for graduation is 5.000 / 10.00. "
            "Students with CGPA >= 5.000 are in Good Academic Standing. "
            "Students with CGPA < 5.000 are placed under Academic Review / Probation."
        ),
        metadata={"source": "Institutional Academic Regulations", "scale": "10-point"},
    ),
    RAGChunk(
        chunk_id="policy_gpa_improvement_strategies",
        category="GPA_STRATEGY",
        title="Strategies to Increase and Maximize Cumulative GPA (CGPA)",
        content=(
            "Actionable methods to improve CGPA on the 10-point scale:\n"
            "1. Retake Unpassed or Low-Grade Courses (Best Grade Policy): Under the institutional BEST_GRADE repeated-course policy, "
            "retaking a course where a grade of F, D, or C was earned replaces the previous lower grade points in the CGPA calculation, "
            "providing the single fastest mathematical increase in cumulative GPA.\n"
            "2. Focus on High-Credit Courses: A 4.0-credit course has double the mathematical weight of a 2.0-credit course. "
            "Achieving an A (9.0) or A+ (10.0) in 4-credit courses (such as core computer science and math classes) boosts CGPA significantly.\n"
            "3. Balanced Semester Credit Loads: Keep semester workloads between 12 and 16 credits to allocate sufficient study time per course.\n"
            "4. Prerequisite Sequencing: Ensure all foundational prerequisites are thoroughly mastered before taking advanced technical electives.\n"
            "5. Faculty Advising & Academic Support: Consult with your assigned faculty advisor to identify courses best aligned with your strengths."
        ),
        metadata={"source": "Academic Advising Guidelines", "topic": "GPA Improvement"},
    ),
    RAGChunk(
        chunk_id="policy_repeated_courses",
        category="POLICY",
        title="Repeated Course & Grade Replacement Policy",
        content=(
            "The university applies the BEST_GRADE repeated course policy. "
            "When a student repeats an eligible course, the highest grade earned is counted toward cumulative GPA and credit totals. "
            "The previous attempt remains recorded on the academic transcript with an exclusion code, preventing it from reducing CGPA."
        ),
        metadata={"source": "Registrar Policy Manual", "topic": "Course Repeats"},
    ),
    RAGChunk(
        chunk_id="policy_graduation_requirements",
        category="POLICY",
        title="Undergraduate Degree Graduation Criteria",
        content=(
            "To qualify for graduation, students must complete at least 120 semester credits, "
            "satisfy all General Education, Mathematics & Science, Major Core, Technical Elective, and Capstone requirement groups, "
            "maintain a minimum 5.000 CGPA on the 10-point scale, and complete the Senior Capstone Design sequence (CS480 & CS481)."
        ),
        metadata={"source": "Curriculum Handbook", "topic": "Graduation"},
    ),
    RAGChunk(
        chunk_id="policy_advising_roles",
        category="POLICY",
        title="Faculty Advising and Plan Reviews",
        content=(
            "Each student is assigned a dedicated Faculty Academic Advisor. "
            "Advisors review multi-semester degree plans, evaluate prerequisite override requests, "
            "monitor academic risk alerts, and provide career mentorship. "
            "Degree plans must be submitted to the assigned advisor for formal approval before enrollment registration."
        ),
        metadata={"source": "Faculty Handbook", "topic": "Advising"},
    ),
]


# -----------------------------------------------------------------------------
# FAST IN-MEMORY RAG RETRIEVER WITH CACHING
# -----------------------------------------------------------------------------

# In-memory query cache: (cache_key) -> (timestamp, List[RAGChunk])
_RAG_QUERY_CACHE: Dict[str, Tuple[float, List[RAGChunk]]] = {}
CACHE_TTL_SECONDS = 30.0  # 30-second TTL for repeat queries


def _tokenize(text: str) -> List[str]:
    """Tokenizes text into normalized keywords and alphanumeric course tokens."""
    tokens = re.findall(r"\b[a-zA-Z0-9_-]+\b", text.lower())
    # Strip hyphens and underscores for course code matching (e.g. cs-201 -> cs201)
    expanded = []
    for t in tokens:
        expanded.append(t)
        cleaned = re.sub(r"[-_]", "", t)
        if cleaned != t:
            expanded.append(cleaned)
    return expanded


def build_student_dynamic_chunks(student_context: Dict[str, Any]) -> List[RAGChunk]:
    """
    Constructs authorized, dynamic RAG chunks from student academic records.
    """
    chunks: List[RAGChunk] = []
    student_rec = student_context.get("student_record")
    if not student_rec:
        return chunks

    username = student_rec.get("username", "student")
    cgpa = student_rec.get("cached_cgpa", "0.00")
    total_cr = student_rec.get("cached_total_credits", "0.00")
    prog_name = student_rec.get("programme_name", "Degree Programme")
    prog_code = student_rec.get("programme_code", "PROG")
    policy = student_rec.get("repeated_course_policy", "BEST_GRADE")

    # 1. Student Academic Profile & Standing Chunk
    try:
        cgpa_num = float(cgpa)
        standing = "Good Standing" if cgpa_num >= 5.0 else "Academic Review Required"
    except Exception:
        standing = "Good Standing"

    chunks.append(
        RAGChunk(
            chunk_id=f"student_standing_{username}",
            category="STUDENT_CONTEXT",
            title=f"Student Academic Standing & CGPA for {student_rec.get('first_name', username)}",
            content=(
                f"Student: {student_rec.get('first_name')} {student_rec.get('last_name')} ({username})\n"
                f"Degree Programme: {prog_name} ({prog_code})\n"
                f"Cumulative GPA: {cgpa} / 10.00 Scale\n"
                f"Total Earned Credits: {total_cr} credits\n"
                f"Academic Standing: {standing} (Minimum required: 5.000 / 10.00)\n"
                f"Enrollment Term: {student_rec.get('enrollment_term', 'FA2024')}\n"
                f"Repeated Course Policy: {policy}"
            ),
            metadata={"student_username": username, "cgpa": cgpa, "standing": standing},
        )
    )

    # 2. Completed Courses Chunk
    completed = student_context.get("completed_courses", [])
    if completed:
        courses_str = ", ".join(
            [f"{c['code']} (Grade: {c.get('grade', 'P')}, {c.get('credits', 3)} cr, Term: {c.get('term_code', 'N/A')})" for c in completed]
        )
        chunks.append(
            RAGChunk(
                chunk_id=f"student_completed_{username}",
                category="STUDENT_CONTEXT",
                title="Completed Course Transcript History",
                content=(
                    f"Completed Courses ({len(completed)} total): {courses_str}\n"
                    f"All listed courses count toward degree requirements and satisfy prerequisite checks."
                ),
                metadata={"course_count": len(completed), "codes": [c["code"] for c in completed]},
            )
        )

    # 3. In-Progress & Failed Courses Chunk
    in_prog = student_context.get("in_progress_courses", [])
    failed = student_context.get("failed_courses", [])
    if in_prog or failed:
        in_prog_str = ", ".join([f"{c['code']} ({c['title']})" for c in in_prog]) if in_prog else "None"
        failed_str = ", ".join([f"{c['code']} ({c['title']}, Grade: F in {c.get('term_code', 'N/A')})" for c in failed]) if failed else "None"
        chunks.append(
            RAGChunk(
                chunk_id=f"student_current_status_{username}",
                category="STUDENT_CONTEXT",
                title="Current Enrollment & Retake Opportunities",
                content=(
                    f"Currently Enrolled Courses: {in_prog_str}\n"
                    f"Unpassed / Failed Courses Eligible for Retake: {failed_str}\n"
                    f"Under the {policy} policy, repeating unpassed courses replaces failing grade points in CGPA."
                ),
                metadata={"in_progress_count": len(in_prog), "failed_count": len(failed)},
            )
        )

    # 4. Degree Audit Chunk
    audit = student_context.get("degree_audit")
    if audit:
        earned = audit.get("total_credits_earned") or audit.get("earned_credits", total_cr)
        req = audit.get("total_credits_required") or audit.get("required_credits", "120")
        is_sat = audit.get("is_degree_satisfied", False)
        chunks.append(
            RAGChunk(
                chunk_id=f"student_audit_{username}",
                category="STUDENT_CONTEXT",
                title="Official Degree Audit Progress",
                content=(
                    f"Degree Requirements Audit for {prog_name}:\n"
                    f"Overall Degree Satisfied: {'Yes' if is_sat else 'No (In Progress)'}\n"
                    f"Credits Completed: {earned} / {req} credits\n"
                    f"Minimum CGPA Threshold: {audit.get('min_cgpa_required', '5.000')} / 10.00 (Current: {cgpa})"
                ),
                metadata={"satisfied": is_sat, "earned": earned, "required": req},
            )
        )

    # 5. Assigned Advisor Chunk
    advisor = student_context.get("assigned_advisor")
    if advisor:
        chunks.append(
            RAGChunk(
                chunk_id=f"student_advisor_{username}",
                category="STUDENT_CONTEXT",
                title="Assigned Faculty Academic Advisor",
                content=(
                    f"Assigned Advisor: {advisor.get('name')}\n"
                    f"Email: {advisor.get('email')}\n"
                    f"Department: {advisor.get('department', 'Faculty of Engineering')}\n"
                    "Students may schedule advising consultations for plan review and prerequisite approvals."
                ),
                metadata={"advisor_name": advisor.get("name"), "email": advisor.get("email")},
            )
        )

    return chunks


def build_catalog_chunks(catalog_courses: List[Dict[str, Any]]) -> List[RAGChunk]:
    """Creates chunks for catalog courses with their prerequisite rules."""
    chunks = []
    for c in catalog_courses:
        code = c.get("code", "")
        title = c.get("title", "")
        cr = c.get("credits", "3.0")
        desc = c.get("description", "")
        rule = c.get("prerequisite_rule")
        rule_desc = "None"
        if rule:
            rule_desc = f"Rule Type: {rule.get('type')}, Requires: {rule.get('course_code') or rule.get('min_credits') or rule.get('min_cgpa') or 'Compound Rule'}"

        chunks.append(
            RAGChunk(
                chunk_id=f"course_{code.lower()}",
                category="CATALOG",
                title=f"Course Catalog: {code} - {title}",
                content=(
                    f"Course Code: {code}\n"
                    f"Title: {title} ({cr} credits)\n"
                    f"Description: {desc}\n"
                    f"Prerequisites: {rule_desc}"
                ),
                metadata={"course_code": code, "credits": cr},
            )
        )
    return chunks


def score_chunk(query_tokens: List[str], chunk: RAGChunk, query_text: str) -> float:
    """
    Computes a hybrid relevance score for a RAG chunk against query tokens and intent keywords.
    """
    chunk_text = f"{chunk.title} {chunk.content}".lower()
    score = 0.0

    # Token match scoring
    for token in query_tokens:
        if len(token) <= 2:
            continue
        # Exact word match
        if re.search(r"\b" + re.escape(token) + r"\b", chunk_text):
            score += 3.0
        elif token in chunk_text:
            score += 1.0

    # High-intent boosts
    q_lower = query_text.lower()

    # GPA / Increase / Standing intent
    if any(k in q_lower for k in ["gpa", "cgpa", "increase", "improve", "raise", "standing", "scale", "probation"]):
        if chunk.category in ("GPA_STRATEGY", "POLICY") and "gpa" in chunk.chunk_id:
            score += 12.0
        if chunk.category == "STUDENT_CONTEXT" and "standing" in chunk.chunk_id:
            score += 10.0
        if "increase" in q_lower or "improve" in q_lower or "raise" in q_lower:
            if chunk.chunk_id == "policy_gpa_improvement_strategies":
                score += 20.0
            if "retake" in chunk_text or "repeated" in chunk_text:
                score += 8.0

    # Advisor intent
    if any(k in q_lower for k in ["advisor", "advise", "counselor", "who is my advisor"]):
        if "advisor" in chunk.chunk_id:
            score += 15.0

    # Prerequisite / Course intent
    for token in query_tokens:
        # If token looks like a course code (e.g. cs101, math102)
        if re.match(r"^[a-zA-Z]{2,4}\d{3}$", token):
            if token in chunk.chunk_id:
                score += 25.0
            elif token in chunk_text:
                score += 8.0

    # Graduation / Progress intent
    if any(k in q_lower for k in ["graduate", "graduation", "progress", "audit", "remaining credits"]):
        if "audit" in chunk.chunk_id or "graduation" in chunk.chunk_id:
            score += 12.0

    return score


def retrieve_rag_context(
    query: str,
    student_context: Dict[str, Any],
    top_k: int = 5,
) -> List[RAGChunk]:
    """
    Retrieves the top-k most relevant RAG knowledge chunks for a query.
    Uses in-memory scoring with TTL-based query caching for sub-millisecond retrieval.
    """
    cache_key = f"{student_context.get('student_record', {}).get('username', 'anon')}_{query.strip().lower()}"
    now = time.time()

    # Check cache
    if cache_key in _RAG_QUERY_CACHE:
        cache_time, cached_chunks = _RAG_QUERY_CACHE[cache_key]
        if now - cache_time < CACHE_TTL_SECONDS:
            return cached_chunks

    # Build corpus
    corpus: List[RAGChunk] = []
    corpus.extend(STATIC_POLICY_CHUNKS)
    corpus.extend(build_student_dynamic_chunks(student_context))
    corpus.extend(build_catalog_chunks(student_context.get("catalog_courses", [])))

    query_tokens = _tokenize(query)

    # Score chunks
    scored_chunks: List[RAGChunk] = []
    for chunk in corpus:
        s = score_chunk(query_tokens, chunk, query)
        if s > 0:
            chunk.score = s
            scored_chunks.append(chunk)

    # Sort descending by score
    scored_chunks.sort(key=lambda c: c.score, reverse=True)
    results = scored_chunks[:top_k]

    # Save to cache
    _RAG_QUERY_CACHE[cache_key] = (now, results)
    return results


def format_rag_context_for_prompt(chunks: List[RAGChunk]) -> str:
    """Formats retrieved RAG chunks into clean markdown text for the LLM prompt."""
    if not chunks:
        return "No specific institutional knowledge chunks retrieved."

    lines = ["### Retrieved Institutional & Academic Context:"]
    for i, c in enumerate(chunks, 1):
        lines.append(f"\n[{i}] **{c.title}** (Source: {c.metadata.get('source', c.category)})")
        lines.append(c.content.strip())
    return "\n".join(lines)


def format_rag_citations(chunks: List[RAGChunk]) -> List[Dict[str, str]]:
    """Converts RAG chunks to the platform citation format."""
    citations = []
    seen = set()
    for c in chunks:
        ref = c.title
        if ref in seen:
            continue
        seen.add(ref)
        citations.append({
            "source_type": f"RAG_{c.category}",
            "reference": c.title,
            "details": f"Relevance Score: {c.score:.1f}. {c.content[:140]}...",
        })
    return citations
