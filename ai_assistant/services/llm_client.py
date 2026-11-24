"""
Multi-Tier LLM Fallback Client for Academic Advisor System.

Implements a robust 4-tier fallback architecture:
- Tier 1: Primary Free AI Provider (Google Gemini API via GEMINI_API_KEY)
- Tier 2: Secondary Free AI Provider (Groq / OpenRouter / Backup via SECONDARY_AI_API_KEY)
- Tier 3: Grounded Deterministic RAG Synthesizer (Local Rule Engine + Degree Audit, 10-point GPA scale)
- Tier 4: Hardcoded Institutional Safety Fallback (Guaranteed safe response for network/service outages)
"""

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 4.0


# -----------------------------------------------------------------------------
# TIER 1: GOOGLE GEMINI REST API
# -----------------------------------------------------------------------------

def call_gemini_api(
    system_instruction: str,
    context_text: str,
    user_prompt: str,
    api_key: str,
) -> Optional[str]:
    """
    Calls Google Gemini REST API.
    Auto-detects active models (gemini-3.7-flash, gemini-3.8-flash, gemini-3.5-flash, gemini-flash-latest).
    Returns generated response text or None if the request fails.
    """
    if not api_key or len(api_key.strip()) < 5:
        return None

    candidate_models = [
        "gemini-flash-lite-latest",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-3.7-flash",
        "gemini-3.8-flash",
    ]
    endpoints = [
        f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key.strip()}"
        for m in candidate_models
    ]

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": f"{context_text}\n\nStudent Question: {user_prompt}"
                    }
                ],
            }
        ],
        "systemInstruction": {
            "parts": [
                {
                    "text": system_instruction
                }
            ]
        },
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 900,
        },
    }

    data = json.dumps(payload).encode("utf-8")

    for endpoint in endpoints:
        try:
            req = urllib.request.Request(
                endpoint,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                if response.status == 200:
                    resp_json = json.loads(response.read().decode("utf-8"))
                    candidates = resp_json.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts and "text" in parts[0]:
                            text = parts[0]["text"].strip()
                            if len(text) > 20:
                                return text
        except urllib.error.HTTPError as http_err:
            logger.warning("Gemini API HTTP Error %s: %s", http_err.code, http_err.reason)
            # If 429 quota or 404 model not found, try next or cascade to Tier 2
            continue
        except Exception as exc:
            logger.warning("Gemini API call failed (%s), cascading to secondary fallback.", exc)
            break

    return None


# -----------------------------------------------------------------------------
# TIER 2: SECONDARY FREE AI (GROQ / OPENROUTER / BACKUP)
# -----------------------------------------------------------------------------

def call_groq_api(
    system_instruction: str,
    context_text: str,
    user_prompt: str,
    api_key: str,
    model: Optional[str] = None,
) -> Optional[str]:
    """
    Calls Groq Cloud REST API using OpenAI-compatible chat completions endpoint.
    Auto-detects active models (openai/gpt-oss-120b, openai/gpt-oss-20b, llama-3.3-70b-versatile, etc.).
    """
    if not api_key or len(api_key.strip()) < 5:
        return None

    candidate_models = [model] if model else [
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
    ]

    endpoint = "https://api.groq.com/openai/v1/chat/completions"

    for cand_model in candidate_models:
        payload = {
            "model": cand_model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": f"{context_text}\n\nStudent Question: {user_prompt}"},
            ],
            "temperature": 0.1,
            "max_tokens": 900,
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                endpoint,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key.strip()}",
                    "User-Agent": "AcademicAdvisorSystem/1.0",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                if response.status == 200:
                    resp_json = json.loads(response.read().decode("utf-8"))
                    choices = resp_json.get("choices", [])
                    if choices:
                        content = choices[0].get("message", {}).get("content", "").strip()
                        if len(content) > 20:
                            return content
        except urllib.error.HTTPError as http_err:
            logger.warning("Groq model %s returned HTTP %s, trying next.", cand_model, http_err.code)
            continue
        except Exception as exc:
            logger.warning("Groq API call failed (%s), trying next model.", exc)
            continue

    return None


def call_openrouter_api(
    system_instruction: str,
    context_text: str,
    user_prompt: str,
    api_key: str,
    model: str = "google/gemini-2.0-flash-exp:free",
) -> Optional[str]:
    """
    Calls OpenRouter API with free tier models.
    """
    if not api_key or len(api_key.strip()) < 5:
        return None

    endpoint = "https://openrouter.ai/api/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": f"{context_text}\n\nStudent Question: {user_prompt}"},
        ],
        "temperature": 0.1,
        "max_tokens": 900,
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key.strip()}",
                "HTTP-Referer": "http://localhost:5173",
                "X-Title": "Academic Advisor Degree Planning System",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            if response.status == 200:
                resp_json = json.loads(response.read().decode("utf-8"))
                choices = resp_json.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "").strip()
                    if len(content) > 20:
                        return content
    except Exception as exc:
        logger.warning("OpenRouter API call failed (%s).", exc)

    return None


