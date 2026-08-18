import time
from fastapi import Request, HTTPException
from collections import defaultdict

# A simple in-memory sliding window rate limiter
# Map of IP -> list of timestamps
_login_attempts = defaultdict(list)
_webhook_attempts = defaultdict(list)

import os
from app.core.settings import settings

def rate_limit_login(request: Request):
    if settings.env in ("test", "testing") or os.getenv("TESTING") == "True":
        return
    ip = request.client.host if request.client else "127.0.0.1"
    now = time.time()
    
    # Clean up old attempts (older than 1 minute)
    _login_attempts[ip] = [t for t in _login_attempts[ip] if now - t < 60]
    
    # Limit: 5 requests per minute
    if len(_login_attempts[ip]) >= 5:
        raise HTTPException(status_code=429, detail="Too many login attempts. Please try again later.")
        
    _login_attempts[ip].append(now)


def rate_limit_webhook(request: Request):
    ip = request.client.host if request.client else "127.0.0.1"
    now = time.time()
    
    # Clean up old attempts (older than 1 minute)
    _webhook_attempts[ip] = [t for t in _webhook_attempts[ip] if now - t < 60]
    
    # Limit: 60 requests per minute
    if len(_webhook_attempts[ip]) >= 60:
        raise HTTPException(status_code=429, detail="Too many webhook requests. Please try again later.")
        
    _webhook_attempts[ip].append(now)
