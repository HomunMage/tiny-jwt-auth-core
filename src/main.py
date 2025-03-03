# main.py

import os
from datetime import datetime
import httpx
from typing import Dict
import asyncio

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from ServerTee import ServerTee
from util import logger
from jwt_auth_router import jwt_auth_router # Import the router

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

# Include the JWT authentication router
app.include_router(jwt_auth_router)

# Dictionary to store ProcessHandler instances per user
handlers = {}


@app.get("/hello/")
async def test_endpoint():
    logger("hello")
    return {"message": "Hello World"}



# Catch-all route for unmatched GET requests
@app.api_route("/{anypath:path}", methods=["GET"])
async def catch_all(request: Request, anypath: str):
    logger(f"Unmatched GET request: {anypath}")
    return JSONResponse(content={"message": f"Route {anypath} not found"}, status_code=404)


# Run the app using Uvicorn
if __name__ == "__main__":
    import uvicorn

    backend_port = int(os.environ.get("BACKEND_PORT", 8000))  # Default to 8000 if not set
    uvicorn.run(app, host="0.0.0.0", port=backend_port, reload=True)