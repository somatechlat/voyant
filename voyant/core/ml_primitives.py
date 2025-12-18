"""
Machine Learning Primitives

Wraps Scikit-Learn for standard ML operations.
Implements Roadmap Tier 3 & Phase 3 Items.
Adheres to Vibe Coding Rules: Real implementations using sklearn.
"""
import logging
import numpy as np
import pandas as pd
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from sklearn.cluster import KMeans, DBSCAN
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, IsolationForest
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.impute import SimpleImputer
    from sklearn.metrics import silhouette_score, accuracy_score, r2_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from voyant.core.errors import AnalysisError

logger = logging.getLogger(__name__)

class MLPrimitives:
    """
    Core ML operations powered by Scikit-Learn.
    """
    
    def __init__(self):
        if not SKLEARN_AVAILABLE:
            logger.warning("Scikit-learn not found. ML primitives will fail.")

    def _check_deps(self):
        if not SKLEARN_AVAILABLE:
            raise AnalysisError("VYNT-7001", "Scikit-learn is not installed.")

    def detect_anomalies(self, data: List[Dict[str, float]], contamination: float = 0.1) -> Dict[str, Any]:
        """
        Detect anomalies using Isolation Forest.
        
        Personas:
        - PhD Developer: Uses Isolation Forest algorithm for robust outlier detection in high-dimensional space.
        - Performance Engineer: Efficient implementation using numpy/pandas vectorization.
        """
        self._check_deps()
        
        if not data:
            raise AnalysisError("VYNT-7005", "No data provided for anomaly detection")
            
        try:
            df = pd.DataFrame(data)
            # Numeric only
            df_numeric = df.select_dtypes(include=[np.number])
            
            if df_numeric.empty:
                 raise AnalysisError("VYNT-7006", "No numeric data found for anomaly detection")

            # Handle NaN
            imputer = SimpleImputer(strategy='median')
            X = imputer.fit_transform(df_numeric)
            
            # Fit Isolation Forest
            clf = IsolationForest(contamination=contamination, random_state=42)
            preds = clf.fit_predict(X) 
            # -1 is anomaly, 1 is normal
            
            # Map back to indices
            anomalies = [i for i, x in enumerate(preds) if x == -1]
            
            return {
                "total_records": len(data),
                "anomaly_count": len(anomalies),
                "anomaly_indices": anomalies,
                "contamination_params": contamination,
                "anomalies": df.iloc[anomalies].to_dict(orient="records")
            }
            
        except Exception as e:
            logger.error(f"Anomaly Detection failed: {e}", extra={"metric": "ml_inference_error", "type": "anomaly_detection"})
            raise AnalysisError("VYNT-7007", f"Anomaly Detection Error: {e}")

    def cluster_kmeans(self, data: List[Dict[str, float]], n_clusters: int = 3) -> Dict[str, Any]:
        """
        Perform K-Means clustering.
        """
        self._check_deps()
        
        if not data:
            raise AnalysisError("VYNT-7002", "No data provided for clustering")

        try:
            df = pd.DataFrame(data)
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(df)
            
            # Fit K-Means
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
            labels = kmeans.fit_predict(X_scaled)
            
            # Metrics
            score = -1.0
            if len(data) > n_clusters:
                score = silhouette_score(X_scaled, labels)
            
            df['cluster'] = labels.tolist()
            
            return {
                "clusters": labels.tolist(),
                "centroids": kmeans.cluster_centers_.tolist(),
                "silhouette_score": score,
                "labeled_data": df.to_dict(orient="records")
            }
            
        except Exception as e:
            logger.error(f"K-Means failed: {e}")
            raise AnalysisError("VYNT-7003", f"Clustering Error: {e}")

    def train_classifier(self, 
                         data: List[Dict[str, Any]], 
                         target_col: str, 
                         feature_cols: List[str]) -> Dict[str, Any]:
        """
        Train a Random Forest Classifier.
        """
        self._check_deps()
        
        try:
            df = pd.DataFrame(data)
            
            if target_col not in df.columns:
                 raise ValueError(f"Target column {target_col} not found")

            # Prepare X and y
            X = df[feature_cols]
            y = df[target_col]
            
            # Preprocessing
            # Simple numeric checks
            X = X.select_dtypes(include=[np.number])
            imputer = SimpleImputer(strategy='mean') # Basic imputation
            X_imputed = imputer.fit_transform(X)
            
            # Encoder for target if needed
            le = None
            if y.dtype == 'object':
                le = LabelEncoder()
                y = le.fit_transform(y)
                
            # Train
            clf = RandomForestClassifier(n_estimators=100, random_state=42)
            clf.fit(X_imputed, y)
            
            # Feature Importance
            importances = dict(zip(feature_cols, clf.feature_importances_.tolist()))
            
            return {
                "model_type": "RandomForestClassifier",
                "accuracy": float(clf.score(X_imputed, y)), # Training score for now
                "feature_importance": importances,
                "classes": le.classes_.tolist() if le else "numeric"
            }

        except Exception as e:
            logger.error(f"Classification failed: {e}", extra={"metric": "ml_training_error", "type": "classification"})
            raise AnalysisError("VYNT-7004", f"Classification Error: {e}")
    
    def train_regression(self, data: List[Dict[str, float]], target_col: str, feature_cols: List[str]) -> Dict[str, Any]:
        """
        Train a linear regression model.
        
        Args:
            data: Training data as list of dicts
            target_col: Name of target variable
            feature_cols: List of feature column names
        """
        self._check_deps()
        
        try:
            df = pd.DataFrame(data)
            
            # Validate columns
            missing = [c for c in feature_cols + [target_col] if c not in df.columns]
            if missing:
                raise AnalysisError("VYNT-7008", f"Missing columns: {missing}")
            
            X = df[feature_cols].values
            y = df[target_col].values
            
            # Handle NaN
            imputer = SimpleImputer(strategy='mean')
            X = imputer.fit_transform(X)
            
            # Train model
            model = LinearRegression()
            model.fit(X, y)
            
            # Predictions and metrics
            y_pred = model.predict(X)
            
            # Calculate R²
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            # RMSE
            rmse = np.sqrt(np.mean((y - y_pred) ** 2))
            
            return {
                "model_type": "linear_regression",
                "n_samples": len(data),
                "features": feature_cols,
                "target": target_col,
                "coefficients": model.coef_.tolist(),
                "intercept": float(model.intercept_),
                "r2_score": float(r2),
                "rmse": float(rmse),
                "feature_importance": {
                    feature_cols[i]: abs(model.coef_[i]) 
                    for i in range(len(feature_cols))
                }
            }
            
        except Exception as e:
            logger.error(f"Regression failed: {e}", extra={"metric": "ml_training_error", "type": "regression"})
            raise AnalysisError("VYNT-7009", f"Regression Error: {e}")
