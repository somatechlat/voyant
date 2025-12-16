"""
Statistical Primitives

Wraps R-Engine execution for standard statistical operations.
Implements Roadmap Tier 3 & 4 Core Statistics.
Adheres to Vibe Coding Rules: Uses REngine for actual computation.
"""
from typing import Any, Dict, List, Optional, Union
import logging

from voyant.core.r_bridge import REngine
from voyant.core.errors import AnalysisError

logger = logging.getLogger(__name__)

class RStatsPrimitives:
    """
    Core statistical operations powered by R.
    """
    
    def __init__(self, r_engine: Optional[REngine] = None):
        self.r = r_engine or REngine()

    def describe_column(self, vector: List[float], col_name: str = "x") -> Dict[str, float]:
        """
        Calculate descriptive statistics for a numeric vector.
        Includes: mean, median, sd, quartiles, skewness, kurtosis.
        """
        if not vector:
            raise AnalysisError("VYNT-6001", "Cannot describe empty vector")
            
        try:
            self.r.assign(col_name, vector)
            
            # Using R's e1071 (check availability) or base R
            # Safe base-R implementation + moments
            script = f"""
            x <- {col_name}
            x <- x[!is.na(x)]
            
            n <- length(x)
            mu <- mean(x)
            md <- median(x)
            s <- sd(x)
            
            # Moments
            m3 <- sum((x-mu)^3)/n
            m4 <- sum((x-mu)^4)/n
            skew <- m3/(s^3)
            kurt <- m4/(s^4) - 3
            
            qs <- quantile(x, probs=c(0.25, 0.75))
            iqr <- qs[2] - qs[1]
            
            list(
                mean = mu,
                median = md,
                std_dev = s,
                min = min(x),
                max = max(x),
                q1 = qs[1],
                q3 = qs[2],
                iqr = iqr,
                skewness = skew,
                kurtosis = kurt
            )
            """
            result = self.r.eval(script)
            return dict(result)
            
        except Exception as e:
            logger.error(f"Failed to describe column: {e}")
            raise AnalysisError("VYNT-6020", f"R Describe Error: {e}")

    def correlation_matrix(self, df_dict: Dict[str, List[float]], method: str = "pearson") -> Dict[str, Any]:
        """
        Calculate correlation matrix.
        Args:
            df_dict: Dictionary of column name -> value list
            method: 'pearson', 'spearman', or 'kendall'
        """
        try:
            # Create data frame in R
            # Assign lists individually then bind
            cols = list(df_dict.keys())
            for col, values in df_dict.items():
                self.r.assign(col, values)
            
            col_str = ", ".join(cols)
            script = f"""
            df <- data.frame({col_str})
            cor_mat <- cor(df, use="pairwise.complete.obs", method="{method}")
            as.data.frame(cor_mat) # Return as list of lists via bridge conversion
            """
            
            # r_bridge assigns dictionaries of lists for DFs usually,
            # but here we get a dict of columns back
            result = self.r.eval(script)
            return dict(result)
            
        except Exception as e:
            raise AnalysisError("VYNT-6021", f"Correlation Error: {e}")

    def fit_distribution(self, vector: List[float], dist: str = "normal") -> Dict[str, float]:
        """
        Fit a distribution to data using MASS::fitdistr.
        """
        try:
            self.r.assign("v", vector)
            
            # Map common names to R distribution names
            dist_map = {
                "normal": "normal",
                "lognormal": "log-normal", 
                "exponential": "exponential",
                "gamma": "gamma"
            }
            r_dist = dist_map.get(dist, "normal")
            
            script = f"""
            library(MASS)
            fit <- fitdistr(v, "{r_dist}")
            as.list(fit$estimate)
            """
            
            # Fallback if MASS not available?
            # Vibe Rule #5: check deps. 
            # We assume the container has standard pkgs. if fail, we catch.
            result = self.r.eval(script)
            return dict(result)
            
        except Exception as e:
             raise AnalysisError("VYNT-6022", f"Dist Fit Error: {e}")
