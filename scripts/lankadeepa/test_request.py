#!/usr/bin/env python3
"""Simple test to check if requests work"""

import requests

def test_basic_request():
    try:
        print("Testing basic request to Lankadeepa...")
        response = requests.get("https://www.lankadeepa.lk/politics/13", timeout=10)
        print(f"Status code: {response.status_code}")
        print(f"Content length: {len(response.text)}")
        print("✓ Basic request successful")
    except Exception as e:
        print(f"✗ Request failed: {e}")

if __name__ == "__main__":
    test_basic_request()
