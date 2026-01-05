"""
Linear Regression Analysis Workflow: Orchestrates Statistical Modeling.

This Temporal workflow defines the automated process for performing linear
regression analysis on a given dataset. It delegates the computationally
intensive model training to a dedicated activity and then processes the
results to provide a human-readable equation and an interpretation of
the model's quality.
"""

from datetime import timedelta
from typing import Any, Dict, List

from temporalio import workflow

# This context manager is necessary to allow importing non-workflow/activity
# modules within the workflow definition. It passes control to the Python
# import system directly, bypassing Temporal's default import handling.
with workflow.unsafe.imports_passed_through():
    from voyant.activities.ml_activities import MLActivities


@workflow.defn
class LinearRegressionWorkflow:
    """
    Temporal workflow for orchestrating linear regression analysis.
    """

    @workflow.run
    async def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the linear regression analysis workflow.

        This method coordinates the training of a linear regression model
        and formats its output for clarity.

        Args:
            params: A dictionary containing the regression configuration:
                - `data` (List[Dict[str, float]]): The input dataset for training.
                - `target_col` (str): The name of the target (dependent) variable column.
                - `feature_cols` (List[str]): A list of feature (independent) variable column names.

        Returns:
            A dictionary containing the analysis results, including model coefficients,
            metrics, a formatted equation, and a qualitative assessment of model quality.
        """
        data = params.get("data", [])
        target_col = params.get("target_col", "target")
        feature_cols = params.get("feature_cols", [])

        workflow.logger.info(
            f"Starting LINEAR_REGRESSION: target='{target_col}' with {len(feature_cols)} features."
        )

        # Execute the activity that trains the linear regression model.
        # This offloads the heavy computation to a separate activity worker.
        result = await workflow.execute_activity(
            MLActivities.train_regression_model,
            {"data": data, "target_col": target_col, "feature_cols": feature_cols},
            start_to_close_timeout=timedelta(minutes=10), # Allow up to 10 minutes for model training.
        )

        # Post-process results for a user-friendly summary.
        return {
            "status": "completed",
            "analysis": result,
            "model_summary": {
                "equation": self._format_equation(result),
                "quality": self._interpret_r2(result.get("r2_score", 0)),
            },
        }

    def _format_equation(self, result: Dict[str, Any]) -> str:
        """
        Formats the regression model's coefficients into a human-readable equation string.

        Args:
            result: The raw results dictionary from the regression activity.

        Returns:
            A string representing the regression equation (e.g., "y = 1.23 + 0.45*x1 - 0.12*x2").
        """
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
        """
        Interprets the R-squared score qualitatively.

        Args:
            r2: The R-squared value of the regression model (0.0 to 1.0).

        Returns:
            A qualitative assessment string (e.g., "excellent", "good", "poor").
        """
        if r2 >= 0.9:
            return "excellent"
        elif r2 >= 0.7:
            return "good"
        elif r2 >= 0.5:
            return "moderate"
        else:
            return "poor"
