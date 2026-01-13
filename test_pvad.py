#!/usr/bin/env python3
"""
Test script for PVAD - Simulates market data to verify detection logic
"""

import time
import random
from datetime import datetime
import numpy as np

# Import from main script
from pvad import VolumeAnalyzer, VolatilityAnalyzer, TrendAnalyzer


def simulate_normal_market():
    """Simulate normal market conditions"""
    return {
        'price': 50000 + random.uniform(-100, 100),
        'volume': 1000 + random.uniform(-50, 50)
    }


def simulate_volume_spike():
    """Simulate volume anomaly"""
    return {
        'price': 50000 + random.uniform(-100, 100),
        'volume': 1000 + random.uniform(2000, 3000)  # Much higher volume
    }


def simulate_compression():
    """Simulate volatility compression"""
    return {
        'price': 50000 + random.uniform(-10, 10),  # Very tight price range
        'volume': 1000 + random.uniform(-50, 50)
    }


def simulate_trend_initiation():
    """Simulate trend starting"""
    return {
        'price': 50000 + random.uniform(200, 500),  # Strong price movement
        'volume': 1000 + random.uniform(500, 1000)  # Increased volume
    }


def test_volume_analyzer():
    """Test volume anomaly detection"""
    print("\n" + "="*70)
    print("Testing Volume Analyzer")
    print("="*70)
    
    analyzer = VolumeAnalyzer()
    product_id = "TEST-USD"
    
    # Build baseline with normal data
    print("\nBuilding baseline with normal volume...")
    for i in range(20):
        data = simulate_normal_market()
        analyzer.update(product_id, data['volume'])
    
    # Test normal volume
    normal_data = simulate_normal_market()
    delta = analyzer.calculate_volume_delta(product_id, normal_data['volume'])
    print(f"Normal volume delta: {delta:.2f}σ")
    print(f"Is anomaly: {analyzer.is_volume_anomaly(delta)}")
    
    # Test volume spike
    spike_data = simulate_volume_spike()
    delta = analyzer.calculate_volume_delta(product_id, spike_data['volume'])
    print(f"\nVolume spike delta: {delta:.2f}σ")
    print(f"Is anomaly: {analyzer.is_volume_anomaly(delta)}")
    
    assert analyzer.is_volume_anomaly(delta), "Volume spike should be detected"
    print("✓ Volume spike detected correctly!")


def test_volatility_analyzer():
    """Test volatility compression detection"""
    print("\n" + "="*70)
    print("Testing Volatility Analyzer")
    print("="*70)
    
    analyzer = VolatilityAnalyzer()
    product_id = "TEST-USD"
    
    # Build baseline with normal volatility
    print("\nBuilding baseline with normal volatility...")
    for i in range(20):
        data = simulate_normal_market()
        analyzer.update(product_id, data['price'])
    
    # Test normal volatility
    volatility = analyzer.calculate_volatility(product_id)
    print(f"Normal volatility: {volatility:.4f}")
    print(f"Is compressed: {analyzer.is_compressed(volatility)}")
    
    # Test compression
    print("\nSimulating compression period...")
    for i in range(15):
        data = simulate_compression()
        analyzer.update(product_id, data['price'])
    
    volatility = analyzer.calculate_volatility(product_id)
    print(f"Compressed volatility: {volatility:.4f}")
    print(f"Is compressed: {analyzer.is_compressed(volatility)}")
    
    assert analyzer.is_compressed(volatility), "Compression should be detected"
    print("✓ Volatility compression detected correctly!")


def test_trend_analyzer():
    """Test trend initiation detection"""
    print("\n" + "="*70)
    print("Testing Trend Analyzer")
    print("="*70)
    
    analyzer = TrendAnalyzer()
    product_id = "TEST-USD"
    
    # Build baseline with normal data
    print("\nBuilding baseline with normal market...")
    base_price = 50000
    for i in range(20):
        data = simulate_normal_market()
        analyzer.update(product_id, data['price'], data['volume'])
    
    # Test normal conditions
    strength = analyzer.calculate_trend_strength(product_id)
    print(f"Normal trend strength: {strength:.4f}")
    print(f"Is trend initiating: {analyzer.is_trend_initiating(strength)}")
    
    # Test trend initiation
    print("\nSimulating trend initiation...")
    for i in range(10):
        # Gradually increasing price and volume
        price = base_price + (i * 100)
        volume = 1000 + (i * 100)
        analyzer.update(product_id, price, volume)
    
    strength = analyzer.calculate_trend_strength(product_id)
    print(f"Trend strength: {strength:.4f}")
    print(f"Is trend initiating: {analyzer.is_trend_initiating(strength)}")
    
    assert analyzer.is_trend_initiating(strength), "Trend should be detected"
    print("✓ Trend initiation detected correctly!")


