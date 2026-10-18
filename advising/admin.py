from django.contrib import admin

from advising.models import RiskAcknowledgment, StudentRiskProfile


@admin.register(StudentRiskProfile)
class StudentRiskProfileAdmin(admin.ModelAdmin):
    list_display = (
        "student_record",
        "institution",
        "overall_risk_level",
        "critical_risk_count",
        "warning_risk_count",
        "active_risk_count",
        "assessed_at",
    )
    list_filter = ("institution", "overall_risk_level", "assessed_at")
    search_fields = ("student_record__student__username", "student_record__student_id_number")
    readonly_fields = ("assessed_at",)


@admin.register(RiskAcknowledgment)
class RiskAcknowledgmentAdmin(admin.ModelAdmin):
    list_display = (
        "risk_profile",
        "indicator_code",
        "advisor",
        "status",
        "created_at",
    )
    list_filter = ("institution", "status", "indicator_code")
    search_fields = ("risk_profile__student_record__student__username", "advisor__username", "notes")
