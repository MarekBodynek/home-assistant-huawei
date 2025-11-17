"""Constants for the Energy ML integration."""
from datetime import timedelta

DOMAIN = "energy_ml"

# Data collection settings
DATA_COLLECTION_INTERVAL = timedelta(hours=1)
MIN_DATA_DAYS = 7  # Minimum days of data needed for training
MAX_DATA_DAYS = 30  # Maximum days to keep in history

# Sensors to collect from Home Assistant
SENSORS_TO_COLLECT = {
    # Energy sensors
    "battery_soc": "sensor.akumulatory_stan_pojemnosci",
    "pv_power": "sensor.inwerter_moc_wejsciowa",
    "grid_power": "sensor.pomiar_mocy_moc_czynna",
    "daily_pv_production": "sensor.inwerter_dzienna_produkcja",
    "battery_power": "sensor.akumulatory_moc_ladowania_rozladowania",

    # Weather sensors
    "temp_outdoor": "sensor.temperatura_zewnetrzna",
    "weather_state": "weather.forecast_dom",

    # Tariff sensors
    "tariff_zone": "sensor.strefa_taryfowa",
    "rce_price": "sensor.pstryk_current_sell_price",
    "workday": "binary_sensor.dzien_roboczy",

    # PC/CWU sensors
    "heating_season": "binary_sensor.sezon_grzewczy",
    "pc_co_active": "binary_sensor.pc_co_aktywne",
    "cwu_window": "binary_sensor.okno_cwu",

    # Sun sensors (built-in)
    "sun_elevation": "sun.sun",
}

# Feature engineering settings
FEATURE_LAG_HOURS = [1, 24, 168]  # 1h, 24h (1d), 168h (7d)
FEATURE_ROLLING_WINDOWS = [3, 6, 24]  # 3h, 6h, 24h

# Model settings
MODEL_CONFIDENCE_THRESHOLD = 0.7  # Minimum confidence to use ML predictions
MODEL_RETRAIN_HOUR = 1  # Hour of day for daily retraining (01:00)
MODEL_WEEKLY_RETRAIN_DAY = 6  # Day of week for full retrain (Sunday = 6)

# Storage paths
DATA_STORAGE_PATH = "/config/ml_data/collected"
MODEL_STORAGE_PATH = "/config/ml_data/models"
LOG_STORAGE_PATH = "/config/ml_data/logs"

# Data quality settings
MAX_MISSING_DATA_PERCENT = 0.20  # Maximum 20% missing data
OUTLIER_STD_THRESHOLD = 3  # Remove outliers > 3 standard deviations

# Prediction horizons (hours)
PREDICTION_HORIZONS = [1, 6, 24]
