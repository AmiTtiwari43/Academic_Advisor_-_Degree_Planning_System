from rest_framework.throttling import SimpleRateThrottle


class LoginRateThrottle(SimpleRateThrottle):
    """
    Rate throttle applied to login attempts per IP address.
    """

    scope = "login"

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class PasswordResetRateThrottle(SimpleRateThrottle):
    """
    Rate throttle applied to password reset requests per IP address.
    """

    scope = "password_reset"

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }
