# main.py

import os
import configparser
from datetime import datetime
import httpx
from typing import Any, Dict, Optional
import asyncio

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.security import (HTTPAuthorizationCredentials, HTTPBearer,
                              OAuth2PasswordRequestForm)

from passlib.context import CryptContext


from ServerTee import ServerTee
from JWTToken import JWTToken
from mydb import MyDB
from util import logger


# log name as today's date in YYYY-MM-DD format
today_date = datetime.now().strftime("%Y-%m-%d")
# Create log file path dynamically based on the date
log_file_path = f"log/{today_date}.log"
# Initialize ServerTee with the dynamically generated log file path
tee = ServerTee(log_file_path)
# Print the log file path for reference
logger(log_file_path)

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware
origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # List of allowed origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allows all headers
)



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


@app.post("/auth/token")  # Moved from router
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



# Catch-all route for unmatched requests
@app.api_route("/{anypath:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])  # Add all HTTP methods
async def proxy_to_backend(request: Request, anypath: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Proxies all requests to the backend server after JWT authentication.
    """
    backend_port = int(os.environ.get("BACKEND_PORT"))
    backend_url = f"http://backend:6000/{anypath}"  # Construct backend URL

    logger(f"Proxying request to: {backend_url}")

    try:
        # Extract request body
        body = await request.body()

        # Make the request to the backend server
        async with httpx.AsyncClient() as client:
            backend_response = await client.request(
                method=request.method,
                url=backend_url,
                headers=request.headers,
                content=body,
                params=request.query_params,
                timeout=30  # Add a timeout to prevent hanging requests
            )

        # Return the backend response to the client
        return StreamingResponse(
            backend_response.aiter_bytes(),
            status_code=backend_response.status_code,
            headers=backend_response.headers,
        )

    except httpx.TimeoutException as e:
        logger(f"Backend request timed out: {e}")
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Backend request timed out")
    except httpx.RequestError as e:
        logger(f"Error connecting to backend: {e}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Error connecting to backend")
    except Exception as e:
        logger(f"Unexpected error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")



# Run the app using Uvicorn
if __name__ == "__main__":
    import uvicorn

    auth_port = int(os.environ.get("AUTH_PORT", 8000))  # Default to 8000 if not set
    uvicorn.run(app, host="0.0.0.0", port=auth_port, reload=True)