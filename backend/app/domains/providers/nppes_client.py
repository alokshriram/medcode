"""
NPPES NPI Registry API Client

Provides integration with the CMS National Plan and Provider Enumeration System (NPPES)
API for looking up provider information by NPI number.

API Documentation: https://npiregistry.cms.hhs.gov/api-page
No authentication required - free public API.
"""
import logging
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

NPPES_API_BASE_URL = "https://npiregistry.cms.hhs.gov/api/"
NPPES_API_VERSION = "2.1"
DEFAULT_TIMEOUT = 10.0  # seconds


@dataclass
class NPPESProviderData:
    """Structured data extracted from NPPES API response."""
    npi: str
    enumeration_type: str  # "NPI-1" (Individual) or "NPI-2" (Organization)
    first_name: str | None
    last_name: str | None
    middle_name: str | None
    credential: str | None
    gender: str | None
    taxonomy_code: str | None
    specialty: str | None
    status: str  # "A" = Active
    raw_response: dict  # Full API response for caching


class NPPESAPIError(Exception):
    """Raised when NPPES API returns an error or is unreachable."""
    pass


class NPPESProviderNotFound(Exception):
    """Raised when NPI is not found in NPPES registry."""
    pass


class NPPESClient:
    """
    Client for the NPPES NPI Registry API.

    Usage:
        client = NPPESClient()
        provider = client.lookup_npi("1234567890")
        print(provider.full_name, provider.specialty)
    """

    def __init__(self, timeout: float = DEFAULT_TIMEOUT):
        self.timeout = timeout
        self._client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        """Get or create HTTP client (lazy initialization)."""
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout)
        return self._client

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "NPPESClient":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def lookup_npi(self, npi: str) -> NPPESProviderData:
        """
        Look up a provider by NPI number.

        Args:
            npi: 10-digit National Provider Identifier

        Returns:
            NPPESProviderData with provider information

        Raises:
            NPPESProviderNotFound: If NPI is not found
            NPPESAPIError: If API request fails
        """
        if not self._validate_npi(npi):
            raise ValueError(f"Invalid NPI format: {npi}. Must be 10 digits.")

        try:
            client = self._get_client()
            response = client.get(
                NPPES_API_BASE_URL,
                params={
                    "version": NPPES_API_VERSION,
                    "number": npi,
                },
            )
            response.raise_for_status()
            data = response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"NPPES API HTTP error for NPI {npi}: {e}")
            raise NPPESAPIError(f"NPPES API returned status {e.response.status_code}") from e
        except httpx.RequestError as e:
            logger.error(f"NPPES API request error for NPI {npi}: {e}")
            raise NPPESAPIError(f"Failed to connect to NPPES API: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error looking up NPI {npi}: {e}")
            raise NPPESAPIError(f"Unexpected error: {e}") from e

        return self._parse_response(npi, data)

    def _validate_npi(self, npi: str) -> bool:
        """Validate NPI format (10 digits)."""
        return npi.isdigit() and len(npi) == 10

    def _parse_response(self, npi: str, data: dict) -> NPPESProviderData:
        """Parse NPPES API response into structured data."""
        result_count = data.get("result_count", 0)

        if result_count == 0:
            raise NPPESProviderNotFound(f"NPI {npi} not found in NPPES registry")

        results = data.get("results", [])
        if not results:
            raise NPPESProviderNotFound(f"NPI {npi} not found in NPPES registry")

        # Take first result (should only be one for NPI lookup)
        result = results[0]

        # Extract basic info
        basic = result.get("basic", {})

        # Extract primary taxonomy
        taxonomy_code = None
        specialty = None
        taxonomies = result.get("taxonomies", [])
        for tax in taxonomies:
            if tax.get("primary", False):
                taxonomy_code = tax.get("code")
                specialty = tax.get("desc")
                break
        # Fallback to first taxonomy if no primary
        if not taxonomy_code and taxonomies:
            taxonomy_code = taxonomies[0].get("code")
            specialty = taxonomies[0].get("desc")

        return NPPESProviderData(
            npi=result.get("number", npi),
            enumeration_type=result.get("enumeration_type", ""),
            first_name=basic.get("first_name"),
            last_name=basic.get("last_name"),
            middle_name=basic.get("middle_name"),
            credential=basic.get("credential"),
            gender=basic.get("sex"),
            taxonomy_code=taxonomy_code,
            specialty=specialty,
            status=basic.get("status", ""),
            raw_response=result,
        )

    def search_providers(
        self,
        first_name: str | None = None,
        last_name: str | None = None,
        state: str | None = None,
        taxonomy_description: str | None = None,
        enumeration_type: str = "NPI-1",  # Default to individuals
        limit: int = 10,
    ) -> list[NPPESProviderData]:
        """
        Search for providers by name, location, or specialty.

        Args:
            first_name: Provider's first name
            last_name: Provider's last name
            state: Two-letter state code
            taxonomy_description: Specialty description (e.g., "Internal Medicine")
            enumeration_type: "NPI-1" for individuals, "NPI-2" for organizations
            limit: Maximum results to return (max 200)

        Returns:
            List of matching providers
        """
        params: dict[str, Any] = {
            "version": NPPES_API_VERSION,
            "enumeration_type": enumeration_type,
            "limit": min(limit, 200),
        }

        if first_name:
            params["first_name"] = first_name
        if last_name:
            params["last_name"] = last_name
        if state:
            params["state"] = state
        if taxonomy_description:
            params["taxonomy_description"] = taxonomy_description

        try:
            client = self._get_client()
            response = client.get(NPPES_API_BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"NPPES API search error: {e}")
            raise NPPESAPIError(f"NPPES API returned status {e.response.status_code}") from e
        except httpx.RequestError as e:
            logger.error(f"NPPES API search request error: {e}")
            raise NPPESAPIError(f"Failed to connect to NPPES API: {e}") from e

        results = []
        for result in data.get("results", []):
            try:
                results.append(self._parse_response(result.get("number", ""), {"results": [result], "result_count": 1}))
            except NPPESProviderNotFound:
                continue

        return results


# Singleton instance for reuse
_default_client: NPPESClient | None = None


def get_nppes_client() -> NPPESClient:
    """Get the default NPPES client instance."""
    global _default_client
    if _default_client is None:
        _default_client = NPPESClient()
    return _default_client
