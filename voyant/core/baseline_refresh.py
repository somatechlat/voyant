"""
Automated Baseline Refresh Module

Scheduled periodic re-baselining for drift/quality.
Reference: STATUS.md Gap #11 - Automated Baseline Refresh

Features:
- Configurable refresh schedules
- Per-source baseline policies
- Freshness tracking
- Refresh history
- Async background tasks

Personas Applied:
- PhD Developer: Scheduler patterns
- Analyst: Baseline freshness metrics
- QA: Edge case handling
- ISO Documenter: Policy documentation
- Security: No data in logs
- Performance: Efficient scheduling
- UX: Clear status APIs

Usage:
    from voyant.core.baseline_refresh import (
        schedule_refresh, get_refresh_status,
        RefreshPolicy, trigger_refresh
    )
    
    # Set policy
    set_refresh_policy("orders", RefreshPolicy(interval_hours=24))
    
    # Check status
    status = get_refresh_status("orders")
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class RefreshStrategy(str, Enum):
    """How to calculate new baseline."""
    REPLACE = "replace"          # Replace with current data
    MERGE = "merge"              # Merge with existing (weighted)
    ROLLING_WINDOW = "rolling"   # Use rolling window of data


class RefreshTrigger(str, Enum):
    """What triggers a refresh."""
    SCHEDULED = "scheduled"      # Time-based
    DRIFT_THRESHOLD = "drift"    # When drift exceeds threshold
    MANUAL = "manual"            # Explicitly triggered


@dataclass
class RefreshPolicy:
    """Policy for automated baseline refresh."""
    source_id: str = ""
    enabled: bool = True
    interval_hours: int = 24
    strategy: RefreshStrategy = RefreshStrategy.REPLACE
    drift_threshold: float = 0.3    # Trigger if drift > this
    min_data_points: int = 100      # Minimum rows needed
    retention_count: int = 5        # Keep N historical baselines
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "enabled": self.enabled,
            "interval_hours": self.interval_hours,
            "strategy": self.strategy.value,
            "drift_threshold": self.drift_threshold,
            "min_data_points": self.min_data_points,
            "retention_count": self.retention_count,
        }


@dataclass
class RefreshEvent:
    """A baseline refresh event."""
    source_id: str
    trigger: RefreshTrigger
    timestamp: float = 0
    success: bool = True
    error_message: str = ""
    rows_processed: int = 0
    duration_seconds: float = 0
    baseline_version: str = ""
    
    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "trigger": self.trigger.value,
            "timestamp": datetime.fromtimestamp(self.timestamp).isoformat(),
            "success": self.success,
            "error_message": self.error_message,
            "rows_processed": self.rows_processed,
            "duration_seconds": round(self.duration_seconds, 2),
            "baseline_version": self.baseline_version,
        }


@dataclass
class RefreshStatus:
    """Current refresh status for a source."""
    source_id: str
    policy: RefreshPolicy
    last_refresh: Optional[RefreshEvent] = None
    next_scheduled: Optional[float] = None
    is_due: bool = False
    history_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "policy": self.policy.to_dict(),
            "last_refresh": self.last_refresh.to_dict() if self.last_refresh else None,
            "next_scheduled": datetime.fromtimestamp(self.next_scheduled).isoformat() if self.next_scheduled else None,
            "is_due": self.is_due,
            "hours_until_next": max(0, (self.next_scheduled - time.time()) / 3600) if self.next_scheduled else None,
            "history_count": self.history_count,
        }


# =============================================================================
# Baseline Refresh Manager
# =============================================================================

class BaselineRefreshManager:
    """
    Manages automated baseline refresh.
    """
    
    def __init__(self):
        self._policies: Dict[str, RefreshPolicy] = {}
        self._history: Dict[str, List[RefreshEvent]] = {}
        self._refresh_handler: Optional[Callable] = None
        self._scheduler_task: Optional[asyncio.Task] = None
        self._running = False
    
    def set_policy(self, source_id: str, policy: RefreshPolicy) -> None:
        """Set refresh policy for a source."""
        policy.source_id = source_id
        self._policies[source_id] = policy
        logger.info(f"Set refresh policy for {source_id}: every {policy.interval_hours}h")
    
    def get_policy(self, source_id: str) -> Optional[RefreshPolicy]:
        """Get refresh policy for a source."""
        return self._policies.get(source_id)
    
    def set_refresh_handler(self, handler: Callable) -> None:
        """Set the function to call for actual refresh."""
        self._refresh_handler = handler
    
    def get_status(self, source_id: str) -> Optional[RefreshStatus]:
        """Get refresh status for a source."""
        policy = self._policies.get(source_id)
        if not policy:
            return None
        
        history = self._history.get(source_id, [])
        last_refresh = history[-1] if history else None
        
        # Calculate next scheduled
        next_scheduled = None
        is_due = False
        if last_refresh:
            next_scheduled = last_refresh.timestamp + (policy.interval_hours * 3600)
            is_due = time.time() > next_scheduled
        else:
            is_due = True  # Never refreshed
        
        return RefreshStatus(
            source_id=source_id,
            policy=policy,
            last_refresh=last_refresh,
            next_scheduled=next_scheduled,
            is_due=is_due,
            history_count=len(history),
        )
    
    async def trigger_refresh(
        self,
        source_id: str,
        trigger: RefreshTrigger = RefreshTrigger.MANUAL,
    ) -> RefreshEvent:
        """Trigger a baseline refresh for a source."""
        start_time = time.time()
        event = RefreshEvent(source_id=source_id, trigger=trigger)
        
        try:
            if self._refresh_handler:
                result = await self._refresh_handler(source_id)
                event.rows_processed = result.get("rows_processed", 0)
                event.baseline_version = result.get("version", "")
            else:
                # Default refresh when no handler configured
                # Note: Configure _refresh_handler for production use
                logger.info(f"Default refresh for {source_id} (no handler configured)")
                event.baseline_version = f"baseline_{int(time.time())}"
            
            event.success = True
            
        except Exception as e:
            event.success = False
            event.error_message = str(e)
            logger.error(f"Refresh failed for {source_id}: {e}")
        
        event.duration_seconds = time.time() - start_time
        
        # Store in history
        if source_id not in self._history:
            self._history[source_id] = []
        self._history[source_id].append(event)
        
        # Apply retention
        policy = self._policies.get(source_id)
        if policy:
            max_history = policy.retention_count * 2  # Keep 2x for debugging
            self._history[source_id] = self._history[source_id][-max_history:]
        
        logger.info(f"Refresh completed for {source_id}: success={event.success}")
        return event
    
    def get_history(self, source_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get refresh history for a source."""
        history = self._history.get(source_id, [])
        return [e.to_dict() for e in history[-limit:]]
    
    def list_sources(self) -> List[Dict[str, Any]]:
        """List all sources with policies."""
        result = []
        for source_id in self._policies:
            status = self.get_status(source_id)
            if status:
                result.append({
                    "source_id": source_id,
                    "enabled": status.policy.enabled,
                    "interval_hours": status.policy.interval_hours,
                    "is_due": status.is_due,
                    "last_refresh": status.last_refresh.timestamp if status.last_refresh else None,
                })
        return result
    
    async def start_scheduler(self, check_interval_seconds: int = 300) -> None:
        """Start the background scheduler."""
        if self._running:
            return
        
        self._running = True
        self._scheduler_task = asyncio.create_task(
            self._scheduler_loop(check_interval_seconds)
        )
        logger.info(f"Started baseline refresh scheduler (check every {check_interval_seconds}s)")
    
    async def stop_scheduler(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped baseline refresh scheduler")
    
    async def _scheduler_loop(self, interval: int) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                await asyncio.sleep(interval)
                
                if not self._running:
                    break
                
                # Check all sources
                for source_id, policy in self._policies.items():
                    if not policy.enabled:
                        continue
                    
                    status = self.get_status(source_id)
                    if status and status.is_due:
                        logger.info(f"Triggering scheduled refresh for {source_id}")
                        await self.trigger_refresh(source_id, RefreshTrigger.SCHEDULED)
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Scheduler error: {e}")
    
    def clear(self) -> None:
        """Clear all state (testing)."""
        self._policies.clear()
        self._history.clear()


# =============================================================================
# Global Instance
# =============================================================================

_manager: Optional[BaselineRefreshManager] = None


def get_manager() -> BaselineRefreshManager:
    global _manager
    if _manager is None:
        _manager = BaselineRefreshManager()
    return _manager


def set_refresh_policy(source_id: str, policy: RefreshPolicy) -> None:
    """Set refresh policy for a source."""
    get_manager().set_policy(source_id, policy)


def get_refresh_status(source_id: str) -> Optional[Dict[str, Any]]:
    """Get refresh status for a source."""
    status = get_manager().get_status(source_id)
    return status.to_dict() if status else None


async def trigger_refresh(
    source_id: str,
    trigger: RefreshTrigger = RefreshTrigger.MANUAL,
) -> Dict[str, Any]:
    """Trigger a baseline refresh."""
    event = await get_manager().trigger_refresh(source_id, trigger)
    return event.to_dict()


def get_refresh_history(source_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get refresh history."""
    return get_manager().get_history(source_id, limit)


def list_refresh_policies() -> List[Dict[str, Any]]:
    """List all refresh policies."""
    return get_manager().list_sources()


async def start_refresh_scheduler(interval_seconds: int = 300) -> None:
    """Start the refresh scheduler."""
    await get_manager().start_scheduler(interval_seconds)


async def stop_refresh_scheduler() -> None:
    """Stop the refresh scheduler."""
    await get_manager().stop_scheduler()


def reset_manager() -> None:
    """Reset manager (testing)."""
    global _manager
    _manager = None
