"""
Linear Regression Analysis Workflow

LINEAR_REGRESSION_ANALYSIS preset.
Adheres to Vibe Coding Rules: Real scikit-learn LinearRegression.
"""
from datetime import timedelta
from typing import Any, Dict

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from voyant.activities.ml_activities import MLActivities

@workflow.defn
class LinearRegressionWorkflow:
    @workflow.run
    async def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run linear regression analysis.
        
        Args:
            params: {
                "data": List[Dict[str, float]]
                "target_col": str
                "feature_cols": List[str]
            }
        """
        data = params.get("data", [])
        target_col = params.get("target_col", "target")
        feature_cols = params.get("feature_cols", [])
        
        workflow.logger.info(f"Starting LINEAR_REGRESSION: {target_col} ~ {len(feature_cols)} features")
        
        result = await workflow.execute_activity(
            MLActivities.train_regression_model,
            {
                "data": data,
                "target_col": target_col,
                "feature_cols": feature_cols
            },
            start_to_close_timeout=timedelta(minutes=10)
        )
        
        return {
            "status": "completed",
            "analysis": result,
            "model_summary": {
                "equation": self._format_equation(result),
                "quality": self._interpret_r2(result.get("r2_score", 0))
            }
        }
    
    def _format_equation(self, result: Dict[str, Any]) -> str:
        """Format regression equation."""
        target = result.get("target", "y")
        intercept = result.get("intercept", 0)
        coefs = result.get("coefficients", [])
        features = result.get("features", [])
        
        terms = [f"{intercept:.2f}"]
        for i, (feat, coef) in enumerate(zip(features, coefs)):
            sign = "+" if coef >= 0 else "-"
            terms.append(f"{sign} {abs(coef):.2f}*{feat}")
        
        return f"{target} = " + " ".join(terms)
    
    def _interpret_r2(self, r2: float) -> str:
        """Interpret R² score."""
        if r2 >= 0.9:
            return "excellent"
        elif r2 >= 0.7:
            return "good"
        elif r2 >= 0.5:
            return "moderate"
        else:
            return "poor"
