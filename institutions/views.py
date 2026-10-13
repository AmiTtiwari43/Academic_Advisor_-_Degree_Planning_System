from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from institutions.models import Institution
from institutions.serializers import DepartmentSerializer, InstitutionSerializer
from institutions.services import get_institution_departments, list_active_institutions


class InstitutionListView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = InstitutionSerializer

    @extend_schema(
        responses={200: InstitutionSerializer(many=True)},
        description="List all active institutions.",
    )
    def get(self, request):
        institutions = list_active_institutions()
        serializer = InstitutionSerializer(institutions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DepartmentListView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DepartmentSerializer

    @extend_schema(
        responses={200: DepartmentSerializer(many=True), 404: dict},
        description="List all departments within the specified institution.",
    )
    def get(self, request, institution_id):
        try:
            institution = Institution.objects.get(id=institution_id)
        except (Institution.DoesNotExist, ValueError):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        departments = get_institution_departments(institution)
        serializer = DepartmentSerializer(departments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