def test_combined_anomaly():
    """Test combined anomaly detection"""
    print("\n" + "="*70)
    print("Testing Combined Anomaly Detection")
    print("="*70)
    
    volume_analyzer = VolumeAnalyzer()
    volatility_analyzer = VolatilityAnalyzer()
    trend_analyzer = TrendAnalyzer()
    product_id = "BTC-USD"
    
    # Build baseline
    print("\nBuilding baseline data (30 periods)...")
    for i in range(30):
        data = simulate_normal_market()
        volume_analyzer.update(product_id, data['volume'])
        volatility_analyzer.update(product_id, data['price'])
        trend_analyzer.update(product_id, data['price'], data['volume'])
    
    print("Baseline established.")
    
    # Simulate perfect setup for breakout
    print("\nSimulating pre-breakout conditions:")
    print("  - Compression phase (tight price range)")
    for i in range(10):
        data = simulate_compression()
        volume_analyzer.update(product_id, data['volume'])
        volatility_analyzer.update(product_id, data['price'])
        trend_analyzer.update(product_id, data['price'], data['volume'])
    
    print("  - Breakout (volume spike + trend initiation)")
    for i in range(5):
        data = simulate_volume_spike()
        price = 50000 + (i * 150)
        volume_analyzer.update(product_id, data['volume'])
        volatility_analyzer.update(product_id, price)
        trend_analyzer.update(product_id, price, data['volume'])
    
    # Check all conditions
    volume_delta = volume_analyzer.calculate_volume_delta(product_id, simulate_volume_spike()['volume'])
    volatility = volatility_analyzer.calculate_volatility(product_id)
    trend_strength = trend_analyzer.calculate_trend_strength(product_id)
    
    print(f"\nFinal Analysis:")
    print(f"  Volume Delta: {volume_delta:.2f}σ (anomaly: {volume_analyzer.is_volume_anomaly(volume_delta)})")
    print(f"  Volatility: {volatility:.4f} (compressed: {volatility_analyzer.is_compressed(volatility)})")
    print(f"  Trend Strength: {trend_strength:.4f} (initiating: {trend_analyzer.is_trend_initiating(trend_strength)})")
    
    # Calculate anomaly score
    score = 0
    if volume_analyzer.is_volume_anomaly(volume_delta):
        score += 3
        print("\n  ⚠ Volume Anomaly Detected (+3)")
    if volatility_analyzer.is_compressed(volatility):
        score += 2
        print("  ⚠ Volatility Compression Detected (+2)")
    if trend_analyzer.is_trend_initiating(trend_strength):
        score += 2
        print("  ⚠ Trend Initiation Detected (+2)")
    
    print(f"\n  Total Anomaly Score: {score}/7")
    
    if score >= 3:
        print("\n  🚨 ALERT THRESHOLD REACHED - Would trigger notification!")
    
    assert score >= 3, "Combined anomaly should trigger alert"
    print("\n✓ Combined anomaly detection working correctly!")


def main():
    """Run all tests"""
    print("\n╔════════════════════════════════════════════════════════════════════╗")
    print("║   PVAD Test Suite                                                  ║")
    print("║   Testing anomaly detection algorithms                            ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    
    try:
        test_volume_analyzer()
        test_volatility_analyzer()
        test_trend_analyzer()
        test_combined_anomaly()
        
        print("\n" + "="*70)
        print("ALL TESTS PASSED ✓")
        print("="*70)
        print("\nThe PVAD detection algorithms are functioning correctly!")
        print("The script is ready to use with live Coinbase data.")
        print()
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
