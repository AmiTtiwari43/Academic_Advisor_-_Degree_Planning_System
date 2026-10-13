from django.contrib.auth import logout
from django.http import JsonResponse


class ActiveMembershipMiddleware:
    """
    Ensures that authenticated users are active and possess at least one
    active institutional membership (unless they are a superuser).
    If a user is deactivated or all their memberships are deactivated,
    their session is immediately invalidated.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            is_active = request.user.is_active
            has_membership = (
                request.user.is_superuser
                or request.user.institution_memberships.filter(is_active=True).exists()
            )
            if not is_active or not has_membership:
                logout(request)
                if request.path.startswith("/api/"):
                    return JsonResponse(
                        {"detail": "User account or institution membership is inactive."},
                        status=401,
                    )

        return self.get_response(request)
