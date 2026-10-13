import uuid

import pytest
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.test import Client
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient

from accounts.models import AdvisorAssignment, InstitutionMembership, Role, UserProfile
from accounts.services import assign_advisor, set_user_active_status
from common.models import assert_tenant_scoped
from institutions.models import Department, Institution


@pytest.fixture
def test_setup(db):
    """
    Standard test fixture providing institutions, users, and memberships.
    """
    inst_a = Institution.objects.create(name="Alpha University", code="ALPHA", domain="alpha.edu")
    inst_b = Institution.objects.create(name="Beta College", code="BETA", domain="beta.edu")

    dept_a = Department.objects.create(institution=inst_a, name="Computer Science", code="CS")

    # Users for Alpha University
    student_a1_user = User.objects.create_user(
        username="student_a1", email="student_a1@alpha.edu", password="Password123!"
    )
    student_a2_user = User.objects.create_user(
        username="student_a2", email="student_a2@alpha.edu", password="Password123!"
    )
    advisor_a_user = User.objects.create_user(
        username="advisor_a", email="advisor_a@alpha.edu", password="Password123!"
    )
    coord_a_user = User.objects.create_user(
        username="coord_a", email="coord_a@alpha.edu", password="Password123!"
    )

    student_a1 = InstitutionMembership.objects.create(
        user=student_a1_user, institution=inst_a, role=Role.STUDENT
    )
    student_a2 = InstitutionMembership.objects.create(
        user=student_a2_user, institution=inst_a, role=Role.STUDENT
    )
    advisor_a = InstitutionMembership.objects.create(
        user=advisor_a_user, institution=inst_a, role=Role.ADVISOR
    )
    coord_a = InstitutionMembership.objects.create(
        user=coord_a_user, institution=inst_a, role=Role.COORDINATOR
    )

    # User for Beta College
    student_b_user = User.objects.create_user(
        username="student_b", email="student_b@beta.edu", password="Password123!"
    )
    student_b = InstitutionMembership.objects.create(
        user=student_b_user, institution=inst_b, role=Role.STUDENT
    )

    return {
        "inst_a": inst_a,
        "inst_b": inst_b,
        "dept_a": dept_a,
        "student_a1_user": student_a1_user,
        "student_a2_user": student_a2_user,
        "advisor_a_user": advisor_a_user,
        "coord_a_user": coord_a_user,
        "student_b_user": student_b_user,
        "student_a1": student_a1,
        "student_a2": student_a2,
        "advisor_a": advisor_a,
        "coord_a": coord_a,
        "student_b": student_b,
    }


@pytest.mark.django_db
def test_tenant_scoping_assertion(test_setup):
    """
    Verifies that assert_tenant_scoped helper validates TenantModel subclasses
    and fails on un-scoped models.
    """
    assert assert_tenant_scoped(Department)
    assert assert_tenant_scoped(InstitutionMembership)
    assert assert_tenant_scoped(AdvisorAssignment)

    with pytest.raises(AssertionError):
        assert_tenant_scoped(Institution)

    with pytest.raises(AssertionError):
        assert_tenant_scoped(User)

    inst_a = test_setup["inst_a"]
    dept_qs = Department.objects.for_institution(inst_a)
    assert dept_qs.count() == 1
    assert dept_qs.first().code == "CS"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "method,url",
    [
        ("get", "/api/auth/me/"),
        ("get", "/api/auth/profile/"),
        ("patch", "/api/auth/profile/"),
        ("get", f"/api/institutions/{uuid.uuid4()}/departments/"),
        ("get", f"/api/students/{uuid.uuid4()}/"),
        ("get", "/api/advising/assignments/"),
        ("post", "/api/advising/assignments/"),
        ("post", "/api/curriculum/manage-test/"),
    ],
)
def test_unauthenticated_request_rejected(method, url):
    """
    Acceptance Test 1: Unauthenticated requests to every protected endpoint
    return 401 or 403.
    """
    client = APIClient()
    func = getattr(client, method)
    response = func(url, data={}) if method in ["post", "patch"] else func(url)
    assert response.status_code in [401, 403], f"URL {url} returned {response.status_code}"


