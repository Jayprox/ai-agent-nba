import requests
from typing import Any, Dict

class ApiError(Exception):
    """Custom exception for API errors."""
    pass

def get_json(url: str, params: Dict[str, Any]) -> Any:
    """Performs a GET request and returns parsed JSON or raises ApiError."""
    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code != 200:
            raise ApiError(f"HTTP {response.status_code}: {response.text[:300]}")
        return response.json()
    except requests.RequestException as e:
        raise ApiError(str(e)) from e
