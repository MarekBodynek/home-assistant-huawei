"""Data preprocessing for Energy ML integration."""
import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from ..const import (
    MAX_MISSING_DATA_PERCENT,
    OUTLIER_STD_THRESHOLD,
)

_LOGGER = logging.getLogger(__name__)


class DataPreprocessor:
    """Preprocess and clean collected data."""

    def __init__(self):
        """Initialize preprocessor."""
        self.scaler = StandardScaler()
        self._numeric_columns = []
        self._categorical_columns = []

    def clean_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, any]]:
        """
        Clean and preprocess data.

        Steps:
        1. Remove duplicates
        2. Handle missing values
        3. Remove outliers
        4. Forward fill remaining gaps

        Args:
            df: Raw DataFrame from collector

        Returns:
            Tuple of (cleaned DataFrame, statistics dict)
        """
        try:
            stats = {
                "original_rows": len(df),
                "original_columns": len(df.columns),
                "duplicates_removed": 0,
                "outliers_removed": 0,
                "missing_filled": 0,
                "columns_dropped": [],
            }

            if df.empty:
                _LOGGER.warning("Empty DataFrame provided to clean_data")
                return df, stats

            _LOGGER.info(f"Cleaning data: {len(df)} rows, {len(df.columns)} columns")

            # 1. Remove duplicates
            df_clean = df.copy()
            duplicates = df_clean.index.duplicated(keep="first")
            if duplicates.any():
                stats["duplicates_removed"] = duplicates.sum()
                df_clean = df_clean[~duplicates]
                _LOGGER.info(f"Removed {stats['duplicates_removed']} duplicate rows")

            # 2. Identify numeric and categorical columns
            self._numeric_columns = df_clean.select_dtypes(
                include=[np.number]
            ).columns.tolist()
            self._categorical_columns = df_clean.select_dtypes(
                exclude=[np.number]
            ).columns.tolist()

            _LOGGER.debug(
                f"Numeric columns: {len(self._numeric_columns)}, "
                f"Categorical columns: {len(self._categorical_columns)}"
            )

            # 3. Handle missing values
            missing_stats = self._handle_missing_values(df_clean)
            stats.update(missing_stats)

            # 4. Remove outliers (only for numeric columns)
            outlier_stats = self._remove_outliers(df_clean)
            stats.update(outlier_stats)

            # 5. Drop columns with too much missing data
            columns_to_drop = []
            for col in df_clean.columns:
                missing_pct = df_clean[col].isna().sum() / len(df_clean)
                if missing_pct > MAX_MISSING_DATA_PERCENT:
                    columns_to_drop.append(col)
                    _LOGGER.warning(
                        f"Dropping column {col}: {missing_pct:.1%} missing data"
                    )

            if columns_to_drop:
                df_clean = df_clean.drop(columns=columns_to_drop)
                stats["columns_dropped"] = columns_to_drop

            # 6. Forward fill remaining missing values
            df_clean = df_clean.fillna(method="ffill", limit=6)  # Max 6 hours forward fill
            df_clean = df_clean.fillna(method="bfill", limit=6)  # Backfill if still missing

            # 7. Drop any remaining rows with NaN
            rows_before = len(df_clean)
            df_clean = df_clean.dropna()
            rows_dropped = rows_before - len(df_clean)
            if rows_dropped > 0:
                _LOGGER.warning(f"Dropped {rows_dropped} rows with remaining NaN values")

            stats["final_rows"] = len(df_clean)
            stats["final_columns"] = len(df_clean.columns)
            stats["data_quality"] = self._calculate_data_quality(df_clean)

            _LOGGER.info(
                f"Data cleaning complete: {stats['final_rows']} rows, "
                f"{stats['final_columns']} columns, "
                f"quality: {stats['data_quality']:.1%}"
            )

            return df_clean, stats

        except Exception as e:
            _LOGGER.error(f"Error in clean_data: {e}", exc_info=True)
            return df, stats

    def _handle_missing_values(self, df: pd.DataFrame) -> Dict[str, int]:
        """
        Analyze and report missing values.

        Args:
            df: DataFrame to analyze

        Returns:
            Dict with missing value statistics
        """
        try:
            total_missing = df.isna().sum().sum()
            missing_by_column = df.isna().sum()

            stats = {
                "total_missing": int(total_missing),
                "missing_percent": float(total_missing / (len(df) * len(df.columns))),
            }

            if total_missing > 0:
                _LOGGER.debug(
                    f"Missing values: {total_missing} "
                    f"({stats['missing_percent']:.1%})"
                )

                # Log columns with most missing data
                top_missing = missing_by_column[missing_by_column > 0].sort_values(
                    ascending=False
                ).head(5)
                if not top_missing.empty:
                    _LOGGER.debug(f"Top missing columns:\n{top_missing}")

            return stats

        except Exception as e:
            _LOGGER.error(f"Error handling missing values: {e}")
            return {"total_missing": 0, "missing_percent": 0.0}

    def _remove_outliers(self, df: pd.DataFrame) -> Dict[str, int]:
        """
        Remove outliers using Z-score method.

        Outliers are defined as values > OUTLIER_STD_THRESHOLD standard deviations
        from the mean.

        Args:
            df: DataFrame to process (modified in-place)

        Returns:
            Dict with outlier statistics
        """
        try:
            outliers_removed = 0

            for col in self._numeric_columns:
                if col not in df.columns:
                    continue

                # Calculate Z-score
                mean = df[col].mean()
                std = df[col].std()

                if std == 0:
                    continue  # Skip columns with no variance

                z_scores = np.abs((df[col] - mean) / std)

                # Mark outliers as NaN
                outliers = z_scores > OUTLIER_STD_THRESHOLD
                outlier_count = outliers.sum()

                if outlier_count > 0:
                    df.loc[outliers, col] = np.nan
                    outliers_removed += outlier_count
                    _LOGGER.debug(
                        f"Removed {outlier_count} outliers from {col} "
                        f"(>{OUTLIER_STD_THRESHOLD}σ)"
                    )

            if outliers_removed > 0:
                _LOGGER.info(f"Total outliers removed: {outliers_removed}")

            return {"outliers_removed": outliers_removed}

        except Exception as e:
            _LOGGER.error(f"Error removing outliers: {e}")
            return {"outliers_removed": 0}

    def _calculate_data_quality(self, df: pd.DataFrame) -> float:
        """
        Calculate overall data quality score (0-1).

        Quality factors:
        - Completeness (no missing values)
        - Consistency (no outliers)
        - Coverage (time span)

        Args:
            df: Cleaned DataFrame

        Returns:
            Quality score between 0 and 1
        """
        try:
            if df.empty:
                return 0.0

            # Completeness score (1 - missing%)
            missing_pct = df.isna().sum().sum() / (len(df) * len(df.columns))
            completeness = 1.0 - missing_pct

            # Consistency score (assume good after outlier removal)
            consistency = 0.95

            # Coverage score (based on time span)
            time_span = (df.index.max() - df.index.min()).total_seconds() / 86400  # days
            expected_span = 30  # days
            coverage = min(time_span / expected_span, 1.0)

            # Overall quality (weighted average)
            quality = (
                0.5 * completeness +
                0.3 * consistency +
                0.2 * coverage
            )

            return float(quality)

        except Exception as e:
            _LOGGER.error(f"Error calculating data quality: {e}")
            return 0.0

    def normalize_features(
        self, df: pd.DataFrame, fit: bool = True
    ) -> pd.DataFrame:
        """
        Normalize numeric features using StandardScaler.

        Args:
            df: DataFrame with features
            fit: If True, fit scaler on data. If False, use previously fitted scaler.

        Returns:
            DataFrame with normalized features
        """
        try:
            if df.empty:
                return df

            df_normalized = df.copy()

            # Only normalize numeric columns
            numeric_cols = df_normalized.select_dtypes(
                include=[np.number]
            ).columns.tolist()

            if not numeric_cols:
                _LOGGER.warning("No numeric columns to normalize")
                return df_normalized

            if fit:
                # Fit and transform
                df_normalized[numeric_cols] = self.scaler.fit_transform(
                    df_normalized[numeric_cols]
                )
                _LOGGER.info(f"Fitted and normalized {len(numeric_cols)} features")
            else:
                # Transform only
                df_normalized[numeric_cols] = self.scaler.transform(
                    df_normalized[numeric_cols]
                )
                _LOGGER.debug(f"Normalized {len(numeric_cols)} features")

            return df_normalized

        except Exception as e:
            _LOGGER.error(f"Error normalizing features: {e}")
            return df

    def validate_data(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Validate data quality and completeness.

        Args:
            df: DataFrame to validate

        Returns:
            Tuple of (is_valid, list of validation errors)
        """
        errors = []

        try:
            # Check if DataFrame is empty
            if df.empty:
                errors.append("DataFrame is empty")
                return False, errors

            # Check minimum number of rows (7 days * 24 hours = 168 rows)
            min_rows = 168
            if len(df) < min_rows:
                errors.append(
                    f"Insufficient data: {len(df)} rows (minimum: {min_rows})"
                )

            # Check for missing critical columns
            critical_columns = [
                "battery_soc",
                "pv_power",
                "grid_power",
                "temp_outdoor",
            ]
            for col in critical_columns:
                if col not in df.columns:
                    errors.append(f"Missing critical column: {col}")

            # Check data quality
            quality = self._calculate_data_quality(df)
            if quality < 0.7:
                errors.append(
                    f"Data quality too low: {quality:.1%} (minimum: 70%)"
                )

            # Check time span
            if not df.empty:
                time_span = (df.index.max() - df.index.min()).total_seconds() / 86400
                if time_span < 7:
                    errors.append(
                        f"Insufficient time span: {time_span:.1f} days (minimum: 7)"
                    )

            is_valid = len(errors) == 0

            if is_valid:
                _LOGGER.info("Data validation passed")
            else:
                _LOGGER.warning(f"Data validation failed: {errors}")

            return is_valid, errors

        except Exception as e:
            _LOGGER.error(f"Error in validate_data: {e}")
            errors.append(f"Validation error: {str(e)}")
            return False, errors
