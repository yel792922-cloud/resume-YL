"""Authentication layer: password hashing, JWT tokens, current-user dependency.

Kept deliberately small and stateless (JWT bearer tokens) so it works cleanly
across the split Vercel (frontend) / Render (backend) deployment.
"""

from app.auth.deps import get_current_user
from app.auth.security import create_access_token, hash_password, verify_password

__all__ = ["get_current_user", "create_access_token", "hash_password", "verify_password"]
