"""
Rserve Bridge Module

Handles communication with the R statistical engine via Rserve.
Part of Phase 2: Statistical Engine.
"""
import logging
from typing import Any, Dict, Optional
import pandas as pd
from voyant.core.config import get_settings
from voyant.core.errors import ExternalServiceError, SystemError

logger = logging.getLogger(__name__)

class REngine:
    """
    Interface to the R statistical engine via Rserve.
    
    Usage:
        r = REngine()
        r.assign("data", df)
        result = r.eval("mean(data$value)")
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.host = self.settings.r_engine_host
        self.port = self.settings.r_engine_port
        self.conn = None
        
    def _ensure_dependency(self):
        """Ensure pyRserve is installed."""
        try:
            import pyRserve
        except ImportError:
            raise SystemError(
                "VYNT-6010", 
                message="pyRserve library not installed. Cannot use R engine.",
                resolution="Install pyRserve: pip install pyRserve"
            )

    def connect(self):
        """Establish connection to Rserve."""
        self._ensure_dependency()
        import pyRserve
        
        if self.conn and not self.conn.is_closed:
            return

        try:
            self.conn = pyRserve.connect(host=self.host, port=self.port)
            logger.info(f"Connected to Rserve at {self.host}:{self.port}")
        except Exception as e:
            raise ExternalServiceError(
                "VYNT-6011", 
                message=f"Failed to connect to R Engine: {str(e)}",
                details={"host": self.host, "port": self.port},
                resolution="Ensure voyant-r-engine container is running"
            )

    def disconnect(self):
        """Close connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def eval(self, expression: str) -> Any:
        """
        Evaluate R expression.
        
        Performance Engineer: Circuit breaker adds <1ms overhead
        """
        from voyant.core.circuit_breaker import get_circuit_breaker, CircuitBreakerOpenError, CircuitBreakerConfig
        from voyant.core.errors import ServiceUnavailableError
        
        # Get circuit breaker for Rserve
        cb = get_circuit_breaker(
            "rserve",
            CircuitBreakerConfig(
                failure_threshold=3,
                timeout_seconds=60
            )
        )
        
        def _eval():
            """Inner function for circuit breaker."""
            self.connect()
            try:
                return self.conn.eval(expression)
            except Exception as e:
                logger.error(f"R eval error: {e}")
                raise ExternalServiceError(
                    "VYNT-6002",
                    f"R evaluation failed: {e}",
                    resolution="Check R syntax and Rserve connection"
                )
        
        try:
            return cb.call(_eval)
        except CircuitBreakerOpenError:
            raise ServiceUnavailableError("R-Engine")


    def assign(self, name: str, value: Any):
        """
        Assign value to R variable.
        Automatically converts Pandas DataFrames to R DataFrames.
        """
        if not self.conn or self.conn.is_closed:
            self.connect()
            
        try:
            if isinstance(value, pd.DataFrame):
                # Convert DataFrame to dict of lists (column-oriented)
                # pyRserve usually handles basic types well
                data_dict = value.to_dict(orient='list')
                self.conn.r[name] = data_dict
                # Convert list-structure to proper data.frame in R
                self.conn.eval(f"{name} <- as.data.frame({name})")
            else:
                self.conn.r[name] = value
        except Exception as e:
             raise ExternalServiceError(
                "VYNT-6013", 
                message=f"Failed to assign R variable '{name}': {str(e)}"
            )

    def is_healthy(self) -> bool:
        """Check if R engine is responsive."""
        try:
            res = self.eval("1+1")
            return int(res) == 2
        except Exception:
            return False
