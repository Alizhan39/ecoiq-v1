"""
customer_ai_chat/throttles.py — Rate limiting for anonymous customer chat.
"""
from rest_framework.throttling import SimpleRateThrottle


class CustomerChatIPThrottle(SimpleRateThrottle):
    """
    Per source IP throttle for public customer chat.
    Guards the endpoint against automated abuse or denial-of-service attempts.
    """
    scope = 'customer_chat_ip'

    def get_cache_key(self, request, view):
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request),
        }
