# Quick Start Guide

## Installation

```bash
# Clone the repository
git clone https://github.com/JayMO312/PulseVolume-Anomaly-Detector-PVAD-.git
cd PulseVolume-Anomaly-Detector-PVAD-

# Install dependencies
pip install -r requirements.txt
```

## Running the Script

### Demo Mode (Recommended for First Time)
Test without internet connection using simulated data:
```bash
python pvad.py --demo
```

### Live Mode
Connect to Coinbase API for real-time analysis:
```bash
python pvad.py
```

## Understanding Alerts

When PVAD detects an anomaly, you'll see:

```
======================================================================
ANOMALY DETECTED: BTC-USD
======================================================================
Time: 2026-01-13 10:30:45
Price: $45,234.56
24h Volume: 1,234,567.89
Anomaly Score: 5/7

  ⚠ Volume Anomaly: 2.34σ from baseline
  ⚠ Volatility Compression: 0.0016
  ⚠ Trend Initiation: Strength 0.0267
```

### What Each Signal Means:

- **Volume Anomaly**: Trading volume is significantly higher than normal (2+ standard deviations)
- **Volatility Compression**: Price is moving in a tight range (often precedes breakouts)
- **Trend Initiation**: Strong momentum detected with increasing volume

### Anomaly Score:
- **7/7**: All three signals present (strongest alert)
- **5/7**: Volume spike with one other signal
- **3/7**: Minimum for alert (single strong signal)

## Customization

Edit `config.py` to adjust sensitivity:

```python
# Make more sensitive (more alerts)
VOLUME_DELTA_THRESHOLD = 1.5  # Lower from 2.0
VOLATILITY_THRESHOLD = 0.003  # Raise from 0.002
TREND_STRENGTH_THRESHOLD = 0.010  # Lower from 0.015

# Make less sensitive (fewer alerts)
VOLUME_DELTA_THRESHOLD = 2.5  # Raise from 2.0
VOLATILITY_THRESHOLD = 0.001  # Lower from 0.002
TREND_STRENGTH_THRESHOLD = 0.020  # Raise from 0.015
```

## Testing

Run the test suite to verify everything works:
```bash
python test_pvad.py
```

## Troubleshooting

### "Could not fetch products from Coinbase API"
- Check internet connection
- Try demo mode: `python pvad.py --demo`
- Increase timeout in config.py

### No anomalies detected for a long time
- This is normal during stable markets
- Reduce thresholds in config.py for more sensitivity
- Wait for at least 10+ scans to build baseline data

### Script crashes or errors
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check Python version is 3.7+: `python --version`
- Try demo mode to isolate API issues

## What Makes This Script Consistent

Unlike fragile scripts, PVAD includes:

1. **Error Recovery**: Handles API failures gracefully
2. **Rate Limiting**: Prevents hitting API limits
3. **Smart Throttling**: Prevents alert spam (max 1 per product per 5 min)
4. **Baseline Building**: Requires 10+ data points before alerting
5. **Demo Mode**: Test without external dependencies

## Next Steps

1. Run in demo mode to understand the output
2. Test with live data when ready
3. Adjust thresholds in config.py based on your needs
4. Monitor for a few hours to see how it performs

Happy trading! 📈🚀