@pytest.mark.django_db
def test_student_cannot_read_other_student_same_institution(test_setup):
    """
    Acceptance Test 2: Student A cannot read Student B (same institution) -> 403/404.
    Student can read own record -> 200.
    """
    client = APIClient()
    client.force_authenticate(user=test_setup["student_a1_user"])

    # Attempt to read Student A2 record
    res_other = client.get(f"/api/students/{test_setup['student_a2'].id}/")
    assert res_other.status_code == 403

    # Read own record
    res_self = client.get(f"/api/students/{test_setup['student_a1'].id}/")
    assert res_self.status_code == 200
    assert res_self.json()["username"] == "student_a1"


@pytest.mark.django_db
def test_advisor_cannot_read_unassigned_student_can_read_assigned(test_setup):
    """
    Acceptance Test 3: Advisor cannot read an unassigned student; can read an assigned one.
    """
    inst_a = test_setup["inst_a"]
    advisor_user = test_setup["advisor_a_user"]
    advisor_mem = test_setup["advisor_a"]
    student_1 = test_setup["student_a1"]
    student_2 = test_setup["student_a2"]

    # Assign advisor only to Student 1
    assign_advisor(inst_a, advisor_mem, student_1)

    client = APIClient()
    client.force_authenticate(user=advisor_user)

    # Can read assigned Student 1
    res_assigned = client.get(f"/api/students/{student_1.id}/")
    assert res_assigned.status_code == 200
    assert res_assigned.json()["username"] == "student_a1"

    # Cannot read unassigned Student 2
    res_unassigned = client.get(f"/api/students/{student_2.id}/")
    assert res_unassigned.status_code == 403


@pytest.mark.django_db
def test_cross_institution_lookup_returns_404_no_leak(test_setup):
    """
    Acceptance Test 4: User from institution X requesting a record by institution Y
    identifier -> 404 (no existence leak).
    """
    client = APIClient()
    # Authenticate as coordinator or student of Institution A
    client.force_authenticate(user=test_setup["coord_a_user"])

    # Request student of Institution B
    student_b = test_setup["student_b"]
    response = client.get(f"/api/students/{student_b.id}/")
    # Must be 404 Not Found, not 403, to ensure existence of resource in other tenant is never leaked
    assert response.status_code == 404


@pytest.mark.django_db
def test_student_cannot_elevate_own_role(test_setup):
    """
    Acceptance Test 5: Student cannot change own role via any endpoint
    (PATCH profile with role, membership endpoints).
    """
    client = APIClient()
    student_user = test_setup["student_a1_user"]
    student_mem = test_setup["student_a1"]
    client.force_authenticate(user=student_user)

    # Attempt to inject role, is_staff, is_superuser in profile update
    patch_payload = {
        "preferred_name": "Dr. Hacker",
        "role": "ADMIN",
        "is_staff": True,
        "is_superuser": True,
    }
    response = client.patch("/api/auth/profile/", data=patch_payload, format="json")
    assert response.status_code == 200

    # Verify profile updated legitimate field only
    profile = UserProfile.objects.get(user=student_user)
    assert profile.preferred_name == "Dr. Hacker"

    # Verify role in membership is strictly unchanged
    student_mem.refresh_from_db()
    assert student_mem.role == Role.STUDENT

    # Verify user staff/superuser status is strictly unchanged
    student_user.refresh_from_db()
    assert not student_user.is_staff
    assert not student_user.is_superuser


@pytest.mark.django_db
def test_deactivated_user_cannot_login_and_active_session_invalidated(test_setup):
    """
    Acceptance Test 6: Deactivated user cannot log in and existing sessions stop working.
    """
    user = test_setup["student_a1_user"]
    client = Client()

    # Log in user successfully
    login_success = client.login(username="student_a1", password="Password123!")
    assert login_success is True

    # Active session can access /api/auth/me/
    res_before = client.get("/api/auth/me/")
    assert res_before.status_code == 200

    # Deactivate the user
    set_user_active_status(user, is_active=False)

    # Existing session must be immediately rejected
    res_after = client.get("/api/auth/me/")
    assert res_after.status_code in [401, 403]

    # New login attempt must fail
    res_login = client.post(
        "/api/auth/login/",
        {"username": "student_a1", "password": "Password123!"},
        content_type="application/json",
    )
    assert res_login.status_code == 400


