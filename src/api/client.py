import time
import requests
from src.config import BASE_URL, REQUEST_DELAY, TIMEOUT

HEADERS = {
    "Accept": "application/json",
    "X-Requested-With": "XMLHttpRequest",
}

def get(endpoint, params=None):
    url = f"{BASE_URL}{endpoint}"
    r = requests.get(
        url,
        params=params,
        headers=HEADERS,
        timeout=TIMEOUT,
    )

    content_type = r.headers.get("Content-Type", "")

    if "application/json" not in content_type:
        print("NON-JSON RESPONSE")
        print("URL:", r.url)
        print("Status:", r.status_code)
        print("Content-Type:", content_type)
        print("First 500 chars:")
        print(r.text[:500])
        raise RuntimeError("Expected JSON, got non-JSON response")

    time.sleep(REQUEST_DELAY)
    return r.json()
