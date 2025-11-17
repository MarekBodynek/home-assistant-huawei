"""Data collector for Energy ML integration."""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import asyncio

import pandas as pd
from homeassistant.core import HomeAssistant
from homeassistant.components import recorder
from homeassistant.components.recorder import history

from ..const import (
    SENSORS_TO_COLLECT,
    MAX_DATA_DAYS,
    DATA_STORAGE_PATH,
)

_LOGGER = logging.getLogger(__name__)


class DataCollector:
    """Collect historical data from Home Assistant recorder."""

    def __init__(self, hass: HomeAssistant):
        """Initialize data collector."""
        self.hass = hass
        self._data_cache = None
        self._last_collection = None

    async def collect_current_data(self) -> Dict[str, Any]:
        """
        Collect current sensor states (for real-time predictions).

        Returns:
            Dict with current sensor values and timestamp.
        """
        try:
            data = {
                "timestamp": datetime.now(),
            }

            # Collect all configured sensors
            for sensor_name, entity_id in SENSORS_TO_COLLECT.items():
                state = self.hass.states.get(entity_id)

                if state is None:
                    _LOGGER.warning(f"Sensor {entity_id} not found")
                    data[sensor_name] = None
                    continue

                # Parse state value
                if state.state in ["unknown", "unavailable", None]:
                    data[sensor_name] = None
                elif sensor_name in ["workday", "heating_season", "pc_co_active", "cwu_window"]:
                    # Binary sensors
                    data[sensor_name] = state.state == "on"
                elif sensor_name == "tariff_zone":
                    # String sensor (L1/L2)
                    data[sensor_name] = state.state
                elif sensor_name == "weather_state":
                    # Weather sensor - extract attributes
                    data["cloudiness"] = state.attributes.get("cloudiness", None)
                    data["precipitation_probability"] = state.attributes.get(
                        "precipitation_probability", None
                    )
                    data["weather_condition"] = state.state
                elif sensor_name == "sun_elevation":
                    # Sun sensor - extract elevation and azimuth
                    data["solar_elevation"] = state.attributes.get("elevation", None)
                    data["solar_azimuth"] = state.attributes.get("azimuth", None)
                    data["next_rising"] = state.attributes.get("next_rising", None)
                    data["next_setting"] = state.attributes.get("next_setting", None)
                else:
                    # Numeric sensors
                    try:
                        data[sensor_name] = float(state.state)
                    except (ValueError, TypeError):
                        data[sensor_name] = None

            _LOGGER.debug(f"Collected current data: {len(data)} fields")
            return data

        except Exception as e:
            _LOGGER.error(f"Error collecting current data: {e}")
            return {}

    async def collect_historical_data(
        self, days: int = 30, entity_ids: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Collect historical data from Home Assistant recorder.

        Args:
            days: Number of days of history to collect
            entity_ids: List of entity IDs to collect (default: all from SENSORS_TO_COLLECT)

        Returns:
            pandas DataFrame with historical data indexed by timestamp
        """
        try:
            if entity_ids is None:
                entity_ids = list(SENSORS_TO_COLLECT.values())

            end_time = datetime.now()
            start_time = end_time - timedelta(days=days)

            _LOGGER.info(
                f"Collecting historical data from {start_time} to {end_time} "
                f"({days} days, {len(entity_ids)} sensors)"
            )

            # Get recorder instance
            instance = recorder.get_instance(self.hass)
            if instance is None:
                _LOGGER.error("Recorder instance not available")
                return pd.DataFrame()

            # Wait for recorder to be ready
            await instance.async_recorder_ready()

            # Collect data for each sensor
            all_data = []

            for entity_id in entity_ids:
                try:
                    # Get historical states from recorder
                    # Use run_in_executor to avoid blocking
                    states = await self.hass.async_add_executor_job(
                        self._get_history_states,
                        entity_id,
                        start_time,
                        end_time,
                    )

                    if not states:
                        _LOGGER.warning(f"No historical data for {entity_id}")
                        continue

                    # Convert to DataFrame
                    df = self._states_to_dataframe(states, entity_id)
                    if df is not None and not df.empty:
                        all_data.append(df)
                        _LOGGER.debug(
                            f"Collected {len(df)} records for {entity_id}"
                        )

                except Exception as e:
                    _LOGGER.error(f"Error collecting history for {entity_id}: {e}")
                    continue

            if not all_data:
                _LOGGER.warning("No historical data collected")
                return pd.DataFrame()

            # Merge all DataFrames on timestamp
            _LOGGER.info(f"Merging {len(all_data)} sensor histories")
            result = pd.concat(all_data, axis=1)

            # Remove duplicate columns (if any)
            result = result.loc[:, ~result.columns.duplicated()]

            # Sort by index (timestamp)
            result.sort_index(inplace=True)

            _LOGGER.info(
                f"Historical data collected: {len(result)} rows, "
                f"{len(result.columns)} columns, "
                f"from {result.index.min()} to {result.index.max()}"
            )

            self._data_cache = result
            self._last_collection = datetime.now()

            return result

        except Exception as e:
            _LOGGER.error(f"Error in collect_historical_data: {e}", exc_info=True)
            return pd.DataFrame()

    def _get_history_states(
        self, entity_id: str, start_time: datetime, end_time: datetime
    ) -> List:
        """
        Get historical states from recorder (synchronous).

        This runs in executor to avoid blocking the event loop.
        """
        try:
            # Use history.state_changes_during_period
            states = history.state_changes_during_period(
                self.hass,
                start_time,
                end_time,
                entity_id,
                no_attributes=False,
            )

            if entity_id in states:
                return states[entity_id]

            return []

        except Exception as e:
            _LOGGER.error(f"Error getting history for {entity_id}: {e}")
            return []

    def _states_to_dataframe(
        self, states: List, entity_id: str
    ) -> Optional[pd.DataFrame]:
        """
        Convert list of states to pandas DataFrame.

        Args:
            states: List of state objects from recorder
            entity_id: Entity ID (for column naming)

        Returns:
            DataFrame with timestamp index and value column
        """
        try:
            if not states:
                return None

            # Extract timestamp and value from each state
            data = []
            for state in states:
                try:
                    timestamp = state.last_changed
                    value = state.state

                    # Skip unknown/unavailable states
                    if value in ["unknown", "unavailable", None]:
                        continue

                    # Parse value based on entity type
                    if entity_id.startswith("binary_sensor."):
                        parsed_value = 1 if value == "on" else 0
                    elif entity_id.startswith("sensor."):
                        try:
                            parsed_value = float(value)
                        except (ValueError, TypeError):
                            # String sensor (e.g., tariff_zone)
                            parsed_value = value
                    else:
                        parsed_value = value

                    data.append(
                        {
                            "timestamp": timestamp,
                            "value": parsed_value,
                        }
                    )

                except Exception as e:
                    _LOGGER.debug(f"Error parsing state for {entity_id}: {e}")
                    continue

            if not data:
                return None

            # Create DataFrame
            df = pd.DataFrame(data)
            df.set_index("timestamp", inplace=True)

            # Rename column to entity_id
            sensor_name = self._entity_id_to_sensor_name(entity_id)
            df.rename(columns={"value": sensor_name}, inplace=True)

            return df

        except Exception as e:
            _LOGGER.error(f"Error converting states to DataFrame: {e}")
            return None

    def _entity_id_to_sensor_name(self, entity_id: str) -> str:
        """
        Convert entity_id to sensor name used in SENSORS_TO_COLLECT.

        Args:
            entity_id: e.g., "sensor.akumulatory_stan_pojemnosci"

        Returns:
            sensor name, e.g., "battery_soc"
        """
        for sensor_name, eid in SENSORS_TO_COLLECT.items():
            if eid == entity_id:
                return sensor_name

        # Fallback: use entity_id without domain
        return entity_id.split(".", 1)[1] if "." in entity_id else entity_id

    async def aggregate_to_hourly(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregate data to hourly intervals.

        Args:
            df: DataFrame with any time resolution

        Returns:
            DataFrame resampled to 1-hour intervals
        """
        try:
            if df.empty:
                return df

            _LOGGER.info(f"Aggregating data to hourly intervals ({len(df)} rows)")

            # Resample to 1 hour, using mean for numeric columns
            hourly = df.resample("1H").agg(
                {
                    col: "mean" if df[col].dtype in ["float64", "int64"] else "last"
                    for col in df.columns
                }
            )

            _LOGGER.info(f"Hourly data: {len(hourly)} rows")
            return hourly

        except Exception as e:
            _LOGGER.error(f"Error aggregating to hourly: {e}")
            return df

    async def get_cached_data(self, max_age_minutes: int = 60) -> Optional[pd.DataFrame]:
        """
        Get cached historical data if available and fresh.

        Args:
            max_age_minutes: Maximum age of cache in minutes

        Returns:
            Cached DataFrame or None if cache is stale
        """
        if self._data_cache is None or self._last_collection is None:
            return None

        age = datetime.now() - self._last_collection
        if age > timedelta(minutes=max_age_minutes):
            _LOGGER.debug("Data cache is stale")
            return None

        _LOGGER.debug(f"Using cached data (age: {age.seconds // 60} minutes)")
        return self._data_cache

    async def collect_and_save(self, days: int = 30) -> bool:
        """
        Collect historical data and save to storage.

        Args:
            days: Number of days to collect

        Returns:
            True if successful
        """
        try:
            # Collect historical data
            df = await self.collect_historical_data(days=days)

            if df.empty:
                _LOGGER.warning("No data collected, skipping save")
                return False

            # Aggregate to hourly
            hourly_df = await self.aggregate_to_hourly(df)

            if hourly_df.empty:
                _LOGGER.warning("No hourly data after aggregation")
                return False

            # Save to CSV
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"{DATA_STORAGE_PATH}/historical_data_{timestamp}.csv"

            await self.hass.async_add_executor_job(
                hourly_df.to_csv, filepath
            )

            _LOGGER.info(
                f"Historical data saved to {filepath} "
                f"({len(hourly_df)} rows, {len(hourly_df.columns)} columns)"
            )

            return True

        except Exception as e:
            _LOGGER.error(f"Error in collect_and_save: {e}", exc_info=True)
            return False
