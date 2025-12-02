"""
Firebase Authentication
Handles all Firebase related authentication and user management
"""

import firebase_admin
from firebase_admin import credentials, auth
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from starlette import status
from typing import Optional, Dict

from ..repository.user_repository import UserRepository
from ..model.user import User

# Path to your Firebase service account key
FIREBASE_CREDENTIALS_PATH = "firebaseAuth.json"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

_firebase_app_initialized = False

def initialize_firebase():
    """
    Initializes the Firebase Admin SDK.
    """
    global _firebase_app_initialized
    if not _firebase_app_initialized:
        try:
            cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred)
            _firebase_app_initialized = True
            print("Firebase Admin SDK initialized successfully.")
        except Exception as e:
            print(f"Error initializing Firebase Admin SDK: {e}")
            # Depending on the use case, you might want to raise an exception
            # raise e

async def verify_firebase_token(token: str = Depends(oauth2_scheme)) -> Dict:
    """
    FastAPI dependency to verify a Firebase ID token and return the decoded claims.
    This does NOT check if the user exists in the local database.
    """
    try:
        decoded_token = auth.verify_id_token(token)
        if not decoded_token or "uid" not in decoded_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims")
        return decoded_token
    except (auth.InvalidIdTokenError, auth.ExpiredIdTokenError, auth.RevokedIdTokenError) as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {e}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Token verification error: {e}")

async def get_current_user(decoded_token: Dict = Depends(verify_firebase_token)) -> User:
    """
    FastAPI dependency that uses `verify_firebase_token` to get a decoded token,
    and then retrieves the corresponding user from the local database.
    """
    firebase_uid = decoded_token.get("uid")
    user = await UserRepository.get_by_firebase_uid(firebase_uid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with UID {firebase_uid} not found in local database."
        )
    return user

async def create_or_update_user(decoded_token: dict) -> User:
    """
    Creates or updates a user in the database from a decoded Firebase token.
    """
    firebase_uid = decoded_token['uid']
    user = await UserRepository.get_by_firebase_uid(firebase_uid)
    if user:
        return user
    
    # Create new user
    gmail = decoded_token.get('email')
    username_from_email = gmail.split('@')[0] if gmail else f"user_{firebase_uid[:8]}"
    username = decoded_token.get('name', username_from_email)
    
    new_user = await UserRepository.create(
        firebase_uid=firebase_uid,
        gmail=gmail,
        username=username
    )
    return new_user
