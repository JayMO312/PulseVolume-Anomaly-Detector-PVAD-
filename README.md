# PulseVolume Anomaly Detector (PVAD)

PulseVolume Anomaly Detector employs multi-factor momentum detection algorithms to analyze all Coinbase pairs in real-time. By leveraging dynamic volume deltas, volatility compression metrics, and trend initiation signals, PVAD identifies statistically significant anomalies in market liquidity and price action, predicting imminent breakout events.

## Features

- **Real-time Monitoring**: Continuously analyzes all active Coinbase USD trading pairs
- **Volume Delta Detection**: Identifies significant volume spikes using statistical analysis (2σ threshold)
- **Volatility Compression**: Detects periods of low volatility that often precede breakouts
- **Trend Initiation Signals**: Recognizes emerging trends through combined price and volume momentum
- **Smart Alerting**: Generates alerts only for significant anomalies (score-based system)
- **Rate Limiting**: Respects API limits with built-in throttling
- **Colored Output**: Easy-to-read terminal output with color coding

## Installation

### Prerequisites

- Python 3.7 or higher
- pip package manager

### Setup

1. Clone the repository:
```bash
git clone https://github.com/JayMO312/PulseVolume-Anomaly-Detector-PVAD-.git
cd PulseVolume-Anomaly-Detector-PVAD-
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Running the Detector

Simply run the main script:

```bash
python pvad.py
```

The detector will:
1. Fetch all available Coinbase USD trading pairs
2. Begin monitoring each pair at regular intervals (default: 60 seconds)
3. Display alerts when anomalies are detected
4. Continue running until interrupted (Ctrl+C)

### Understanding the Output

When an anomaly is detected, PVAD displays:

```
======================================================================
ANOMALY DETECTED: BTC-USD
======================================================================
Time: 2026-01-13 10:30:45
Price: $45,234.56
24h Volume: 1,234,567.89
Anomaly Score: 5/7

  ⚠ Volume Anomaly: 2.34σ from baseline
  ⚠ Volatility Compression: 0.3421
  ⚠ Trend Initiation: Strength 1.89
```

#### Anomaly Score Breakdown:
- **Volume Anomaly** (+3 points): Volume significantly exceeds baseline
- **Volatility Compression** (+2 points): Price action is unusually tight
- **Trend Initiation** (+2 points): Strong momentum signal detected
- **Threshold**: Alerts trigger at score ≥ 3

## Configuration

Customize detection parameters by editing `config.py`:

### Key Parameters

```python
# Volume Analysis
VOLUME_DELTA_THRESHOLD = 2.0  # Standard deviations for volume anomaly
VOLUME_LOOKBACK_PERIODS = 24  # Historical periods to analyze

# Volatility Detection
VOLATILITY_THRESHOLD = 0.5    # Compression threshold
VOLATILITY_LOOKBACK_PERIODS = 20

# Trend Detection
TREND_STRENGTH_THRESHOLD = 1.5  # Minimum strength for trend signal
PRICE_CHANGE_THRESHOLD = 0.02   # 2% minimum price change

# Update Frequency
UPDATE_INTERVAL = 60  # Seconds between scans
```

## Algorithm Details

### 1. Volume Delta Analysis
- Calculates rolling mean and standard deviation of volume
- Flags volumes exceeding 2σ from baseline
- Uses 24-period lookback by default

### 2. Volatility Compression
- Computes coefficient of variation of price returns
- Identifies compression when volatility < 0.5 threshold
- 20-period rolling window

### 3. Trend Initiation
- Combines price momentum with volume trends
- Weights recent volume against baseline
- Signals when combined strength exceeds 1.5

### 4. Anomaly Scoring
Composite scoring system:
- All three factors present = Score 7 (highest alert)
- Volume + one other = Score 5
- Single factor = Score 2-3
- Alerts triggered at score ≥ 3

## API Rate Limits

PVAD respects Coinbase API rate limits:
- Maximum 3 requests per second
- Built-in throttling and retry logic
- No authentication required for public endpoints

## Troubleshooting

### Common Issues

**"Could not fetch products from Coinbase API"**
- Check your internet connection
- Verify Coinbase API is accessible
- Try increasing `REQUEST_TIMEOUT` in config.py

**No anomalies detected**
- Markets may be stable - this is normal
- Reduce thresholds in config.py for more sensitivity
- Wait for more data accumulation (first 10+ scans)

**Rate limit errors**
- Reduce `MAX_REQUESTS_PER_SECOND` in config.py
- Increase `UPDATE_INTERVAL` between scans

## Requirements

- requests>=2.31.0
- numpy>=1.24.0
- pandas>=2.0.0
- python-dotenv>=1.0.0
- colorama>=0.4.6

## License

MIT License - See LICENSE file for details

## Disclaimer

This tool is for educational and informational purposes only. It is not financial advice. Cryptocurrency trading carries significant risk. Always do your own research and never invest more than you can afford to lose.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues, questions, or suggestions, please open an issue on GitHub.
