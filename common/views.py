from datetime import datetime, timezone
import mimetypes

from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.db.models import Q
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from academic_records.models import StudentRecord
from accounts.models import InstitutionMembership, Role, UserProfile
from curriculum.models import Course, Programme
from planning.models import Plan


class HealthResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    service = serializers.CharField()
    version = serializers.CharField()
    timestamp = serializers.CharField()


class SearchStudentItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    registration_number = serializers.CharField()
    username = serializers.CharField()
    name = serializers.CharField()
    programme_code = serializers.CharField()
    programme_name = serializers.CharField()
    cgpa = serializers.CharField(required=False, allow_null=True)


class SearchFacultyItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    registration_number = serializers.CharField()
    username = serializers.CharField()
    name = serializers.CharField()
    role = serializers.CharField()
    department = serializers.CharField(required=False, allow_null=True)


class SearchCourseItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    code = serializers.CharField()
    title = serializers.CharField()
    credits = serializers.DecimalField(max_digits=4, decimal_places=1)


class SearchProgrammeItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    code = serializers.CharField()
    name = serializers.CharField()
    degree_type = serializers.CharField()


class SearchPlanItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    status = serializers.CharField()
    student_registration_number = serializers.CharField()
    student_username = serializers.CharField()
    student_name = serializers.CharField()
    programme_code = serializers.CharField()


class GlobalSearchResultsSerializer(serializers.Serializer):
    query = serializers.CharField()
    students = SearchStudentItemSerializer(many=True)
    faculty = SearchFacultyItemSerializer(many=True)
    courses = SearchCourseItemSerializer(many=True)
    programmes = SearchProgrammeItemSerializer(many=True)
    plans = SearchPlanItemSerializer(many=True)


