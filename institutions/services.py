from django.db.models import QuerySet

from institutions.models import Department, Institution


def list_active_institutions() -> QuerySet[Institution]:
    """
    Returns all active institutions.
    """
    return Institution.objects.filter(is_active=True).order_by("name")


def get_institution_departments(institution: Institution) -> QuerySet[Department]:
    """
    Returns all departments for the specified institution using tenant scoping.
    """
    return Department.objects.for_institution(institution).order_by("name")
