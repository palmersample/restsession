"""
Set defaults for session instances when no parameters (or some parameters) are
supplied. MappingProxyType prevents mutation of the default parameters inside
the code; use property setters to change once an instance has been created.
"""
from types import MappingProxyType
from .default_hooks import default_request_exception_hook


# 301: Moved Permanently
# 302: Found / moved temporarily
# 303: See other
# 307: Temporary redirect (HTTP/1.1)
# 308: Permanent redirect (no HTTP method change)
REDIRECT_STATUS_CODES = (301, 302, 303, 307, 308)

# 408: Request timeout
# 413: Payload too large
# 429: Too many requests
CLIENT_ERROR_CODES = (408, 413, 429)

# 503: Service Unavailable - should be temporary
SERVER_ERROR_CODES = (503,)

# Commonly used (?)
DEFAULT_HEADERS = {
    "User-Agent": "python-restsession/0.01",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Connection": "keep-alive"
}

DEFAULT_HEADER_HOOKS = None
DEFAULT_EXCEPTION_HOOKS = default_request_exception_hook
DEFAULT_RESPONSE_HOOKS = []

SESSION_DEFAULTS = MappingProxyType(
    {
        "headers": DEFAULT_HEADERS,
        "auth_headers": {},
        "auth": None,
        "timeout": 5,
        "retries": 3,
        "max_redirects": 16,
        "backoff_factor": 0.3,
        "retry_status_code_list": list(CLIENT_ERROR_CODES + SERVER_ERROR_CODES),
        "retry_method_list": [
            "HEAD",
            "GET",
            "PUT",
            "POST",
            "PATCH",
            "DELETE",
            "OPTIONS",
            "TRACE"
        ],
        "respect_retry_headers": True,
        "base_url": None,
        "verify": True,
        "max_reauth": 3,
        "redirect_header_hook": DEFAULT_HEADER_HOOKS,
        "request_exception_hook": DEFAULT_EXCEPTION_HOOKS,
        "response_hooks": DEFAULT_RESPONSE_HOOKS,
        "safe_arguments": True,
        "always_relative_url": False
    }
)
