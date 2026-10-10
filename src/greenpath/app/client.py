"""Small HTTP adapter. UI code never instantiates domain services."""

import os
from typing import Any
from urllib.parse import quote, urlparse

import httpx


class APIError(RuntimeError):
    """An API failure that can be safely shown to the demo user."""


class APIClient:
    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or os.getenv("GREENPATH_API_URL", "http://127.0.0.1:8000")).rstrip("/")
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise APIError("GREENPATH_API_URL must be an HTTP or HTTPS URL without credentials.")

    def get(self, path: str, params: dict[str, str] | None = None) -> Any:
        return self._request("get", path, params=params)

    def post(self, path: str, payload: dict[str, Any]) -> Any:
        """Write through HTTP without caching responses or retrying mutations."""
        return self._request("post", path, json=payload)

    def _request(self, method: str, path: str, **kwargs) -> Any:
        try:
            response = getattr(httpx, method)(self.base_url + path, **kwargs,
                                              timeout=httpx.Timeout(45.0, connect=2.0))
            response.raise_for_status()
            result = response.json()
        except httpx.TimeoutException as error:
            raise APIError("The API timed out. Check that the API is running, then refresh data.") from error
        except httpx.RequestError as error:
            raise APIError("Cannot reach the API. Start both services with make app, then refresh data.") from error
        except httpx.HTTPStatusError as error:
            code = error.response.status_code
            message = "Customer or product not found." if code == 404 else "The API could not complete this request."
            if code in {409, 422}:
                try:
                    detail = error.response.json().get("detail")
                    if isinstance(detail, str):
                        message = detail[:500]
                except (ValueError, AttributeError):
                    pass
            raise APIError(f"{message} HTTP {code}.") from error
        except ValueError as error:
            raise APIError("The API returned an invalid JSON response.") from error
        if not isinstance(result, (dict, list)):
            raise APIError("The API response does not match the expected JSON shape.")
        return result

    @staticmethod
    def customer_path(customer_id: str, suffix: str = "") -> str:
        return f"/customers/{quote(customer_id, safe='')}{suffix}"
