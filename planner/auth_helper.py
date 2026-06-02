# /app/planner/auth_helpers.py
import jwt
from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed

def verify_and_extract_express_token(token_string):
    """
    Decodes the incoming token string using the shared secret key.
    Returns the user data payload if valid, or raises an exception.
    """
    if not token_string:
        raise AuthenticationFailed("No token provided from authorization gateway.")
        
    try:
        # Decrypt and verify the signature using the shared key
        payload = jwt.decode(
            token_string, 
            settings.JWT_SECRET_KEY, # Checked against settings
            algorithms=["HS256"]
        )
        
        # Return a structured dictionary of the user's details
        return {
            'user_id': payload.get('id'),
            'username': payload.get('username'),
            'email': payload.get('email'),
        }
        
    except jwt.ExpiredSignatureError:
        raise AuthenticationFailed("Authentication failed: The gateway token has expired.")
    except jwt.InvalidTokenError:
        raise AuthenticationFailed("Authentication failed: Cryptographic signature block is invalid.")