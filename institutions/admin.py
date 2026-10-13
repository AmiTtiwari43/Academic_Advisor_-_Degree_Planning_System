from django.contrib import admin

from institutions.models import Department, Institution


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "domain", "is_active", "created_at")
    search_fields = ("name", "code", "domain")
    list_filter = ("is_active",)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "institution", "created_at")
    search_fields = ("name", "code", "institution__name")
    list_filter = ("institution",)
