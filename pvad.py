#!/usr/bin/env python3
"""
PulseVolume Anomaly Detector (PVAD)

Analyzes Coinbase trading pairs in real-time using:
- Dynamic volume delta detection
- Volatility compression metrics
- Trend initiation signals

Identifies statistically significant anomalies in market liquidity and price action.
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

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    COLOR_SUPPORT = True
except ImportError:
    COLOR_SUPPORT = False
    
import config


class CoinbaseAPI:
    """Handles communication with Coinbase Exchange API"""
    
    def __init__(self):
        self.base_url = config.COINBASE_API_BASE
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PulseVolume-Anomaly-Detector/1.0'
        })
        self.last_request_time = 0
        
    def _rate_limit(self):
        """Enforce rate limiting"""
        min_interval = 1.0 / config.MAX_REQUESTS_PER_SECOND
        elapsed = time.time() - self.last_request_time
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self.last_request_time = time.time()
        
    def get_products(self) -> List[Dict]:
        """Fetch all available trading pairs"""
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
    
    def __init__(self):
        self.api = CoinbaseAPI()
        self.volume_analyzer = VolumeAnalyzer()
        self.volatility_analyzer = VolatilityAnalyzer()
        self.trend_analyzer = TrendAnalyzer()
        self.alerts = []
        self.last_alert_time = defaultdict(float)
        
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
        print("PulseVolume Anomaly Detector (PVAD) - Starting...")
        print("=" * 70)
        print()
        
        # Fetch products
        print("Fetching available trading pairs from Coinbase...")
        products = self.api.get_products()
        
        if not products:
            print("Error: Could not fetch products from Coinbase API")
            return
        
        product_ids = [p['id'] for p in products]
        print(f"Monitoring {len(product_ids)} trading pairs")
        print()
        
        iteration = 0
        
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
                
                print(f"\nWaiting {config.UPDATE_INTERVAL} seconds until next scan...")
                time.sleep(config.UPDATE_INTERVAL)
                
        except KeyboardInterrupt:
            print("\n\nShutting down PVAD...")
            print(f"Total alerts generated: {len(self.alerts)}")
            print("Thank you for using PulseVolume Anomaly Detector!")


def main():
    """Entry point"""
    print()
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║   PulseVolume Anomaly Detector (PVAD)                             ║")
    print("║   Real-time Cryptocurrency Momentum Detection                     ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print()
    
    detector = AnomalyDetector()
    
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
