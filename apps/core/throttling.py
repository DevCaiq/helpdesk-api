from rest_framework.throttling import ScopedRateThrottle


class EscritaThrottleMixin:
    throttle_classes = [ScopedRateThrottle]

    def get_throttles(self):
        self.throttle_scope = (
            "leitura" if self.request.method in ("GET", "HEAD", "OPTIONS") else "escrita"
        )
        return super().get_throttles()
