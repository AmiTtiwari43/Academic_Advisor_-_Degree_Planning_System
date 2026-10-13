from rest_framework.routers import DefaultRouter

from academic_records.views import (
    AcademicTermViewSet,
    ExemptionViewSet,
    StudentRecordViewSet,
    TranscriptEntryViewSet,
    TransferCreditViewSet,
)

router = DefaultRouter()
router.register(r"terms", AcademicTermViewSet, basename="academic-term")
router.register(r"student-records", StudentRecordViewSet, basename="student-record")
router.register(r"transcripts", TranscriptEntryViewSet, basename="transcript-entry")
router.register(r"transfer-credits", TransferCreditViewSet, basename="transfer-credit")
router.register(r"exemptions", ExemptionViewSet, basename="course-exemption")

urlpatterns = router.urls