@extend_schema(
    summary="Service Health Check",
    description="Public health check endpoint for monitoring, load balancers, and container orchestration.",
    responses={200: HealthResponseSerializer},
    auth=[],
)
@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """
    Public health check endpoint returning service liveness and timestamp.
    """
    return Response(
        {
            "status": "ok",
            "service": "academic-advisor-system",
            "version": "1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


@extend_schema(
    summary="Universal Search",
    description="Universal search endpoint supporting lookup by unique registration number, student name, advisor/faculty name, course code, programme, and degree plans.",
    responses={200: GlobalSearchResultsSerializer},
)
class GlobalSearchView(APIView):
    """
    Universal search endpoint supporting lookup by unique registration number,
    student name, advisor/faculty name, course code, programme, and degree plans.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        user = request.user
        user_inst_ids = list(
            InstitutionMembership.objects.filter(user=user, is_active=True).values_list(
                "institution_id", flat=True
            )
        )

        results = {
            "query": query,
            "students": [],
            "faculty": [],
            "courses": [],
            "programmes": [],
            "plans": [],
        }

        if not query:
            # Return top 5 recent students and courses for quick suggestion
            if user_inst_ids:
                records = (
                    StudentRecord.objects.filter(institution_id__in=user_inst_ids)
                    .select_related("student", "student__profile", "programme")[:5]
                )
                for r in records:
                    p = getattr(r.student, "profile", None)
                    reg_no = p.get_or_generate_registration_number() if p else f"STU-2026-{r.student_id:04d}"
                    name = r.student.get_full_name() or (p.preferred_name if p else "") or r.student.username
                    results["students"].append({
                        "id": str(r.id),
                        "registration_number": reg_no,
                        "username": r.student.username,
                        "name": name,
                        "programme_code": r.programme.code,
                        "programme_name": r.programme.name,
                        "cgpa": str(r.cached_cgpa),
                    })
            return Response(results, status=status.HTTP_200_OK)

        # 1. Search Students
        student_filter = (
            Q(institution_id__in=user_inst_ids)
            & (
                Q(student__profile__registration_number__icontains=query)
                | Q(student__username__icontains=query)
                | Q(student__first_name__icontains=query)
                | Q(student__last_name__icontains=query)
                | Q(student__email__icontains=query)
                | Q(student__profile__preferred_name__icontains=query)
                | Q(programme__code__icontains=query)
                | Q(programme__name__icontains=query)
            )
        )
        student_records = (
            StudentRecord.objects.filter(student_filter)
            .select_related("student", "student__profile", "programme")
            .distinct()[:15]
        )
        for r in student_records:
            p = getattr(r.student, "profile", None)
            reg_no = p.get_or_generate_registration_number() if p else f"STU-2026-{r.student_id:04d}"
            name = r.student.get_full_name() or (p.preferred_name if p else "") or r.student.username
            results["students"].append({
                "id": str(r.id),
                "registration_number": reg_no,
                "username": r.student.username,
                "name": name,
                "email": r.student.email,
                "programme_code": r.programme.code,
                "programme_name": r.programme.name,
                "cgpa": str(r.cached_cgpa),
            })

        # 2. Search Faculty & Advisors
        faculty_filter = (
            Q(institution_id__in=user_inst_ids)
            & ~Q(role=Role.STUDENT)
            & (
                Q(user__profile__registration_number__icontains=query)
                | Q(user__username__icontains=query)
                | Q(user__first_name__icontains=query)
                | Q(user__last_name__icontains=query)
                | Q(user__email__icontains=query)
                | Q(user__profile__preferred_name__icontains=query)
            )
        )
        faculty_members = (
            InstitutionMembership.objects.filter(faculty_filter)
            .select_related("user", "user__profile")
            .distinct()[:10]
        )
        for f in faculty_members:
            p = getattr(f.user, "profile", None)
            reg_no = p.get_or_generate_registration_number() if p else f"FAC-2026-{f.user_id:04d}"
            name = f.user.get_full_name() or (p.preferred_name if p else "") or f.user.username
            results["faculty"].append({
                "id": str(f.user.id),
                "registration_number": reg_no,
                "username": f.user.username,
                "name": name,
                "role": "Mentor" if f.role in [Role.ADVISOR, Role.MENTOR, "FACULTY"] else "Moderator",
                "email": f.user.email,
            })

        # 3. Search Courses
        courses = Course.objects.filter(
            Q(institution_id__in=user_inst_ids)
            & (
                Q(code__icontains=query)
                | Q(title__icontains=query)
                | Q(description__icontains=query)
            )
        )[:15]
        for c in courses:
            results["courses"].append({
                "id": str(c.id),
                "code": c.code,
                "title": c.title,
                "credits": str(c.credits),
            })

        # 4. Search Programmes
        programmes = Programme.objects.filter(
            Q(institution_id__in=user_inst_ids)
            & (
                Q(code__icontains=query)
                | Q(name__icontains=query)
            )
        )[:10]
        for pr in programmes:
            results["programmes"].append({
                "id": str(pr.id),
                "code": pr.code,
                "name": pr.name,
                "degree_type": pr.degree_type,
            })

        # 5. Search Plans
        plans = Plan.objects.filter(
            Q(institution_id__in=user_inst_ids)
            & (
                Q(name__icontains=query)
                | Q(student_record__student__username__icontains=query)
                | Q(student_record__student__profile__registration_number__icontains=query)
            )
        ).select_related("student_record__student", "student_record__student__profile", "student_record__programme")[:10]
        for pl in plans:
            stu = pl.student_record.student
            p = getattr(stu, "profile", None)
            reg_no = p.get_or_generate_registration_number() if p else f"STU-2026-{stu.id:04d}"
            name = stu.get_full_name() or (p.preferred_name if p else "") or stu.username
            results["plans"].append({
                "id": str(pl.id),
                "name": pl.name,
                "status": pl.status,
                "student_id": str(pl.student_record.id),
                "student_name": name,
                "student_registration_number": reg_no,
                "programme_code": pl.student_record.programme.code,
            })

        return Response(results, status=status.HTTP_200_OK)


def spa_index_view(request):
    """
    Serve the built React SPA index.html for frontend routes.
    If the frontend bundle hasn't been compiled yet, return an informational status page.
    """
    index_file = settings.BASE_DIR / "frontend" / "dist" / "index.html"
    if index_file.exists():
        return FileResponse(open(index_file, "rb"), content_type="text/html")
    return HttpResponse(
        "<h1>Academic Advisor & Degree Planning System API</h1>"
        "<p>Backend service is active. Frontend bundle is not compiled yet.</p>"
        "<p><a href='/api/docs/'>Interactive API Documentation (Swagger UI)</a></p>"
        "<p><a href='/admin/'>Django Admin Portal</a></p>",
        content_type="text/html",
    )


def spa_assets_view(request, path):
    """
    Serve frontend built assets (JS, CSS, images, etc.) from frontend/dist/assets/.
    """
    asset_file = settings.BASE_DIR / "frontend" / "dist" / "assets" / path
    if asset_file.exists():
        content_type, _ = mimetypes.guess_type(str(asset_file))
        return FileResponse(
            open(asset_file, "rb"),
            content_type=content_type or "application/octet-stream",
        )
    return HttpResponse(status=404)

