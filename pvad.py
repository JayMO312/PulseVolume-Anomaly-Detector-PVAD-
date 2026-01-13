#!/usr/bin/env python3
"""
PulseVolume Anomaly Detector (PVAD)

Analyzes Coinbase trading pairs in real-time using:
- Dynamic volume delta detection
- Volatility compression metrics
- Trend initiation signals

Identifies statistically significant anomalies in market liquidity and price action.

Usage:
    python pvad.py           # Run with live Coinbase data
    python pvad.py --demo    # Run demo mode with simulated data
"""

import sys
import time
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import json
from collections import defaultdict, deque
import random
import argparse

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    COLOR_SUPPORT = True
except ImportError:
    COLOR_SUPPORT = False
    
import config


class CoinbaseAPI:
    """Handles communication with Coinbase Exchange API"""
    
    def __init__(self, demo_mode=False):
        self.base_url = config.COINBASE_API_BASE
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PulseVolume-Anomaly-Detector/1.0'
        })
        self.last_request_time = 0
        self.demo_mode = demo_mode
        self.demo_products = [
            'BTC-USD', 'ETH-USD', 'SOL-USD', 'ADA-USD', 
            'DOGE-USD', 'XRP-USD', 'LINK-USD', 'MATIC-USD'
        ]
        self.demo_state = {}
        self._init_demo_state()
    
    def _init_demo_state(self):
        """Initialize demo state for each product"""
        if not self.demo_mode:
            return
        base_prices = {
            'BTC-USD': 45000, 'ETH-USD': 2500, 'SOL-USD': 100,
            'ADA-USD': 0.50, 'DOGE-USD': 0.08, 'XRP-USD': 0.60,
            'LINK-USD': 15, 'MATIC-USD': 0.80
        }
        for product in self.demo_products:
            self.demo_state[product] = {
                'price': base_prices.get(product, 100),
                'volume': random.uniform(800, 1200),
                'trend': random.choice(['normal', 'building', 'breaking']),
                'phase': 0
            }
    
    def _update_demo_data(self, product_id: str):
        """Update demo data to simulate market behavior"""
        state = self.demo_state[product_id]
        
        # Randomly change trend
        if random.random() < 0.05:  # 5% chance to change trend
            state['trend'] = random.choice(['normal', 'building', 'breaking'])
            state['phase'] = 0
        
        state['phase'] += 1
        
        if state['trend'] == 'normal':
            # Normal market conditions
            state['price'] *= (1 + random.uniform(-0.005, 0.005))
            state['volume'] = 1000 + random.uniform(-100, 100)
            
        elif state['trend'] == 'building':
            # Building compression before breakout
            state['price'] *= (1 + random.uniform(-0.001, 0.001))  # Low volatility
            state['volume'] = 1000 + random.uniform(-50, 50)
            
        elif state['trend'] == 'breaking':
            # Breakout happening
            direction = 1 if state['phase'] % 10 < 5 else -1
            state['price'] *= (1 + direction * random.uniform(0.01, 0.03))  # Strong move
            state['volume'] = 1000 + random.uniform(1500, 3000)  # Volume spike
        
    def _rate_limit(self):
        """Enforce rate limiting"""
        min_interval = 1.0 / config.MAX_REQUESTS_PER_SECOND
        elapsed = time.time() - self.last_request_time
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self.last_request_time = time.time()
        
    def get_products(self) -> List[Dict]:
        """Fetch all available trading pairs"""
        if self.demo_mode:
            return [{'id': pid, 'status': 'online', 'quote_currency': 'USD'} 
                    for pid in self.demo_products]
        
        try:
            self._rate_limit()
            response = self.session.get(
                f"{self.base_url}/products",
                timeout=config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            products = response.json()
            # Filter for active products
            return [p for p in products if p.get('status') == 'online' and p.get('quote_currency') == 'USD']
        except Exception as e:
            print(f"Error fetching products: {e}")
            return []
    
    def get_ticker(self, product_id: str) -> Optional[Dict]:
        """Fetch current ticker data for a product"""
        if self.demo_mode:
            self._update_demo_data(product_id)
            state = self.demo_state[product_id]
            return {
                'price': str(state['price']),
                'volume': str(state['volume'])
            }
        
        try:
            self._rate_limit()
            response = self.session.get(
                f"{self.base_url}/products/{product_id}/ticker",
                timeout=config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching ticker for {product_id}: {e}")
            return None
    
    def get_stats(self, product_id: str) -> Optional[Dict]:
        """Fetch 24hr stats for a product"""
        if self.demo_mode:
            state = self.demo_state[product_id]
            return {
                'volume': str(state['volume']),
                'open': str(state['price'] * 0.98),
                'high': str(state['price'] * 1.02),
                'low': str(state['price'] * 0.98)
            }
        
        try:
            self._rate_limit()
            response = self.session.get(
                f"{self.base_url}/products/{product_id}/stats",
                timeout=config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching stats for {product_id}: {e}")
            return None


class VolumeAnalyzer:
    """Analyzes volume deltas and detects anomalies"""
    
    def __init__(self):
        self.volume_history = defaultdict(lambda: deque(maxlen=config.VOLUME_LOOKBACK_PERIODS))
    
    def update(self, product_id: str, volume: float):
        """Update volume history"""
        self.volume_history[product_id].append(volume)
    
    def calculate_volume_delta(self, product_id: str, current_volume: float) -> Optional[float]:
        """Calculate volume delta in standard deviations"""
        history = self.volume_history[product_id]
        
        if len(history) < config.MIN_DATA_POINTS:
            return None
        
        volumes = np.array(list(history))
        mean_volume = np.mean(volumes)
        std_volume = np.std(volumes)
        
        if std_volume == 0:
            return 0.0
        
        delta = (current_volume - mean_volume) / std_volume
        return delta
    
    def is_volume_anomaly(self, delta: Optional[float]) -> bool:
        """Check if volume delta indicates an anomaly"""
        if delta is None:
            return False
        return abs(delta) >= config.VOLUME_DELTA_THRESHOLD


class VolatilityAnalyzer:
    """Analyzes price volatility and compression"""
    
    def __init__(self):
        self.price_history = defaultdict(lambda: deque(maxlen=config.VOLATILITY_LOOKBACK_PERIODS))
    
    def update(self, product_id: str, price: float):
        """Update price history"""
        self.price_history[product_id].append(price)
    
    def calculate_volatility(self, product_id: str) -> Optional[float]:
        """Calculate price volatility (standard deviation of returns)"""
        history = self.price_history[product_id]
        
        if len(history) < config.MIN_DATA_POINTS:
            return None
        
        prices = np.array(list(history))
        returns = np.diff(prices) / prices[:-1]
        
        if len(returns) < 2:
            return None
        
        # Use standard deviation of returns as volatility metric
        volatility = np.std(returns)
        return volatility
    
    def is_compressed(self, volatility: Optional[float]) -> bool:
        """Check if volatility indicates compression"""
        if volatility is None:
            return False
        return volatility < config.VOLATILITY_THRESHOLD


class TrendAnalyzer:
    """Analyzes trend initiation signals"""
    
    def __init__(self):
        self.price_history = defaultdict(lambda: deque(maxlen=20))
        self.volume_history = defaultdict(lambda: deque(maxlen=20))
    
    def update(self, product_id: str, price: float, volume: float):
        """Update history"""
        self.price_history[product_id].append(price)
        self.volume_history[product_id].append(volume)
    
    def calculate_trend_strength(self, product_id: str) -> Optional[float]:
        """Calculate trend strength score"""
        price_hist = self.price_history[product_id]
        volume_hist = self.volume_history[product_id]
        
        if len(price_hist) < config.MIN_DATA_POINTS:
            return None
        
        prices = np.array(list(price_hist))
        volumes = np.array(list(volume_hist))
        
        # Calculate price momentum
        price_change = (prices[-1] - prices[0]) / prices[0]
        
        # Calculate volume trend
        recent_vol = np.mean(volumes[-5:]) if len(volumes) >= 5 else np.mean(volumes)
        baseline_vol = np.mean(volumes)
        vol_increase = (recent_vol - baseline_vol) / (baseline_vol + 1e-10)
        
        # Combine signals
        trend_strength = abs(price_change) * (1 + vol_increase)
        
        return trend_strength
    
    def is_trend_initiating(self, strength: Optional[float]) -> bool:
        """Check if trend is initiating"""
        if strength is None:
            return False
        return strength >= config.TREND_STRENGTH_THRESHOLD


class AnomalyDetector:
    """Main anomaly detection system"""
    
    def __init__(self, demo_mode=False):
        self.api = CoinbaseAPI(demo_mode=demo_mode)
        self.volume_analyzer = VolumeAnalyzer()
        self.volatility_analyzer = VolatilityAnalyzer()
        self.trend_analyzer = TrendAnalyzer()
        self.alerts = []
        self.last_alert_time = defaultdict(float)
        self.demo_mode = demo_mode
        
    def analyze_product(self, product_id: str) -> Optional[Dict]:
        """Analyze a single product for anomalies"""
        # Fetch data
        ticker = self.api.get_ticker(product_id)
        stats = self.api.get_stats(product_id)
        
        if not ticker or not stats:
            return None
        
        try:
            price = float(ticker.get('price', 0))
            volume = float(stats.get('volume', 0))
            
            if price == 0 or volume == 0:
                return None
            
            # Update analyzers
            self.volume_analyzer.update(product_id, volume)
            self.volatility_analyzer.update(product_id, price)
            self.trend_analyzer.update(product_id, price, volume)
            
            # Calculate metrics
            volume_delta = self.volume_analyzer.calculate_volume_delta(product_id, volume)
            volatility = self.volatility_analyzer.calculate_volatility(product_id)
            trend_strength = self.trend_analyzer.calculate_trend_strength(product_id)
            
            # Check for anomalies
            has_volume_anomaly = self.volume_analyzer.is_volume_anomaly(volume_delta)
            has_compression = self.volatility_analyzer.is_compressed(volatility)
            has_trend = self.trend_analyzer.is_trend_initiating(trend_strength)
            
            # Calculate anomaly score
            anomaly_score = 0
            if has_volume_anomaly:
                anomaly_score += 3
            if has_compression:
                anomaly_score += 2
            if has_trend:
                anomaly_score += 2
            
            result = {
                'product_id': product_id,
                'price': price,
                'volume': volume,
                'volume_delta': volume_delta,
                'volatility': volatility,
                'trend_strength': trend_strength,
                'anomaly_score': anomaly_score,
                'has_volume_anomaly': has_volume_anomaly,
                'has_compression': has_compression,
                'has_trend': has_trend,
                'timestamp': datetime.now()
            }
            
            return result
            
        except (ValueError, KeyError, TypeError) as e:
            print(f"Error analyzing {product_id}: {e}")
            return None
    
    def generate_alert(self, analysis: Dict):
        """Generate alert if anomaly is significant"""
        if analysis['anomaly_score'] >= 3:
            product_id = analysis['product_id']
            
            # Throttle alerts (max 1 per product per 5 minutes)
            if time.time() - self.last_alert_time[product_id] < 300:
                return
            
            self.last_alert_time[product_id] = time.time()
            self.alerts.append(analysis)
            
            # Keep only recent alerts
            if len(self.alerts) > config.MAX_ALERTS_DISPLAY * 2:
                self.alerts = self.alerts[-config.MAX_ALERTS_DISPLAY * 2:]
    
    def display_alert(self, analysis: Dict):
        """Display an alert with formatting"""
        if COLOR_SUPPORT and config.ENABLE_COLOR_OUTPUT:
            color = Fore.RED if analysis['anomaly_score'] >= 5 else Fore.YELLOW
            print(f"\n{color}{'=' * 70}")
            print(f"{Style.BRIGHT}ANOMALY DETECTED: {analysis['product_id']}")
            print(f"{'=' * 70}{Style.RESET_ALL}")
        else:
            print(f"\n{'=' * 70}")
            print(f"ANOMALY DETECTED: {analysis['product_id']}")
            print(f"{'=' * 70}")
        
        print(f"Time: {analysis['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Price: ${analysis['price']:.2f}")
        print(f"24h Volume: {analysis['volume']:.2f}")
        print(f"Anomaly Score: {analysis['anomaly_score']}/7")
        print()
        
        if analysis['has_volume_anomaly']:
            delta = analysis['volume_delta']
            print(f"  ⚠ Volume Anomaly: {delta:.2f}σ from baseline")
        
        if analysis['has_compression']:
            vol = analysis['volatility']
            print(f"  ⚠ Volatility Compression: {vol:.4f}")
        
        if analysis['has_trend']:
            strength = analysis['trend_strength']
            print(f"  ⚠ Trend Initiation: Strength {strength:.4f}")
        
        print()
    
    def run(self):
        """Main detection loop"""
        print("=" * 70)
        if self.demo_mode:
            print("PulseVolume Anomaly Detector (PVAD) - DEMO MODE")
        else:
            print("PulseVolume Anomaly Detector (PVAD) - Starting...")
        print("=" * 70)
        print()
        
        # Fetch products
        if self.demo_mode:
            print("Using simulated market data for demonstration...")
        else:
            print("Fetching available trading pairs from Coinbase...")
        products = self.api.get_products()
        
        if not products:
            print("Error: Could not fetch products from Coinbase API")
            return
        
        product_ids = [p['id'] for p in products]
        print(f"Monitoring {len(product_ids)} trading pairs")
        if self.demo_mode:
            print("(Demo mode will scan every 10 seconds)")
        print()
        
        iteration = 0
        update_interval = 10 if self.demo_mode else config.UPDATE_INTERVAL
        
        try:
            while True:
                iteration += 1
                print(f"\n[Scan {iteration}] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print("-" * 70)
                
                anomalies_found = 0
                
                for product_id in product_ids:
                    try:
                        analysis = self.analyze_product(product_id)
                        
                        if analysis and analysis['anomaly_score'] >= 3:
                            anomalies_found += 1
                            self.generate_alert(analysis)
                            self.display_alert(analysis)
                    
                    except Exception as e:
                        print(f"Error processing {product_id}: {e}")
                        continue
                
                if anomalies_found == 0:
                    print("No significant anomalies detected in this scan.")
                else:
                    print(f"\nFound {anomalies_found} anomalies in this scan.")
                
                print(f"\nWaiting {update_interval} seconds until next scan...")
                time.sleep(update_interval)
                
        except KeyboardInterrupt:
            print("\n\nShutting down PVAD...")
            print(f"Total alerts generated: {len(self.alerts)}")
            print("Thank you for using PulseVolume Anomaly Detector!")


def main():
    """Entry point"""
    parser = argparse.ArgumentParser(
        description='PulseVolume Anomaly Detector - Real-time Cryptocurrency Momentum Detection'
    )
    parser.add_argument(
        '--demo',
        action='store_true',
        help='Run in demo mode with simulated data (no internet required)'
    )
    args = parser.parse_args()
    
    print()
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║   PulseVolume Anomaly Detector (PVAD)                             ║")
    print("║   Real-time Cryptocurrency Momentum Detection                     ║")
    if args.demo:
        print("║   DEMO MODE - Using Simulated Data                                ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print()
    
    detector = AnomalyDetector(demo_mode=args.demo)
    
    try:
        detector.run()
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
