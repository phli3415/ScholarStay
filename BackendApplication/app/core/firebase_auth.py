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
FIREBASE_CREDENTIALS_PATH = "BackendApplication/firebase-service-account.json"

# Initialize Firebase Admin SDK
def initialize_firebase():
    """
    Initializes the Firebase Admin SDK.
    This function should be called once when the application starts.
    """
    try:
        # Check if the app is already initialized to prevent errors on hot-reload
        if not firebase_admin._apps:
            cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred)
            print("Firebase Admin SDK initialized successfully.")
        else:
            print("Firebase Admin SDK already initialized.")
    except Exception as e:
        print(f"Error initializing Firebase Admin SDK: {e}")
        raise e

# OAuth2 scheme for extracting the bearer token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

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
    FastAPI dependency to retrieve the user from the database based on a verified token.
    """
    user = await UserRepository.get_by_firebase_uid(decoded_token["uid"])
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found. Please register first.")
    return user

async def get_current_user_or_none(token: str = Depends(oauth2_scheme)) -> Optional[User]:
    """
    FastAPI dependency for optional authentication.
    """
    if not token:
        return None
    try:
        decoded_token = await verify_firebase_token(token)
        return await get_current_user(decoded_token)
    except HTTPException:
        return None

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
