"""
Lago Billing Client for Voyant Usage-Based Billing.

This module provides an asynchronous client for integrating with the Lago API,
a usage-based billing platform. It enables the Voyant application to emit
billable usage events, manage customer records, and handle subscriptions,
facilitating the metering and monetization of platform services.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from voyant.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class BillableEvent:
    """
    Represents a single billable usage event to be emitted to Lago.

    Attributes:
        transaction_id (str): A unique identifier for the event transaction.
        external_customer_id (str): The customer's ID as known by Voyant.
        code (str): The metric code associated with the usage (e.g., "rows_ingested").
        timestamp (int): Unix timestamp of when the event occurred.
        properties (Dict[str, Any]): Additional properties describing the event.
    """

    transaction_id: str
    external_customer_id: str
    code: str
    timestamp: int
    properties: Dict[str, Any]


class LagoClient:
    """
    Asynchronous client for interacting with the Lago billing API.

    This client provides methods to emit usage events, manage customer details,
    and handle subscriptions within the Lago platform.
    """

    # METRICS: A mapping of internal Voyant metric names to Lago-specific metric codes.
    METRICS = {
        "sources_connected": "voyant_sources_connected",
        "rows_ingested": "voyant_rows_ingested",
        "queries_executed": "voyant_queries_executed",
        "storage_gb": "voyant_storage_gb",
        "api_calls": "voyant_api_calls",
    }

    def __init__(self):
        """
        Initializes the LagoClient with API URL and key from application settings.
        """
        self.api_url = settings.lago_api_url
        self.api_key = settings.lago_api_key
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """
        Lazily gets or creates an asynchronous HTTP client instance for Lago API calls.

        The client is configured with the base URL, authorization headers, and a timeout.

        Returns:
            httpx.AsyncClient: An asynchronous HTTP client instance.
        """
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,  # Set a default timeout for API requests.
            )
        return self._client

    async def close(self):
        """
        Closes the underlying HTTP client session.

        This should be called to gracefully release network resources.
        """
        if self._client:
            await self._client.aclose()
            self._client = None

    # =========================================================================
    # Usage Events
    # =========================================================================

    async def emit_usage(
        self,
        customer_id: str,
        metric: str,
        value: float = 1.0,
        properties: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Emits a usage event to the Lago billing system.

        Args:
            customer_id (str): The external ID of the customer for whom usage is being reported.
            metric (str): The internal Voyant metric name (e.g., "rows_ingested").
                          This is mapped to a Lago metric code.
            value (float, optional): The usage quantity. Defaults to 1.0.
            properties (Optional[Dict[str, Any]], optional): Additional custom properties for the event.

        Returns:
            bool: True if the usage event was successfully emitted, False otherwise.
        """
        try:
            client = await self._get_client()

            metric_code = self.METRICS.get(metric, metric) # Use mapped code or raw metric name.

            payload = {
                "event": {
                    "transaction_id": f"{customer_id}_{metric}_{int(datetime.utcnow().timestamp() * 1000)}",
                    "external_customer_id": customer_id,
                    "code": metric_code,
                    "timestamp": int(datetime.utcnow().timestamp()),
                    "properties": {
                        "value": value,
                        **(properties or {}), # Merge custom properties.
                    },
                }
            }

            response = await client.post("/api/v1/events", json=payload)
            response.raise_for_status() # Raises an exception for 4xx or 5xx responses.

            logger.debug(f"Emitted usage: {customer_id}/{metric}={value} (Lago code: {metric_code}).")
            return True

        except Exception as e:
            logger.error(f"Failed to emit usage event to Lago for customer {customer_id}, metric {metric}: {e}")
            return False

    # =========================================================================
    # Customers
    # =========================================================================

    async def create_customer(
        self,
        external_id: str,
        name: str,
        email: str,
        billing_configuration: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Creates a new customer record in Lago.

        Args:
            external_id (str): The unique ID for the customer as known by Voyant.
            name (str): The customer's name.
            email (str): The customer's email address.
            billing_configuration (Optional[Dict[str, Any]], optional): Custom billing configuration for the customer.

        Returns:
            Optional[Dict[str, Any]]: A dictionary representing the created customer
                                      from Lago's response, or None if creation fails.
        """
        try:
            client = await self._get_client()

            payload = {
                "customer": {
                    "external_id": external_id,
                    "name": name,
                    "email": email,
                    "billing_configuration": billing_configuration or {},
                }
            }

            response = await client.post("/api/v1/customers", json=payload)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Created customer in Lago: {external_id} ({email}).")
            return data.get("customer")

        except Exception as e:
            logger.error(f"Failed to create customer '{external_id}' in Lago: {e}")
            return None

    async def get_customer(self, external_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a customer's details from Lago by their external ID.

        Args:
            external_id (str): The unique ID of the customer as known by Voyant.

        Returns:
            Optional[Dict[str, Any]]: A dictionary representing the customer's details
                                      from Lago's response, or None if not found or an error occurs.
        """
        try:
            client = await self._get_client()
            response = await client.get(f"/api/v1/customers/{external_id}")
            response.raise_for_status()
            return response.json().get("customer")
        except Exception as e:
            logger.error(f"Failed to retrieve customer '{external_id}' from Lago: {e}")
            return None

    # =========================================================================
    # Subscriptions
    # =========================================================================

    async def create_subscription(
        self,
        customer_id: str,
        plan_code: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Creates a new subscription for a customer in Lago.

        Args:
            customer_id (str): The external ID of the customer to subscribe.
            plan_code (str): The code of the billing plan to subscribe to.

        Returns:
            Optional[Dict[str, Any]]: A dictionary representing the created subscription
                                      from Lago's response, or None if creation fails.
        """
        try:
            client = await self._get_client()

            payload = {
                "subscription": {
                    "external_customer_id": customer_id,
                    "plan_code": plan_code,
                    "external_id": f"{customer_id}_{plan_code}", # A unique external ID for the subscription.
                }
            }

            response = await client.post("/api/v1/subscriptions", json=payload)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Created subscription in Lago: {customer_id} subscribed to {plan_code}.")
            return data.get("subscription")

        except Exception as e:
            logger.error(f"Failed to create subscription for customer '{customer_id}' and plan '{plan_code}': {e}")
            return None

    # =========================================================================
    # Current Usage
    # =========================================================================

    async def get_current_usage(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves the current usage data for a specific customer from Lago.

        Args:
            customer_id (str): The external ID of the customer.

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing the customer's current
                                      usage data, or None if not found or an error occurs.
        """
        try:
            client = await self._get_client()
            response = await client.get(
                f"/api/v1/customers/{customer_id}/current_usage"
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to retrieve current usage for customer '{customer_id}' from Lago: {e}")
            return None


# Singleton client instance for application-wide use.
_client: Optional[LagoClient] = None


def get_lago_client() -> LagoClient:
    """
    Retrieves the singleton instance of the LagoClient.

    This factory function ensures that only one LagoClient is instantiated
    per application process, promoting efficient use of network resources.
    """
    global _client
    if _client is None:
        _client = LagoClient()
    return _client


async def emit_usage(
    tenant_id: str,
    metric: str,
    value: float = 1.0,
    **properties,
) -> bool:
    """
    Emits a usage event for a specific tenant to the Lago billing system.

    This is a convenience function that utilizes the singleton `LagoClient`.
    Usage emission can be conditionally enabled/disabled via application settings.

    Args:
        tenant_id (str): The identifier of the tenant reporting usage.
        metric (str): The internal metric code (e.g., "rows_ingested").
        value (float, optional): The quantity of usage. Defaults to 1.0.
        **properties: Additional custom properties to attach to the usage event.

    Returns:
        bool: True if the usage event was successfully emitted (or billing is disabled), False otherwise.
    """
    # Check if billing is enabled in the application settings.
    if not settings.enable_billing:
        logger.debug("Billing is disabled. Skipping Lago usage emission.")
        return True # Return True if billing is disabled, as the 'emission' effectively succeeded by doing nothing.
    return await get_lago_client().emit_usage(tenant_id, metric, value, properties)
