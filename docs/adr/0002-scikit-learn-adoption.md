# 2. Scikit-Learn Adoption

Date: 2025-12-17

## Status

Accepted

## Context

Voyant requires statistical analysis capabilities, specifically Anomaly Detection and Time Series Forecasting, to fulfill the "Advanced Analytics" roadmap phase. We needed a library that provides these algorithms with minimal operational overhead (no heavy GPU requirement, simple pip install).

## Decision

We adopted `scikit-learn` as the primary machine learning library for:
- **Anomaly Detection**: Using `IsolationForest`.
- **Forecasting**: Using `LinearRegression` with feature engineering.

## Consequences

### Positive
- **Maturity**: Well-tested, industry-standard algorithms.
- **Performance**: Efficient implementations (Cython/C) suitable for the "Performance Engineer" persona.
- **Simplicity**: Easy to integrate into the existing Python service environment.

### Negative
- **Dependency Size**: Adds a non-trivial dependency (numpy/scipy/sklearn) to the build, though manageable for modern containers.
