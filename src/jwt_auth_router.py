# jwt_auth_router.py

import configparser
import os
from datetime import timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.security import (HTTPAuthorizationCredentials, HTTPBearer,
                              OAuth2PasswordRequestForm)
from passlib.context import CryptContext

from JWTToken import JWTToken
from mydb import MyDB
from util import logger

# JWT Authentication Router
jwt_auth_router = APIRouter(prefix="/auth", tags=["authentication"])

# Initialize the database
my_db = MyDB("workspace/db.json")  # Initialize MyDB

# Load configuration from secret.ini
config = configparser.ConfigParser()
config.read('workspace/secret.ini')

# Get the secret key from secret.ini
SECRET_KEY = config.get('security', 'secret_key')

# Initialize JWTToken class
jwt_token_handler = JWTToken(secret_key=SECRET_KEY)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security scheme
http_bearer = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

async def get_user(username: str):
    """Retrieve user data based on username."""
    return my_db.get_user(username)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(http_bearer)):
    """Dependency to get the current user from the JWT token."""
    token = credentials.credentials
    logger("get_current_user: ", token)
    username = jwt_token_handler.verify_token(token)
    logger("get_current_user: ", username)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = await get_user(username)
    logger("get_current_user: ", user)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


@jwt_auth_router.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Endpoint to obtain a JWT access token."""
    logger(f"SECRET_KEY: {SECRET_KEY}")  # Add this line
    user = await get_user(form_data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not verify_password(form_data.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = jwt_token_handler.create_access_token(username=form_data.username)
    logger(f"access token created: ", access_token)
    return {"access_token": access_token, "token_type": "bearer"}


# Example protected endpoint (requires authentication)
@jwt_auth_router.get("/files")
async def list_files(current_user: dict = Depends(get_current_user)):
    """Endpoint to list files in the user's directory."""
    username = current_user["username"]
    user_dir = os.path.join("workspace", username)
    logger("get files: ", username)
    logger("get files: ", user_dir)
    if not os.path.exists(user_dir):
        return "Directory not found for this user."

    try:
        filenames = os.listdir(user_dir)
        return ", ".join(filenames)  # Return as a comma-separated string
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))