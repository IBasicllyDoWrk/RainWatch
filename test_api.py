#!/usr/bin/env python3
"""
Simple test script to verify the new API endpoint works correctly.
"""
import requests
import json
from datetime import datetime

def test_api_endpoint():
    """Test the new /api/devices/{device_id}/latest endpoint"""
    
    base_url = "http://localhost:8000"
    
    print("Testing RainWatch API endpoints...")
    
    # Test 1: Get all devices
    print("\n1. Testing /api/devices endpoint:")
    try:
        response = requests.get(f"{base_url}/api/devices")
        if response.status_code == 200:
            devices = response.json()
            print(f"✓ Found {len(devices)} devices")
            for device in devices:
                print(f"  - Device {device['id']}: {device['name']} at ({device['latitude']}, {device['longitude']})")
        else:
            print(f"✗ Error: {response.status_code}")
            return
    except requests.exceptions.ConnectionError:
        print("✗ Connection error - make sure the server is running on localhost:8000")
        return
    
    # Test 2: Get latest reading for first device
    if devices:
        device_id = devices[0]['id']
        device_name = devices[0]['name']
        
        print(f"\n2. Testing /api/devices/{device_id}/latest endpoint for '{device_name}':")
        try:
            response = requests.get(f"{base_url}/api/devices/{device_id}/latest")
            if response.status_code == 200:
                reading = response.json()
                print("✓ Latest reading retrieved successfully:")
                print(f"  - Device: {reading['device_name']}")
                print(f"  - Temperature: {reading['temperature']}°C")
                print(f"  - Humidity: {reading['humidity']}%")
                print(f"  - Pressure: {reading['pressure']} hPa")
                print(f"  - Rain Chance: {reading['rain_chance']}%")
                if reading['timestamp']:
                    timestamp = datetime.fromisoformat(reading['timestamp'].replace('Z', '+00:00'))
                    print(f"  - Last Updated: {timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                else:
                    print("  - Last Updated: No data available")
            else:
                print(f"✗ Error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"✗ Error: {e}")
    
    # Test 3: Test non-existent device
    print(f"\n3. Testing /api/devices/999/latest endpoint (non-existent device):")
    try:
        response = requests.get(f"{base_url}/api/devices/999/latest")
        if response.status_code == 404:
            print("✓ Correctly returned 404 for non-existent device")
        else:
            print(f"✗ Expected 404, got {response.status_code}")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print("\nAPI testing complete!")

if __name__ == "__main__":
    test_api_endpoint()
