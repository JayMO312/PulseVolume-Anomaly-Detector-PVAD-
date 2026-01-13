"""
Configuration settings for PulseVolume Anomaly Detector
"""

# API Configuration
COINBASE_API_BASE = "https://api.exchange.coinbase.com"
REQUEST_TIMEOUT = 10  # seconds
UPDATE_INTERVAL = 60  # seconds between updates

# Volume Analysis Parameters
VOLUME_DELTA_THRESHOLD = 2.0  # Standard deviations for significant volume change
VOLUME_LOOKBACK_PERIODS = 24  # Number of periods to analyze for volume baseline

# Volatility Compression Parameters
VOLATILITY_THRESHOLD = 0.002  # Threshold for detecting compression (std dev of returns)
VOLATILITY_LOOKBACK_PERIODS = 20  # Number of periods for volatility calculation

# Trend Detection Parameters
TREND_STRENGTH_THRESHOLD = 0.015  # Minimum strength to signal trend initiation
PRICE_CHANGE_THRESHOLD = 0.02  # 2% price change threshold

# Statistical Parameters
CONFIDENCE_LEVEL = 0.95  # Confidence level for statistical tests
MIN_DATA_POINTS = 10  # Minimum data points required for analysis

# Display Settings
MAX_ALERTS_DISPLAY = 10  # Maximum number of alerts to display
ENABLE_COLOR_OUTPUT = True  # Enable colored terminal output

# Rate Limiting
MAX_REQUESTS_PER_SECOND = 3
