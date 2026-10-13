from django.db import models


class TenantQuerySet(models.QuerySet):
    """
    QuerySet providing explicit multi-tenant scoping.
    """

    def for_institution(self, institution):
        if hasattr(institution, "id"):
            institution = institution.id
        return self.filter(institution_id=institution)


class TenantManager(models.Manager):
    """
    Manager providing tenant-scoped queries.
    """

    def get_queryset(self) -> TenantQuerySet:
        return TenantQuerySet(self.model, using=self._db)

    def for_institution(self, institution) -> TenantQuerySet:
        return self.get_queryset().for_institution(institution)


class TenantModel(models.Model):
    """
    Abstract base model ensuring every institution-owned record has a non-null
    foreign key to Institution and utilizes tenant-scoped querysets.
    """

    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.CASCADE,
        related_name="+",
        db_index=True,
    )

    objects = TenantManager()

    class Meta:
        abstract = True


def assert_tenant_scoped(model_or_instance):
    """
    Test helper verifying that a model or model instance is strictly tenant-scoped.
    """
    model_cls = (
        model_or_instance if isinstance(model_or_instance, type) else model_or_instance.__class__
    )
    if not issubclass(model_cls, TenantModel):
        raise AssertionError(f"Model {model_cls.__name__} does not inherit from TenantModel.")
    if not hasattr(model_cls.objects, "for_institution"):
        raise AssertionError(
            f"Model {model_cls.__name__}.objects does not support for_institution()."
        )
    return True
