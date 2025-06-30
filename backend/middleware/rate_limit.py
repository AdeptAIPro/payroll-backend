from fastapi import HTTPException, Request
import time
from collections import defaultdict
from typing import Dict, List
from backend.utils.logger import api_logger

class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, List[float]] = defaultdict(list)
    
    async def check_rate_limit(self, request: Request):
        """Check if request is within rate limit"""
        client_ip = request.client.host
        now = time.time()
        
        # Clean old requests (older than 1 minute)
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if now - req_time < 60
        ]
        
        # Check if limit exceeded
        if len(self.requests[client_ip]) >= self.requests_per_minute:
            api_logger.warning(
                "Rate limit exceeded",
                client_ip=client_ip,
                requests_count=len(self.requests[client_ip])
            )
            raise HTTPException(
                status_code=429, 
                detail="Rate limit exceeded. Please try again later."
            )
        
        # Add current request
        self.requests[client_ip].append(now)
        
        # Log if approaching limit
        if len(self.requests[client_ip]) >= self.requests_per_minute * 0.8:
            api_logger.info(
                "Rate limit warning",
                client_ip=client_ip,
                requests_count=len(self.requests[client_ip])
            )

# Global rate limiter instance
rate_limiter = RateLimiter(requests_per_minute=60) 