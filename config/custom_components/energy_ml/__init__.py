"""Energy ML - Machine Learning for Battery Management."""
import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    DOMAIN,
    DATA_COLLECTION_INTERVAL,
)
from .data import DataCollector, DataPreprocessor, FeatureEngineer
from .storage import DataStorage

_LOGGER = logging.getLogger(__name__)

PLATFORMS = []  # No sensor platforms yet (will add later)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up Energy ML component from YAML configuration."""
    hass.data.setdefault(DOMAIN, {})

    # Initialize data collection components
    collector = DataCollector(hass)
    preprocessor = DataPreprocessor()
    feature_engineer = FeatureEngineer()
    storage = DataStorage()

    # Store in hass.data
    hass.data[DOMAIN] = {
        "collector": collector,
        "preprocessor": preprocessor,
        "feature_engineer": feature_engineer,
        "storage": storage,
    }

    _LOGGER.info("Energy ML component initialized")

    # Start data collection on Home Assistant start
    async def start_data_collection(event):
        """Start data collection when HA starts."""
        _LOGGER.info("Starting Energy ML data collection")

        # Schedule periodic data collection
        async def collect_data_job(now):
            """Periodic job to collect current data."""
            try:
                _LOGGER.debug("Running periodic data collection")

                # Collect current sensor states
                current_data = await collector.collect_current_data()

                if current_data:
                    _LOGGER.debug(f"Collected {len(current_data)} current data points")
                else:
                    _LOGGER.warning("No current data collected")

            except Exception as e:
                _LOGGER.error(f"Error in periodic data collection: {e}", exc_info=True)

        # Register periodic job (runs every hour)
        async_track_time_interval(
            hass,
            collect_data_job,
            DATA_COLLECTION_INTERVAL,
        )

        _LOGGER.info(
            f"Scheduled data collection every {DATA_COLLECTION_INTERVAL.total_seconds() / 3600:.0f} hours"
        )

        # Run initial data collection
        await collect_data_job(None)

    # Listen for Home Assistant start event
    hass.bus.async_listen_once("homeassistant_start", start_data_collection)

    # Register services
    async def handle_collect_historical_data(call):
        """Handle collect_historical_data service call."""
        days = call.data.get("days", 30)
        _LOGGER.info(f"Service called: collect_historical_data (days={days})")

        try:
            # Collect historical data
            df = await collector.collect_historical_data(days=days)

            if df.empty:
                _LOGGER.error("No data collected")
                return

            # Aggregate to hourly
            hourly_df = await collector.aggregate_to_hourly(df)

            # Save to storage
            filepath = storage.save_collected_data(hourly_df, data_type="historical")
            _LOGGER.info(f"Historical data saved: {filepath}")

        except Exception as e:
            _LOGGER.error(f"Error in collect_historical_data service: {e}", exc_info=True)

    async def handle_collect_and_process(call):
        """Handle collect_and_process service call."""
        days = call.data.get("days", 30)
        _LOGGER.info(f"Service called: collect_and_process (days={days})")

        try:
            # 1. Collect historical data
            _LOGGER.info("Step 1/4: Collecting historical data...")
            df = await collector.collect_historical_data(days=days)

            if df.empty:
                _LOGGER.error("No data collected")
                return

            # 2. Aggregate to hourly
            _LOGGER.info("Step 2/4: Aggregating to hourly intervals...")
            hourly_df = await collector.aggregate_to_hourly(df)

            # 3. Clean and preprocess
            _LOGGER.info("Step 3/4: Cleaning and preprocessing...")
            clean_df, stats = preprocessor.clean_data(hourly_df)
            _LOGGER.info(f"Preprocessing stats: {stats}")

            # 4. Feature engineering
            _LOGGER.info("Step 4/4: Engineering features...")
            features_df = feature_engineer.create_features(clean_df)

            # Save processed data
            filepath = storage.save_features(features_df)
            _LOGGER.info(f"Features saved: {filepath}")

            # Log summary
            _LOGGER.info(
                f"Data collection complete: {len(features_df)} rows, "
                f"{len(features_df.columns)} features, "
                f"quality: {stats.get('data_quality', 0):.1%}"
            )

        except Exception as e:
            _LOGGER.error(f"Error in collect_and_process service: {e}", exc_info=True)

    async def handle_get_storage_stats(call):
        """Handle get_storage_stats service call."""
        _LOGGER.info("Service called: get_storage_stats")

        try:
            stats = storage.get_storage_stats()
            _LOGGER.info(f"Storage stats: {stats}")

            # Create persistent notification with stats
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "Energy ML Storage Statistics",
                    "message": (
                        f"Data files: {stats.get('data_files', 0)}\n"
                        f"Model files: {stats.get('model_files', 0)}\n"
                        f"Log files: {stats.get('log_files', 0)}\n"
                        f"Total size: {stats.get('total_size_mb', 0):.2f} MB"
                    ),
                    "notification_id": "energy_ml_storage_stats",
                },
            )

        except Exception as e:
            _LOGGER.error(f"Error in get_storage_stats service: {e}", exc_info=True)

    # Register services
    hass.services.async_register(
        DOMAIN, "collect_historical_data", handle_collect_historical_data
    )
    hass.services.async_register(
        DOMAIN, "collect_and_process", handle_collect_and_process
    )
    hass.services.async_register(
        DOMAIN, "get_storage_stats", handle_get_storage_stats
    )

    _LOGGER.info("Energy ML services registered")

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Energy ML from a config entry."""
    # Not using config flow yet
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
    return True
