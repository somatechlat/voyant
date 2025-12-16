"""
Statistical Engine Module

Provides high-level statistical analysis functions using the R backend.
"""
from typing import Dict, Any, List, Optional
import logging
import pandas as pd
from voyant.core.r_bridge import REngine
from voyant.core.errors import ValidationError

logger = logging.getLogger(__name__)

class StatisticalEngine:
    """
    High-level interface for statistical analysis.
    Delegates complex calculations to R via REngine.
    """
    
    def __init__(self):
        self.r = REngine()

    def _sanitize_col(self, col: str) -> str:
        """Sanitize column name for R usage."""
        # Simple sanitization - ideally use backticks in R but Rserve usage might vary
        return col.replace(" ", "_").replace("-", "_")

    def check_normality(self, df: pd.DataFrame, column: str) -> Dict[str, Any]:
        """
        Run Shapiro-Wilk test for normality.
        H0: Data is normally distributed.
        p < 0.05 -> Reject H0 (Data is NOT normal)
        """
        if len(df) < 3 or len(df) > 5000:
             # Shapiro-Wilk limit in R
             # Shapiro-Wilk limit in R
             # Ideally we would fallback to Anderson-Darling, but for now we raise a clear validation error
             # to avoid misleading results or silent failures.
             logger.warning(f"Shapiro-Wilk test requires 3 <= N <= 5000. Found N={len(df)}")
             raise ValidationError(
                 "VYNT-1002", 
                 f"Shapiro-Wilk test requires 3 <= N <= 5000 rows. Provided: {len(df)}.",
                 resolution="Use a sample of the dataset or a different distribution test."
             )

        self.r.assign("data", df[[column]])
        # Determine R column name - pyRserve/pandas conversion usually keeps names
        r_col = column
        
        cmd = f"res <- shapiro.test(data[['{r_col}']])"
        self.r.eval(cmd)
        
        return {
            "test": "Shapiro-Wilk",
            "statistic": float(self.r.eval("res$statistic")),
            "p_value": float(self.r.eval("res$p.value")),
            "is_normal": float(self.r.eval("res$p.value")) > 0.05
        }

    def anova(self, df: pd.DataFrame, value_col: str, group_col: str) -> Dict[str, Any]:
        """
        Run One-way ANOVA.
        """
        if df[group_col].nunique() < 2:
            raise ValidationError("VYNT-1002", "ANOVA requires at least 2 groups")

        self.r.assign("df", df[[value_col, group_col]])
        
        # Use aov()
        # Note: referencing columns in df via string names in formula
        cmd = f"model <- aov(df[['{value_col}']] ~ df[['{group_col}']])"
        self.r.eval(cmd)
        self.r.eval("res <- summary(model)")
        
        # Extract F and p from summary list
        # summary(model)[[1]] is the table
        # We need to extract safely.
        f_val = self.r.eval("res[[1]][['F value']][1]")
        p_val = self.r.eval("res[[1]][['Pr(>F)']][1]")
        
        return {
            "test": "One-way ANOVA",
            "f_statistic": float(f_val) if f_val is not None else 0.0,
            "p_value": float(p_val) if p_val is not None else 1.0,
            "significant": float(p_val) < 0.05 if p_val is not None else False
        }

    def t_test(self, df: pd.DataFrame, group_col: str, value_col: str) -> Dict[str, Any]:
        """
        Run Welch Two Sample t-test.
        """
        groups = df[group_col].unique()
        if len(groups) != 2:
            raise ValidationError("VYNT-1002", f"T-test requires exactly 2 groups, found {len(groups)}")
            
        self.r.assign("df", df[[value_col, group_col]])
        
        cmd = f"res <- t.test(df[['{value_col}']] ~ df[['{group_col}']])"
        self.r.eval(cmd)
        
        return {
            "test": "Welch Two Sample t-test",
            "statistic": float(self.r.eval("res$statistic")),
            "p_value": float(self.r.eval("res$p.value")),
            "significant": float(self.r.eval("res$p.value")) < 0.05,
            "mean_group1": float(self.r.eval("res$estimate[1]")),
            "mean_group2": float(self.r.eval("res$estimate[2]"))
        }

    def correlation_matrix(self, df: pd.DataFrame, method: str = "pearson") -> pd.DataFrame:
        """
        Calculate correlation matrix using R (faster/more robust for some types).
        """
        self.r.assign("df", df.select_dtypes(include=['number']))
        self.r.eval(f"res <- cor(df, use='complete.obs', method='{method}')")
        
        # Convert back
        # res is a matrix in R
        # pyRserve typically returns numpy array for matrix
        res = self.r.eval("res")
        
        # Reconstruct DataFrame (need column names)
        cols = list(df.select_dtypes(include=['number']).columns)
        return pd.DataFrame(res, columns=cols, index=cols)
