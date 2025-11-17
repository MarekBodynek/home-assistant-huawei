"""Feature engineering for Energy ML integration."""
import logging
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from ..const import (
    FEATURE_LAG_HOURS,
    FEATURE_ROLLING_WINDOWS,
)

_LOGGER = logging.getLogger(__name__)


class FeatureEngineer:
    """Create features for machine learning models."""

    def __init__(self):
        """Initialize feature engineer."""
        self._feature_columns = []

    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create all features from raw data.

        Args:
            df: Cleaned DataFrame from preprocessor

        Returns:
            DataFrame with engineered features
        """
        try:
            if df.empty:
                _LOGGER.warning("Empty DataFrame provided to create_features")
                return df

            _LOGGER.info(f"Creating features from {len(df)} rows")

            df_features = df.copy()

            # 1. Calendar features
            df_features = self._add_calendar_features(df_features)

            # 2. Lag features (1h, 24h, 7d ago)
            df_features = self._add_lag_features(df_features)

            # 3. Rolling window features (3h, 6h, 24h averages)
            df_features = self._add_rolling_features(df_features)

            # 4. Solar/astronomical features
            df_features = self._add_solar_features(df_features)

            # 5. Energy balance features
            df_features = self._add_energy_balance_features(df_features)

            # 6. Interaction features
            df_features = self._add_interaction_features(df_features)

            # Store feature column names
            self._feature_columns = df_features.columns.tolist()

            _LOGGER.info(
                f"Feature engineering complete: {len(df_features)} rows, "
                f"{len(df_features.columns)} features"
            )

            return df_features

        except Exception as e:
            _LOGGER.error(f"Error in create_features: {e}", exc_info=True)
            return df

    def _add_calendar_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add calendar-based features.

        Features:
        - hour: 0-23
        - day_of_week: 0-6 (Monday=0)
        - month: 1-12
        - week_of_year: 1-52
        - season: 0-3 (winter=0, spring=1, summer=2, fall=3)
        - is_weekend: 0/1
        """
        try:
            df["hour"] = df.index.hour
            df["day_of_week"] = df.index.dayofweek
            df["month"] = df.index.month
            df["week_of_year"] = df.index.isocalendar().week
            df["day_of_year"] = df.index.dayofyear

            # Season (0=winter, 1=spring, 2=summer, 3=fall)
            df["season"] = (df["month"] % 12 + 3) // 3 - 1

            # Weekend (Saturday=5, Sunday=6)
            df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)

            # Cyclical encoding for hour and month
            df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
            df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
            df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
            df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)

            _LOGGER.debug("Added calendar features")
            return df

        except Exception as e:
            _LOGGER.error(f"Error adding calendar features: {e}")
            return df

    def _add_lag_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add lag features (historical values).

        Creates lagged versions of key columns for 1h, 24h, 168h ago.
        """
        try:
            # Columns to create lags for
            lag_columns = [
                "battery_soc",
                "pv_power",
                "grid_power",
                "temp_outdoor",
            ]

            for col in lag_columns:
                if col not in df.columns:
                    continue

                for lag_hours in FEATURE_LAG_HOURS:
                    lag_col_name = f"{col}_lag_{lag_hours}h"
                    df[lag_col_name] = df[col].shift(lag_hours)

                    # Also add change (delta) features
                    if lag_hours > 0:
                        change_col_name = f"{col}_change_{lag_hours}h"
                        df[change_col_name] = df[col] - df[f"{col}_lag_{lag_hours}h"]

            _LOGGER.debug(f"Added lag features for {len(lag_columns)} columns")
            return df

        except Exception as e:
            _LOGGER.error(f"Error adding lag features: {e}")
            return df

    def _add_rolling_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add rolling window features (moving averages, std, min, max).

        Creates rolling statistics for 3h, 6h, 24h windows.
        """
        try:
            # Columns to create rolling features for
            rolling_columns = [
                "battery_soc",
                "pv_power",
                "grid_power",
                "temp_outdoor",
            ]

            for col in rolling_columns:
                if col not in df.columns:
                    continue

                for window_hours in FEATURE_ROLLING_WINDOWS:
                    # Rolling mean
                    mean_col_name = f"{col}_rolling_mean_{window_hours}h"
                    df[mean_col_name] = df[col].rolling(
                        window=window_hours, min_periods=1
                    ).mean()

                    # Rolling std (volatility)
                    std_col_name = f"{col}_rolling_std_{window_hours}h"
                    df[std_col_name] = df[col].rolling(
                        window=window_hours, min_periods=1
                    ).std()

                    # Rolling min/max (for some columns)
                    if col in ["pv_power", "battery_soc"]:
                        min_col_name = f"{col}_rolling_min_{window_hours}h"
                        max_col_name = f"{col}_rolling_max_{window_hours}h"
                        df[min_col_name] = df[col].rolling(
                            window=window_hours, min_periods=1
                        ).min()
                        df[max_col_name] = df[col].rolling(
                            window=window_hours, min_periods=1
                        ).max()

            _LOGGER.debug(f"Added rolling features for {len(rolling_columns)} columns")
            return df

        except Exception as e:
            _LOGGER.error(f"Error adding rolling features: {e}")
            return df

    def _add_solar_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add solar/astronomical features.

        Features:
        - daylight_hours: Length of day
        - is_daylight: Whether sun is above horizon
        - solar_elevation/azimuth (if available from sensors)
        """
        try:
            # If solar_elevation and solar_azimuth exist, use them
            if "solar_elevation" in df.columns:
                df["is_daylight"] = (df["solar_elevation"] > 0).astype(int)

            # Calculate approximate daylight hours based on day of year and latitude
            # Latitude for Warsaw: 52.2297°N
            latitude = 52.2297
            df["daylight_hours"] = self._calculate_daylight_hours(
                df["day_of_year"], latitude
            )

            # Solar angle features (if available)
            if "solar_elevation" in df.columns:
                # Normalize solar elevation (0-90 degrees)
                df["solar_elevation_norm"] = df["solar_elevation"] / 90.0

            if "solar_azimuth" in df.columns:
                # Cyclical encoding for azimuth (0-360 degrees)
                df["solar_azimuth_sin"] = np.sin(
                    2 * np.pi * df["solar_azimuth"] / 360
                )
                df["solar_azimuth_cos"] = np.cos(
                    2 * np.pi * df["solar_azimuth"] / 360
                )

            _LOGGER.debug("Added solar features")
            return df

        except Exception as e:
            _LOGGER.error(f"Error adding solar features: {e}")
            return df

    def _calculate_daylight_hours(
        self, day_of_year: pd.Series, latitude: float
    ) -> pd.Series:
        """
        Calculate approximate daylight hours using astronomical formula.

        Args:
            day_of_year: Day of year (1-365)
            latitude: Latitude in degrees

        Returns:
            Series with daylight hours
        """
        try:
            # Solar declination angle
            declination = 23.45 * np.sin(
                2 * np.pi * (day_of_year - 81) / 365
            )

            # Hour angle
            lat_rad = np.radians(latitude)
            dec_rad = np.radians(declination)

            hour_angle = np.arccos(
                -np.tan(lat_rad) * np.tan(dec_rad)
            )

            # Daylight hours
            daylight = 2 * np.degrees(hour_angle) / 15

            # Clamp to realistic values
            daylight = daylight.clip(0, 24)

            return daylight

        except Exception as e:
            _LOGGER.error(f"Error calculating daylight hours: {e}")
            return pd.Series([12] * len(day_of_year))

    def _add_energy_balance_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add energy balance features.

        Features:
        - pv_surplus: PV power - grid power (when positive)
        - power_deficit: grid power - PV power (when positive)
        - battery_charge_rate: Rate of battery charging
        """
        try:
            if "pv_power" in df.columns and "grid_power" in df.columns:
                # PV surplus (positive = exporting to grid)
                df["pv_surplus"] = (df["pv_power"] - df["grid_power"]).clip(lower=0)

                # Power deficit (positive = importing from grid)
                df["power_deficit"] = (df["grid_power"] - df["pv_power"]).clip(lower=0)

            if "battery_soc" in df.columns:
                # Battery charge rate (change per hour)
                df["battery_charge_rate"] = df["battery_soc"].diff()

            if "battery_power" in df.columns:
                # Battery utilization (normalized by max power 5000W)
                df["battery_utilization"] = (df["battery_power"] / 5000).clip(-1, 1)

            _LOGGER.debug("Added energy balance features")
            return df

        except Exception as e:
            _LOGGER.error(f"Error adding energy balance features: {e}")
            return df

    def _add_interaction_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add interaction features (combinations of multiple features).

        Features:
        - temp_hour: Temperature × hour (captures daily temp patterns)
        - heating_season_temp: Heating season × temperature
        - workday_hour: Workday × hour (captures workday patterns)
        """
        try:
            # Temperature × hour interaction
            if "temp_outdoor" in df.columns and "hour" in df.columns:
                df["temp_hour_interaction"] = df["temp_outdoor"] * df["hour"]

            # Heating season × temperature
            if "heating_season" in df.columns and "temp_outdoor" in df.columns:
                df["heating_temp_interaction"] = (
                    df["heating_season"].astype(int) * df["temp_outdoor"]
                )

            # Workday × hour
            if "workday" in df.columns and "hour" in df.columns:
                df["workday_hour_interaction"] = (
                    df["workday"].astype(int) * df["hour"]
                )

            # Weekend × hour
            if "is_weekend" in df.columns and "hour" in df.columns:
                df["weekend_hour_interaction"] = df["is_weekend"] * df["hour"]

            # PC active × temperature
            if "pc_co_active" in df.columns and "temp_outdoor" in df.columns:
                df["pc_temp_interaction"] = (
                    df["pc_co_active"].astype(int) * df["temp_outdoor"]
                )

            _LOGGER.debug("Added interaction features")
            return df

        except Exception as e:
            _LOGGER.error(f"Error adding interaction features: {e}")
            return df

    def get_feature_importance_columns(self) -> List[str]:
        """
        Get list of most important feature columns for models.

        Returns:
            List of feature column names ordered by expected importance
        """
        # Order features by expected importance (from domain knowledge)
        important_features = [
            # Calendar features (most important for consumption)
            "hour", "day_of_week", "month", "season",
            "is_weekend", "workday",
            "hour_sin", "hour_cos",

            # Historical lags (patterns)
            "battery_soc_lag_24h", "battery_soc_lag_168h",
            "pv_power_lag_24h", "pv_power_lag_168h",
            "grid_power_lag_24h", "grid_power_lag_168h",

            # Rolling averages (smoothed trends)
            "battery_soc_rolling_mean_24h",
            "pv_power_rolling_mean_6h",
            "grid_power_rolling_mean_6h",

            # Solar features (critical for PV production)
            "solar_elevation", "solar_elevation_norm",
            "daylight_hours", "is_daylight",

            # Weather features
            "temp_outdoor", "temp_outdoor_lag_24h",
            "cloudiness", "precipitation_probability",

            # Energy balance
            "pv_surplus", "power_deficit",
            "battery_charge_rate", "battery_utilization",

            # Tariff and PC
            "tariff_zone", "rce_price",
            "heating_season", "pc_co_active", "cwu_window",

            # Interactions
            "temp_hour_interaction", "workday_hour_interaction",
            "heating_temp_interaction", "pc_temp_interaction",
        ]

        # Filter to only features that exist
        existing_features = [
            f for f in important_features if f in self._feature_columns
        ]

        _LOGGER.debug(f"Important features: {len(existing_features)}")
        return existing_features

    def select_features_for_consumption_model(self, df: pd.DataFrame) -> List[str]:
        """
        Select features specifically for consumption prediction model.

        Returns:
            List of feature names for consumption model
        """
        consumption_features = [
            # Calendar (very important for consumption patterns)
            "hour", "day_of_week", "month", "is_weekend", "workday",
            "hour_sin", "hour_cos",

            # Historical consumption
            "grid_power_lag_24h", "grid_power_lag_168h",
            "grid_power_rolling_mean_6h", "grid_power_rolling_mean_24h",

            # Temperature (affects PC/heating)
            "temp_outdoor", "temp_outdoor_lag_24h",
            "heating_season", "pc_co_active", "cwu_window",

            # Tariff (people change behavior based on tariff)
            "tariff_zone",

            # Interactions
            "temp_hour_interaction", "workday_hour_interaction",
            "heating_temp_interaction", "pc_temp_interaction",
        ]

        # Filter to existing columns
        existing = [f for f in consumption_features if f in df.columns]
        _LOGGER.debug(f"Consumption model features: {len(existing)}")
        return existing

    def select_features_for_production_model(self, df: pd.DataFrame) -> List[str]:
        """
        Select features specifically for PV production prediction model.

        Returns:
            List of feature names for production model
        """
        production_features = [
            # Solar features (most important!)
            "solar_elevation", "solar_elevation_norm",
            "solar_azimuth_sin", "solar_azimuth_cos",
            "daylight_hours", "is_daylight",

            # Calendar (season affects production)
            "hour", "month", "day_of_year",
            "hour_sin", "hour_cos", "month_sin", "month_cos",

            # Historical production
            "pv_power_lag_24h", "pv_power_lag_168h",
            "pv_power_rolling_mean_6h", "pv_power_rolling_mean_24h",

            # Weather (clouds, temp)
            "temp_outdoor", "cloudiness", "precipitation_probability",

            # Time of year
            "season", "week_of_year",
        ]

        # Filter to existing columns
        existing = [f for f in production_features if f in df.columns]
        _LOGGER.debug(f"Production model features: {len(existing)}")
        return existing
