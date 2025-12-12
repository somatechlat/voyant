"""
Lago Billing Client for Voyant

Usage-based billing integration via Lago.
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
    """Billable usage event."""
    transaction_id: str
    external_customer_id: str
    code: str  # metric code
    timestamp: int  # unix timestamp
    properties: Dict[str, Any]


class LagoClient:
    """Lago billing API client."""
    
    METRICS = {
        "sources_connected": "voyant_sources_connected",
        "rows_ingested": "voyant_rows_ingested",
        "queries_executed": "voyant_queries_executed",
        "storage_gb": "voyant_storage_gb",
        "api_calls": "voyant_api_calls",
    }
    
    def __init__(self):
        self.api_url = settings.lago_api_url
        self.api_key = settings.lago_api_key
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client
    
    async def close(self):
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
        """Emit usage event to Lago."""
        try:
            client = await self._get_client()
            
            metric_code = self.METRICS.get(metric, metric)
            
            payload = {
                "event": {
                    "transaction_id": f"{customer_id}_{metric}_{int(datetime.utcnow().timestamp() * 1000)}",
                    "external_customer_id": customer_id,
                    "code": metric_code,
                    "timestamp": int(datetime.utcnow().timestamp()),
                    "properties": {
                        "value": value,
                        **(properties or {}),
                    },
                }
            }
            
            response = await client.post("/api/v1/events", json=payload)
            response.raise_for_status()
            
            logger.debug(f"Emitted usage: {customer_id}/{metric}={value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to emit usage: {e}")
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
        """Create customer in Lago."""
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
            logger.info(f"Created customer: {external_id}")
            return data.get("customer")
            
        except Exception as e:
            logger.error(f"Failed to create customer: {e}")
            return None
    
    async def get_customer(self, external_id: str) -> Optional[Dict[str, Any]]:
        """Get customer by external ID."""
        try:
            client = await self._get_client()
            response = await client.get(f"/api/v1/customers/{external_id}")
            response.raise_for_status()
            return response.json().get("customer")
        except Exception as e:
            logger.error(f"Failed to get customer: {e}")
            return None
    
    # =========================================================================
    # Subscriptions
    # =========================================================================
    
    async def create_subscription(
        self,
        customer_id: str,
        plan_code: str,
    ) -> Optional[Dict[str, Any]]:
        """Create subscription for customer."""
        try:
            client = await self._get_client()
            
            payload = {
                "subscription": {
                    "external_customer_id": customer_id,
                    "plan_code": plan_code,
                    "external_id": f"{customer_id}_{plan_code}",
                }
            }
            
            response = await client.post("/api/v1/subscriptions", json=payload)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Created subscription: {customer_id} -> {plan_code}")
            return data.get("subscription")
            
        except Exception as e:
            logger.error(f"Failed to create subscription: {e}")
            return None
    
    # =========================================================================
    # Current Usage
    # =========================================================================
    
    async def get_current_usage(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Get current usage for customer."""
        try:
            client = await self._get_client()
            response = await client.get(
                f"/api/v1/customers/{customer_id}/current_usage"
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get usage: {e}")
            return None


# Singleton client
_client: Optional[LagoClient] = None

def get_lago_client() -> LagoClient:
    global _client
    if _client is None:
        _client = LagoClient()
    return _client


# Convenience function
async def emit_usage(
    tenant_id: str,
    metric: str,
    value: float = 1.0,
    **properties,
) -> bool:
    """Emit usage event for tenant."""
    if not settings.enable_billing:
        return True
    return await get_lago_client().emit_usage(tenant_id, metric, value, properties)