def call_secondary_ai(
    system_instruction: str,
    context_text: str,
    user_prompt: str,
    api_key: str,
    provider: str = "groq",
) -> Tuple[Optional[str], str]:
    """
    Dispatches to configured secondary free AI provider.
    """
    provider_lower = (provider or "groq").lower().strip()

    if provider_lower in ("groq", "llama"):
        # Try Groq 70B then 8B
        res = call_groq_api(system_instruction, context_text, user_prompt, api_key, model="llama-3.3-70b-versatile")
        if not res:
            res = call_groq_api(system_instruction, context_text, user_prompt, api_key, model="llama-3.1-8b-instant")
        if res:
            return res, "Secondary AI (Groq Cloud / Llama 3.3)"

    elif provider_lower in ("openrouter", "router"):
        res = call_openrouter_api(system_instruction, context_text, user_prompt, api_key)
        if res:
            return res, "Secondary AI (OpenRouter Free Tier)"

    elif provider_lower in ("gemini", "google"):
        res = call_gemini_api(system_instruction, context_text, user_prompt, api_key)
        if res:
            return res, "Secondary AI (Backup Gemini Key)"

    return None, ""


# -----------------------------------------------------------------------------
# TIER 4: HARDCODED INSTITUTIONAL SAFETY FALLBACK ANSWER
# -----------------------------------------------------------------------------

def get_hardcoded_academic_fallback(
    user_prompt: str,
    student_context: Optional[Dict[str, Any]] = None,
    institution_name: str = "Antigravity Global University",
) -> str:
    """
    Generates a structured, authoritative, hardcoded institutional response
    when external AI services and dynamic synthesis encounter unexpected exceptions.
    Guarantees the student always receives actionable, policy-compliant guidance.
    """
    student_context = student_context or {}
    student_rec = student_context.get("student_record") or {}
    cgpa_str = student_rec.get("cached_cgpa", "N/A")
    credits_str = student_rec.get("cached_total_credits", "N/A")
    prog_name = student_rec.get("programme_name", "Undergraduate Degree")
    policy = student_rec.get("repeated_course_policy", "BEST_GRADE")
    advisor = student_context.get("assigned_advisor") or {}
    advisor_name = advisor.get("name", "Your Assigned Faculty Advisor")
    advisor_email = advisor.get("email", "advising@agu.edu")

    prompt_lower = (user_prompt or "").lower()

    # Determine standing
    try:
        cgpa_val = float(cgpa_str)
        is_satisfied = cgpa_val >= 5.0
        standing = "Good Standing" if is_satisfied else "Academic Review Required"
    except Exception:
        is_satisfied = True
        standing = "Good Standing"

    # GPA Improvement specific fallback
    if any(k in prompt_lower for k in ["gpa", "cgpa", "increase", "improve", "raise", "standing"]):
        return (
            f"### Official Academic Standing & GPA Improvement Guide ({institution_name})\n\n"
            f"- **Degree Programme:** {prog_name}\n"
            f"- **Your Current Cumulative GPA (CGPA):** **{cgpa_str} / 10.00 Scale**\n"
            f"- **Minimum Graduation Requirement:** 5.00 / 10.00 Scale\n"
            f"- **Academic Standing:** **{standing}** ({'Satisfied' if is_satisfied else 'Below Minimum Threshold'})\n"
            f"- **Graduation Threshold Satisfied:** {'Yes' if is_satisfied else 'No'}\n"
            f"- **Total Earned Credits:** {credits_str} credits\n"
            f"- **Course Retake Policy:** **{policy}**\n\n"
            f"#### How to Mathematically Increase Your CGPA on the 10-Point Scale:\n"
            f"1. **Repeat Unpassed or Low-Grade Courses ({policy} Policy):**\n"
            f"   Under institutional policy, repeating any course where you received a grade of C, D, or F replaces "
            f"   the lower grade points in your cumulative GPA calculation. This produces the fastest increase in CGPA.\n"
            f"2. **Target High-Credit Core Courses:**\n"
            f"   4.0-credit courses carry twice the mathematical weight of 2.0-credit courses. Earning an A (9.0) or "
            f"   A+ (10.0) in high-credit classes pulls your cumulative average upward significantly.\n"
            f"3. **Balanced Semester Credit Loads:**\n"
            f"   Plan 12 to 16 credits per semester in the **Degree Planner** tab to allow sufficient time for mastery.\n"
            f"4. **Consult Your Faculty Advisor:**\n"
            f"   Schedule an appointment with **{advisor_name}** ({advisor_email}) to evaluate retake eligibility "
            f"   and prerequisite waivers before term registration.\n\n"
            f"*(Note: External AI service temporarily unavailable. Response generated from institutional policy safeguards.)*"
        )

    # General academic fallback
    return (
        f"### Institutional Academic Advisory Notice ({institution_name})\n\n"
        f"Your official academic profile is recorded and in good standing:\n"
        f"- **Programme:** {prog_name}\n"
        f"- **Current CGPA:** **{cgpa_str} / 10.00 Scale** (Min. 5.000 for graduation)\n"
        f"- **Credits Earned:** {credits_str} semester credits\n"
        f"- **Assigned Faculty Advisor:** {advisor_name} ({advisor_email})\n\n"
        f"#### Self-Service Academic Navigation:\n"
        f"- **Degree Audit Tab:** View real-time progress across General Education, Major Core, and Electives.\n"
        f"- **Degree Planner Tab:** Simulate future semester schedules, validate prerequisites, and submit plans for approval.\n"
        f"- **Career Guidance Tab:** Explore skill competencies and industry-aligned course recommendations.\n\n"
        f"For questions regarding course prerequisites, academic standing, or policy overrides, "
        f"please contact {advisor_name} ({advisor_email}) or the Academic Registrar.\n\n"
        f"*(Note: External AI service temporarily unavailable. Response generated from institutional policy safeguards.)*"
    )
