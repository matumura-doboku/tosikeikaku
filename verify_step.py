
import requests
import json
import time

BASE_URL = "http://127.0.0.1:5000"

def run_test():
    # 1. Init (Full)
    print("Initializing...")
    res = requests.post(f"{BASE_URL}/api/city/init")
    print(f"Init Status: {res.status_code}")
    time.sleep(2) 

    # 2. Step Loop
    print("Running Steps...")
    for i in range(3):
        res = requests.post(f"{BASE_URL}/api/city/step")
        if res.status_code == 200:
            data = res.json()
            # Check a sample
            keys = list(data.keys())
            if keys:
                sample = data[keys[0]]
                print(f"Step {i+1}: Result Count={len(keys)}, Sample Price={sample.get('land_price'):.2f}")
            else:
                print(f"Step {i+1}: No data returned.")
        else:
            print(f"Step {i+1} Failed: {res.status_code} - {res.text}")
        time.sleep(1)

if __name__ == "__main__":
    run_test()
