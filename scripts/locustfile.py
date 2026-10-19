"""
Locust Load Testing Scenario for Academic Advisor & Degree Planning System.
Simulates concurrent authenticated student and advisor interactions:
- Degree audit requests
- Curriculum exploration
- Unread notification polling
- AI Assistant grounded querying
"""

from locust import HttpUser, between, task


class AcademicPortalUser(HttpUser):
    wait_time = between(1.0, 3.0)

    def on_start(self):
        # Authenticate simulated user session
        login_payload = {
            "username": "alex_student",
            "password": "password123",
        }
        res = self.client.post("/api/auth/login/", json=login_payload)
        if res.status_code == 200:
            self.csrf_token = res.cookies.get("csrftoken", "")
        else:
            self.csrf_token = ""

    @task(3)
    def view_curriculum_catalog(self):
        self.client.get(
            "/api/v1/curricula/",
            headers={"X-CSRFToken": getattr(self, "csrf_token", "")},
            name="Curriculum: List Active",
        )

    @task(4)
    def check_notifications(self):
        self.client.get(
            "/api/v1/notifications/unread-count/",
            headers={"X-CSRFToken": getattr(self, "csrf_token", "")},
            name="Notifications: Unread Count",
        )

    @task(2)
    def query_ai_assistant(self):
        payload = {
            "prompt": "Can I enroll in CS201 next semester?",
        }
        self.client.post(
            "/api/v1/assistant/query/",
            json=payload,
            headers={"X-CSRFToken": getattr(self, "csrf_token", "")},
            name="Assistant: Grounded Query",
        )

    @task(1)
    def view_system_health(self):
        self.client.get(
            "/api/health/",
            name="System Health Check",
        )