@pytest.mark.django_db
def test_post_without_csrf_rejected_on_cookie_auth(test_setup):
    """
    Acceptance Test 7: POST without CSRF token on cookie-authenticated endpoints -> rejected.
    """
    client = Client(enforce_csrf_checks=True)
    logged_in = client.login(username="student_a1", password="Password123!")
    assert logged_in is True

    # Attempt POST to logout without CSRF token header
    response = client.post("/api/auth/logout/")
    assert response.status_code == 403
    assert b"CSRF" in response.content or b"csrf" in response.content or response.status_code == 403


@pytest.mark.django_db
def test_login_throttling_and_no_credential_leak():
    """
    Acceptance Test 8: Login throttling triggers after configured attempts;
    response bodies never contain hashes, tokens, or session IDs.
    """
    client = APIClient()

    # Attempt rapid invalid logins (configured rate is 5/minute)
    responses = []
    for _ in range(7):
        resp = client.post(
            "/api/auth/login/",
            {"username": "nonexistent", "password": "wrongpassword"},
            format="json",
        )
        responses.append(resp)

    # Verify that at least one request triggered 429 Too Many Requests
    status_codes = [r.status_code for r in responses]
    assert 429 in status_codes, f"Expected 429 status code in {status_codes}"

    # Verify no response body leaks sensitive internal data
    for r in responses:
        body_text = r.content.decode("utf-8")
        assert "pbkdf2" not in body_text
        assert "argon2" not in body_text
        assert "bcrypt" not in body_text
        assert "session_key" not in body_text
        assert "SECRET_KEY" not in body_text


@pytest.mark.django_db
def test_coordinator_institution_x_cannot_manage_institution_y(test_setup):
    """
    Acceptance Test 9: Coordinator of institution X cannot manage institution Y.
    """
    client = APIClient()
    client.force_authenticate(user=test_setup["coord_a_user"])

    inst_x = test_setup["inst_a"]
    inst_y = test_setup["inst_b"]

    # Manage own institution -> Authorized (200)
    res_x = client.post(
        "/api/curriculum/manage-test/", {"institution_id": str(inst_x.id)}, format="json"
    )
    assert res_x.status_code == 200

    # Manage foreign institution -> Denied (403)
    res_y = client.post(
        "/api/curriculum/manage-test/", {"institution_id": str(inst_y.id)}, format="json"
    )
    assert res_y.status_code == 403


@pytest.mark.django_db
def test_password_reset_enumeration_protection_and_token_flow(test_setup):
    """
    Acceptance Test 10: Password reset endpoints do not leak user existence,
    and valid token allows password change.
    """
    client = APIClient()

    # Request reset for real email
    res_real = client.post(
        "/api/auth/password-reset/", {"email": "student_a1@alpha.edu"}, format="json"
    )
    assert res_real.status_code == 200

    # Request reset for non-existent email
    res_fake = client.post(
        "/api/auth/password-reset/", {"email": "nobody@nowhere.com"}, format="json"
    )
    assert res_fake.status_code == 200

    # Identical responses prevent enumeration
    assert res_real.json() == res_fake.json()

    # Confirm flow with valid token
    user = test_setup["student_a1_user"]
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))

    res_confirm = client.post(
        "/api/auth/password-reset/confirm/",
        {
            "uid": uid,
            "token": token,
            "new_password": "NewSecretPassword456!",
        },
        format="json",
    )
    assert res_confirm.status_code == 200

    # Verify user can log in with new password
    auth_client = Client()
    assert auth_client.login(username="student_a1", password="NewSecretPassword456!") is True
