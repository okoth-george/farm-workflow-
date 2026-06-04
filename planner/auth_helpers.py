# /app/planner/auth_helpers.py
import jwt
from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed
from .models import UserProfile  # 🔑 Imported your local user table

def verify_and_extract_express_token(token_string):
    """
    Decodes the incoming token, checks/saves the user record in Django's 
    local database, and returns the actual UserProfile object instance.
    """
    if not token_string:
        raise AuthenticationFailed("No token provided from authorization gateway.")
        
    try:
        # Decrypt and verify the signature using the shared key
        payload = jwt.decode(
            token_string, 
            settings.JWT_SECRET_KEY, 
            algorithms=["HS256"]
        )
        
        node_id = payload.get('id')
        node_username = payload.get('username')
        
        if not node_id or not node_username:
            raise AuthenticationFailed("Invalid token payload structure.")

        # ⚡ THE MULTI-USER DATABASE MATCH:
        # Look for the user by their Node/Express ID. If they aren't in Django's DB yet, 
        # Django creates a fresh row for them right here on the fly!
        user_profile, created = UserProfile.objects.get_or_create(
            external_id=node_id,
            defaults={
                'username': node_username,
            }
        )
        
        # Optional: If they updated their username on the Node app, sync it here too
        if not created and user_profile.username != node_username:
            user_profile.username = node_username
            user_profile.save()
            
        # 🚀 Return the actual database profile model instance
        return user_profile
        
    except jwt.ExpiredSignatureError:
        raise AuthenticationFailed("Authentication failed: The gateway token has expired.")
    except jwt.InvalidTokenError:
        raise AuthenticationFailed("Authentication failed: Cryptographic signature block is invalid.")