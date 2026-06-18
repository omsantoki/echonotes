"""Auth package (feature 002, Constitution Art. X).

Email+password signup with OTP verification, password login, Google sign-in, and
forgot/reset — plus the `get_current_user` dependency that gates the data routes.
"""

from app.auth.router import router

__all__ = ["router"]
