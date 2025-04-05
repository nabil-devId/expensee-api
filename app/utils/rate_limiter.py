from datetime import datetime, timedelta
import logging
from typing import Dict, Tuple, Optional, List, Any
import time

logger = logging.getLogger(__name__)

# Simple in-memory storage for rate limiting
# In a production environment, you'd want to use Redis or another distributed cache
# Format: {key: [(timestamp1, count1), (timestamp2, count2), ...]}
RATE_LIMIT_STORE: Dict[str, List[Tuple[float, int]]] = {}


class RateLimiter:
    """
    Simple rate limiter that uses a sliding window algorithm
    """
    
    def __init__(self, window_size: int = 60, max_requests: int = 10):
        """
        Initialize a rate limiter
        
        Args:
            window_size: Time window in seconds
            max_requests: Maximum number of requests allowed within the window
        """
        self.window_size = window_size
        self.max_requests = max_requests
    
    def is_rate_limited(self, key: str) -> Tuple[bool, int]:
        """
        Check if a request should be rate limited
        
        Args:
            key: Identifier for the rate limit (e.g., IP address, user ID)
            
        Returns:
            Tuple of (is_limited, retry_after)
            - is_limited: True if the request should be rate limited
            - retry_after: Seconds to wait before retrying (0 if not limited)
        """
        now = time.time()
        window_start = now - self.window_size
        
        # Initialize store for key if it doesn't exist
        if key not in RATE_LIMIT_STORE:
            RATE_LIMIT_STORE[key] = []
        
        # Remove outdated entries
        RATE_LIMIT_STORE[key] = [
            (timestamp, count) 
            for timestamp, count in RATE_LIMIT_STORE[key] 
            if timestamp > window_start
        ]
        
        # Count total requests in current window
        total_requests = sum(count for _, count in RATE_LIMIT_STORE[key])
        
        # If under the limit, add request and allow
        if total_requests < self.max_requests:
            # If there are entries, increment the most recent
            if RATE_LIMIT_STORE[key]:
                timestamp, count = RATE_LIMIT_STORE[key][-1]
                RATE_LIMIT_STORE[key][-1] = (timestamp, count + 1)
            else:
                # Otherwise add a new entry
                RATE_LIMIT_STORE[key].append((now, 1))
            return False, 0
        
        # Calculate retry-after time
        if RATE_LIMIT_STORE[key]:
            oldest_timestamp = RATE_LIMIT_STORE[key][0][0]
            retry_after = int(oldest_timestamp + self.window_size - now) + 1
            retry_after = max(1, retry_after)  # Ensure it's at least 1 second
        else:
            retry_after = 1
        
        return True, retry_after


# Create rate limiters with different policies
auth_rate_limiter = RateLimiter(window_size=60, max_requests=5)  # 5 reqs/min for auth endpoints
api_rate_limiter = RateLimiter(window_size=60, max_requests=60)  # 60 reqs/min for regular API
reset_password_rate_limiter = RateLimiter(window_size=3600, max_requests=3)  # 3 reqs/hour for password reset
