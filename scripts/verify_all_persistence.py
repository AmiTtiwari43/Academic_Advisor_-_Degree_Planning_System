import os
import sys
import django
import uuid
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from django.db import connection, transaction
from django.contrib.auth.models import User
from accounts.models import UserProfile, Role, InstitutionMembership
from accounts.services import update_user_profile
from planning.models import Plan, PlanItem, PlanStatus, PlanVersion, PlanVersionStatus
from planning.services.plan_management_service import add_course_to_plan, remove_course_from_plan
from planning.services.snapshot_service import create_plan_version_snapshot
from planning.services.workflow_service import start_review, approve_plan_version
from career_mapping.models import CareerObjective, StudentCareerPreference
from notifications.models import Notification, NotificationEventType, ReadStatus
from institutions.models import Institution
from curriculum.models import Course
from academic_records.models import StudentRecord, AcademicTerm

def verify_all_persistence():
    print("==================================================")
    print("VERIFYING DATABASE PERSISTENCE ACROSS ALL UPDATES")
    print("==================================================")

    # 1. PROFILE UPDATE PERSISTENCE
    print("\n[1] Testing Profile Update Persistence...")
    user = User.objects.filter(username="student_alex").first()
    assert user, "User student_alex must exist"

    test_first = "Alexander"
    test_last = "Rivera-Verified"
    test_pref = "Alex Verified"
    test_phone = "+1 (555) 777-9999"
    test_email = "alex.verified@agu.edu"

    update_user_profile(
        user=user,
        first_name=test_first,
        last_name=test_last,
        preferred_name=test_pref,
        phone_number=test_phone,
        email=test_email,
    )

    # Direct raw SQL query to bypass Django ORM cache and verify physical on-disk persistence
    with connection.cursor() as cur:
        cur.execute("SELECT first_name, last_name, email FROM auth_user WHERE username = %s", [user.username])
        raw_user = cur.fetchone()
        assert raw_user[0] == test_first, f"Expected first_name {test_first}, got {raw_user[0]}"
        assert raw_user[1] == test_last, f"Expected last_name {test_last}, got {raw_user[1]}"
        assert raw_user[2] == test_email, f"Expected email {test_email}, got {raw_user[2]}"

        cur.execute(
            "SELECT p.phone_number, p.preferred_name FROM accounts_userprofile p "
            "JOIN auth_user u ON p.user_id = u.id WHERE u.username = %s",
            [user.username]
        )
        raw_prof = cur.fetchone()
        assert raw_prof[0] == test_phone, f"Expected phone_number {test_phone}, got {raw_prof[0]}"
        assert raw_prof[1] == test_pref, f"Expected preferred_name {test_pref}, got {raw_prof[1]}"

    print("   -> Profile updates persisted in physical database on disk! PASS")

    # 2. DEGREE PLAN ITEM ADDITION & REMOVAL PERSISTENCE
    print("\n[2] Testing Degree Plan Mutation Persistence...")
    plan = Plan.objects.filter(student_record__student=user).first()
    assert plan, "Degree plan for student_alex must exist"
    
    # Create or retrieve a test plan in DRAFT status
    test_plan, _ = Plan.objects.get_or_create(
        institution=plan.institution,
        student_record=plan.student_record,
        name="Persistence Test Plan",
        defaults={"curriculum_version": plan.curriculum_version, "is_primary": False, "status": PlanStatus.DRAFT}
    )
    test_plan.status = PlanStatus.DRAFT
    test_plan.save(update_fields=["status"])

    course = Course.objects.filter(
        institution=plan.institution,
        requirement_groups__curriculum_version=plan.curriculum_version
    ).exclude(plan_items__plan=test_plan).first()
    term = AcademicTerm.objects.filter(institution=plan.institution).first()

    if course and term:
        # Add item
        item = add_course_to_plan(
            plan=test_plan,
            course=course,
            planned_term=term,
            term_index=3,
            position=99,
        )
        item_id = str(item.id)

        # Verify via direct SQL using hex id for SQLite
        hex_item_id = item.id.hex if hasattr(item.id, "hex") else str(item.id).replace("-", "")
        with connection.cursor() as cur:
            cur.execute("SELECT id, term_index, position FROM planning_planitem WHERE id = %s", [hex_item_id])
            raw_item = cur.fetchone()
            assert raw_item is not None, "PlanItem must exist in database table planning_planitem"
            assert raw_item[1] == 3, f"Expected term_index 3, got {raw_item[1]}"

        # Remove item
        remove_course_from_plan(plan=test_plan, plan_item_id=str(item.id))
        with connection.cursor() as cur:
            cur.execute("SELECT id FROM planning_planitem WHERE id = %s", [hex_item_id])
            assert cur.fetchone() is None, "PlanItem must be deleted from database table"

        print("   -> Plan item add/remove mutations persisted in database! PASS")

    # 3. WORKFLOW PLAN REVIEW & APPROVAL PERSISTENCE
    print("\n[3] Testing Plan Review Decision & Approval Persistence...")
    advisor_user = User.objects.filter(username="advisor_alice").first()
    if advisor_user:
        # Submit snapshot version
        ver = create_plan_version_snapshot(
            plan=plan,
            submitted_by=user,
            submission_note="Test submission for persistence check",
        )
        ver_id = str(ver.id)

        # Start review and approve version
        start_review(plan=plan, version=ver, advisor=advisor_user)
        dec = approve_plan_version(
            plan=plan,
            version=ver,
            advisor=advisor_user,
            comments="Persistence verification approval notes",
        )

        hex_ver_id = ver.id.hex if hasattr(ver.id, "hex") else str(ver.id).replace("-", "")
        hex_plan_id = plan.id.hex if hasattr(plan.id, "hex") else str(plan.id).replace("-", "")

        with connection.cursor() as cur:
            cur.execute("SELECT status FROM planning_planversion WHERE id = %s", [hex_ver_id])
            raw_ver_status = cur.fetchone()[0]
            assert raw_ver_status == PlanVersionStatus.APPROVED, f"Expected APPROVED, got {raw_ver_status}"

            cur.execute("SELECT status FROM planning_plan WHERE id = %s", [hex_plan_id])
            raw_plan_status = cur.fetchone()[0]
            assert raw_plan_status == PlanStatus.APPROVED, f"Expected APPROVED, got {raw_plan_status}"

            cur.execute("SELECT action, comments FROM planning_planreviewdecision WHERE plan_version_id = %s ORDER BY created_at DESC", [hex_ver_id])
            raw_dec = cur.fetchone()
            assert raw_dec is not None, "Review decision must be written to planning_planreviewdecision"
            assert raw_dec[0] == "APPROVE", f"Expected APPROVE, got {raw_dec[0]}"

        print("   -> Plan review decisions & approvals persisted in database! PASS")

    # 4. CAREER PREFERENCE PERSISTENCE
    print("\n[4] Testing Career Preference Persistence...")
    stu_rec = StudentRecord.objects.filter(student=user).first()
    career_obj = CareerObjective.objects.filter(institution=stu_rec.institution).first()
    if career_obj:
        pref, _ = StudentCareerPreference.objects.update_or_create(
            institution=stu_rec.institution,
            student_record=stu_rec,
            defaults={"career_objective": career_obj, "priority": 1, "notes": "Persistent career test"},
        )
        hex_pref_id = pref.id.hex if hasattr(pref.id, "hex") else str(pref.id).replace("-", "")
        with connection.cursor() as cur:
            cur.execute(
                "SELECT notes FROM student_career_preferences WHERE id = %s",
                [hex_pref_id]
            )
            raw_notes = cur.fetchone()[0]
            assert raw_notes == "Persistent career test", f"Expected 'Persistent career test', got {raw_notes}"
        print("   -> Career preference updates persisted in database! PASS")

    # 5. NOTIFICATION READ STATUS PERSISTENCE
    print("\n[5] Testing Notification Status Persistence...")
    notif = Notification.objects.filter(recipient=user).first()
    if notif:
        notif.read_status = ReadStatus.READ
        notif.save(update_fields=["read_status"])
        hex_notif_id = notif.id.hex if hasattr(notif.id, "hex") else str(notif.id).replace("-", "")
        with connection.cursor() as cur:
            cur.execute("SELECT read_status FROM notifications_notification WHERE id = %s", [hex_notif_id])
            raw_status = cur.fetchone()[0]
            assert raw_status == ReadStatus.READ, f"Expected READ, got {raw_status}"
        print("   -> Notification read status persisted in database! PASS")

    print("\n==================================================")
    print("ALL APPLICATION UPDATES CONFIRMED PERSISTENT ON DISK!")
    print("==================================================")

if __name__ == "__main__":
    verify_all_persistence()
