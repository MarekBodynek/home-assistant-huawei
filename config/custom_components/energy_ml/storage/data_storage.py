"""Data storage and persistence for Energy ML."""
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
import joblib

from ..const import (
    DATA_STORAGE_PATH,
    MODEL_STORAGE_PATH,
    LOG_STORAGE_PATH,
)

_LOGGER = logging.getLogger(__name__)


class DataStorage:
    """Handle data persistence (CSV, pickle, models)."""

    def __init__(self):
        """Initialize data storage."""
        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure storage directories exist."""
        for path in [DATA_STORAGE_PATH, MODEL_STORAGE_PATH, LOG_STORAGE_PATH]:
            Path(path).mkdir(parents=True, exist_ok=True)
            _LOGGER.debug(f"Storage directory ready: {path}")

    def save_collected_data(
        self, df: pd.DataFrame, data_type: str = "historical"
    ) -> str:
        """
        Save collected data to CSV.

        Args:
            df: DataFrame to save
            data_type: Type of data ("historical", "features", etc.)

        Returns:
            Path to saved file
        """
        try:
            if df.empty:
                _LOGGER.warning("Empty DataFrame, skipping save")
                return ""

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{data_type}_data_{timestamp}.csv"
            filepath = os.path.join(DATA_STORAGE_PATH, filename)

            df.to_csv(filepath)
            _LOGGER.info(
                f"Saved {data_type} data to {filepath} "
                f"({len(df)} rows, {len(df.columns)} columns)"
            )

            return filepath

        except Exception as e:
            _LOGGER.error(f"Error saving data to CSV: {e}", exc_info=True)
            return ""

    def load_latest_data(self, data_type: str = "historical") -> Optional[pd.DataFrame]:
        """
        Load most recent data file.

        Args:
            data_type: Type of data to load

        Returns:
            DataFrame or None if not found
        """
        try:
            # Find all matching files
            pattern = f"{data_type}_data_*.csv"
            files = list(Path(DATA_STORAGE_PATH).glob(pattern))

            if not files:
                _LOGGER.info(f"No {data_type} data files found")
                return None

            # Get most recent file
            latest_file = max(files, key=os.path.getctime)
            _LOGGER.info(f"Loading data from {latest_file}")

            df = pd.read_csv(latest_file, index_col=0, parse_dates=True)
            _LOGGER.info(f"Loaded {len(df)} rows, {len(df.columns)} columns")

            return df

        except Exception as e:
            _LOGGER.error(f"Error loading data from CSV: {e}", exc_info=True)
            return None

    def save_features(self, df: pd.DataFrame) -> str:
        """
        Save engineered features to CSV.

        Args:
            df: DataFrame with features

        Returns:
            Path to saved file
        """
        return self.save_collected_data(df, data_type="features")

    def load_latest_features(self) -> Optional[pd.DataFrame]:
        """
        Load most recent feature data.

        Returns:
            DataFrame with features or None
        """
        return self.load_latest_data(data_type="features")

    def save_model(self, model, model_name: str, metadata: Optional[Dict] = None) -> str:
        """
        Save trained model to disk using joblib.

        Args:
            model: Trained scikit-learn model
            model_name: Name for the model file
            metadata: Optional dict with model metadata (metrics, version, etc.)

        Returns:
            Path to saved model file
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{model_name}_{timestamp}.pkl"
            filepath = os.path.join(MODEL_STORAGE_PATH, filename)

            # Save model and metadata together
            save_data = {
                "model": model,
                "metadata": metadata or {},
                "timestamp": timestamp,
            }

            joblib.dump(save_data, filepath, compress=3)
            _LOGGER.info(f"Saved model to {filepath}")

            # Also save latest version (symlink or copy)
            latest_filepath = os.path.join(MODEL_STORAGE_PATH, f"{model_name}_latest.pkl")
            joblib.dump(save_data, latest_filepath, compress=3)
            _LOGGER.info(f"Saved latest model to {latest_filepath}")

            return filepath

        except Exception as e:
            _LOGGER.error(f"Error saving model: {e}", exc_info=True)
            return ""

    def load_model(self, model_name: str, use_latest: bool = True) -> Optional[Dict]:
        """
        Load trained model from disk.

        Args:
            model_name: Name of the model file (without timestamp)
            use_latest: If True, load _latest.pkl version

        Returns:
            Dict with model and metadata, or None if not found
        """
        try:
            if use_latest:
                filepath = os.path.join(MODEL_STORAGE_PATH, f"{model_name}_latest.pkl")
            else:
                # Find most recent timestamped file
                pattern = f"{model_name}_*.pkl"
                files = list(Path(MODEL_STORAGE_PATH).glob(pattern))
                if not files:
                    _LOGGER.info(f"No model files found for {model_name}")
                    return None
                filepath = max(files, key=os.path.getctime)

            if not os.path.exists(filepath):
                _LOGGER.info(f"Model file not found: {filepath}")
                return None

            _LOGGER.info(f"Loading model from {filepath}")
            model_data = joblib.load(filepath)

            return model_data

        except Exception as e:
            _LOGGER.error(f"Error loading model: {e}", exc_info=True)
            return None

    def save_training_log(self, log_data: Dict, log_name: str = "training") -> str:
        """
        Save training log (metrics, config, etc.) to JSON.

        Args:
            log_data: Dict with log data
            log_name: Name for the log file

        Returns:
            Path to saved log file
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{log_name}_{timestamp}.log"
            filepath = os.path.join(LOG_STORAGE_PATH, filename)

            # Write as text log
            with open(filepath, "w") as f:
                f.write(f"=== Training Log ({timestamp}) ===\n\n")
                for key, value in log_data.items():
                    f.write(f"{key}: {value}\n")

            _LOGGER.info(f"Saved training log to {filepath}")
            return filepath

        except Exception as e:
            _LOGGER.error(f"Error saving training log: {e}")
            return ""

    def cleanup_old_files(self, days_to_keep: int = 30):
        """
        Clean up old data files (keep only last N days).

        Args:
            days_to_keep: Number of days of files to keep
        """
        try:
            cutoff_time = datetime.now().timestamp() - (days_to_keep * 86400)

            for storage_path in [DATA_STORAGE_PATH, LOG_STORAGE_PATH]:
                files = Path(storage_path).glob("*")

                for file in files:
                    if file.name.endswith("_latest.pkl"):
                        continue  # Never delete latest models

                    if os.path.getctime(file) < cutoff_time:
                        os.remove(file)
                        _LOGGER.debug(f"Deleted old file: {file}")

            _LOGGER.info(f"Cleanup complete (kept files from last {days_to_keep} days)")

        except Exception as e:
            _LOGGER.error(f"Error during cleanup: {e}")

    def get_storage_stats(self) -> Dict[str, any]:
        """
        Get statistics about stored data.

        Returns:
            Dict with storage statistics
        """
        try:
            stats = {
                "data_files": len(list(Path(DATA_STORAGE_PATH).glob("*.csv"))),
                "model_files": len(list(Path(MODEL_STORAGE_PATH).glob("*.pkl"))),
                "log_files": len(list(Path(LOG_STORAGE_PATH).glob("*.log"))),
            }

            # Calculate total size
            total_size = 0
            for storage_path in [DATA_STORAGE_PATH, MODEL_STORAGE_PATH, LOG_STORAGE_PATH]:
                for file in Path(storage_path).glob("*"):
                    total_size += os.path.getsize(file)

            stats["total_size_mb"] = total_size / (1024 * 1024)

            return stats

        except Exception as e:
            _LOGGER.error(f"Error getting storage stats: {e}")
            return {}
