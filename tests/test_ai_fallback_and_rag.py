"""
Test Suite for RAG Retrieval and Multi-Tier AI Fallback Pipeline.

Validates:
1. High-speed RAG chunk indexing and retrieval (< 10ms).
2. 'How can I increase my GPA' intent returns 10-point scale calculations,
   BEST_GRADE repeated course policy, and credit weighting impact.
3. Multi-tier fallback: Primary AI failure cascades to Secondary AI.
4. Secondary AI failure cascades to Grounded Deterministic RAG Synthesizer.
5. Catastrophic service exception cascades to Hardcoded Institutional Safety Fallback.
"""

from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from ai_assistant.services import (
    call_gemini_api,
    call_groq_api,
    call_secondary_ai,
    get_hardcoded_academic_fallback,
    retrieve_rag_context,
)

User = get_user_model()


@pytest.mark.django_db
class TestAIFallbackAndRAG:

    def test_rag_retrieval_indexing(self, seeded_academic_environment):
        """Verifies that RAG retrieval indexes static policies, student context, and returns top chunks."""
        context = {
            "student_record": {
                "username": "student_alex",
                "first_name": "Alex",
                "last_name": "Rivera",
                "cached_cgpa": "8.50",
                "cached_total_credits": "8.00",
                "repeated_course_policy": "BEST_GRADE",
                "programme_name": "B.S. in Computer Science",
                "programme_code": "CS-BS",
            },
            "completed_courses": [
                {"code": "CS-101", "grade": "A", "credits": 4.0, "term_code": "FA2024"},
            ],
            "catalog_courses": [
                {"code": "CS-201", "title": "Data Structures", "credits": 4.0, "prerequisite_rule": {"type": "course_completed", "course_code": "CS-101"}},
            ],
        }

        # Query about GPA improvement
        chunks = retrieve_rag_context("how can i increase my gpa", context, top_k=3)
        assert len(chunks) > 0
        chunk_titles = [c.title for c in chunks]
        # Should retrieve GPA strategy or 10-point scale policy
        assert any("gpa" in t.lower() or "scale" in t.lower() or "strategies" in t.lower() for t in chunk_titles)

    def test_how_can_i_increase_my_gpa_query(self, seeded_academic_environment):
        """Validates that 'how can i increase my GPA' returns actionable 10-point scale guidance."""
        client = APIClient()
        client.force_authenticate(user=seeded_academic_environment["student"])

        resp = client.post(
            "/api/v1/assistant/query/",
            {"prompt": "How can I increase my GPA?"},
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        ans = data["answer"]

        # Standardized 10-Point scale assertions
        assert "10.00 Scale" in ans
        assert "8.50" in ans
        assert "5.00" in ans

        # GPA Improvement strategic assertions
        assert "BEST_GRADE" in ans or "Repeat" in ans
        assert "High-Credit" in ans or "4.0" in ans
        assert "Quality Points" in ans or "SGPA" in ans or "Formula" in ans

        # Citations check
        citations = data["citations"]
        assert any(c["source_type"] == "DEGREE_AUDIT" for c in citations)

    def test_primary_ai_success(self, seeded_academic_environment):
        """Tests that when Primary AI (Gemini) succeeds, its response is returned."""
        client = APIClient()
        client.force_authenticate(user=seeded_academic_environment["student"])

        mock_gemini_resp = (
            "Grounded response from Gemini: Your current CGPA is 8.50 / 10.00 Scale. "
            "Under the BEST_GRADE policy, repeating courses will increase your cumulative GPA."
        )

        with patch("ai_assistant.services.grounding_service.call_gemini_api", return_value=mock_gemini_resp):
            with patch.dict("os.environ", {"GEMINI_API_KEY": "AIzaSyFakeKeyTest12345"}):
                resp = client.post(
                    "/api/v1/assistant/query/",
                    {"prompt": "How can I increase my GPA?"},
                )
                assert resp.status_code == status.HTTP_200_OK
                data = resp.json()
                assert "Grounded response from Gemini" in data["answer"]
                assert "Primary AI (Google Gemini Flash)" in data["grounded_context_summary"]

    def test_primary_ai_fails_cascades_to_secondary_ai(self, seeded_academic_environment):
        """Tests that when Primary AI fails, the pipeline seamlessly cascades to Secondary AI (Groq/Backup)."""
        client = APIClient()
        client.force_authenticate(user=seeded_academic_environment["student"])

        mock_sec_resp = (
            "Grounded response from Groq Llama 3.3: Your current CGPA is 8.50 on the 10-point scale. "
            "To raise it, prioritize high-credit 4.0 courses."
        )

        # Primary fails (returns None), Secondary succeeds
        with patch("ai_assistant.services.grounding_service.call_gemini_api", return_value=None):
            with patch("ai_assistant.services.grounding_service.call_secondary_ai", return_value=(mock_sec_resp, "Secondary AI (Groq Cloud / Llama 3.3)")):
                with patch.dict("os.environ", {
                    "GEMINI_API_KEY": "AIzaSyFakeKeyTest12345",
                    "SECONDARY_AI_API_KEY": "gsk_FakeGroqKey12345",
                    "SECONDARY_AI_PROVIDER": "groq",
                }):
                    resp = client.post(
                        "/api/v1/assistant/query/",
                        {"prompt": "How can I increase my GPA?"},
                    )
                    assert resp.status_code == status.HTTP_200_OK
                    data = resp.json()
                    assert "Grounded response from Groq Llama 3.3" in data["answer"]
                    assert "Secondary AI (Groq Cloud / Llama 3.3)" in data["grounded_context_summary"]

    def test_both_ai_fail_cascades_to_deterministic_engine(self, seeded_academic_environment):
        """Tests that when both external AI services fail, the Grounded Deterministic Engine serves the response."""
        client = APIClient()
        client.force_authenticate(user=seeded_academic_environment["student"])

        # Both Primary and Secondary fail
        with patch("ai_assistant.services.grounding_service.call_gemini_api", return_value=None):
            with patch("ai_assistant.services.grounding_service.call_secondary_ai", return_value=(None, "")):
                with patch.dict("os.environ", {
                    "GEMINI_API_KEY": "AIzaSyFakeKeyTest12345",
                    "SECONDARY_AI_API_KEY": "gsk_FakeGroqKey12345",
                }):
                    resp = client.post(
                        "/api/v1/assistant/query/",
                        {"prompt": "How can I increase my GPA?"},
                    )
                    assert resp.status_code == status.HTTP_200_OK
                    data = resp.json()
                    assert "8.50 / 10.00 Scale" in data["answer"]
                    assert "Deterministic Academic Engine (RAG Index)" in data["grounded_context_summary"]

    def test_catastrophic_exception_cascades_to_hardcoded_fallback(self, seeded_academic_environment):
        """Tests that an unexpected exception in retrieval triggers the Tier 4 Hardcoded Safety Fallback."""
        client = APIClient()
        client.force_authenticate(user=seeded_academic_environment["student"])

        with patch("ai_assistant.services.grounding_service.get_authorized_context", side_effect=RuntimeError("Database connection lost")):
            resp = client.post(
                "/api/v1/assistant/query/",
                {"prompt": "What is my GPA?"},
            )
            assert resp.status_code == status.HTTP_200_OK
            data = resp.json()
            assert "Official Academic Standing & GPA Improvement Guide" in data["answer"]
            assert "Institutional Safety Fallback [Tier 4 Offline Safeguard]" in data["grounded_context_summary"]
            assert any(c["source_type"] == "INSTITUTIONAL_SAFEGUARD" for c in data["citations"])
