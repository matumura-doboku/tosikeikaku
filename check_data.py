import pandas as pd
import sys

files = [
    r'c:\Users\gyoru\Desktop\city_lite\data\statistical\tblT001101H34.txt',
    r'c:\Users\gyoru\Desktop\city_lite\data\statistical\tblT001108H34.txt',
    r'c:\Users\gyoru\Desktop\city_lite\data\statistical\tblT001164H34.txt'
]

def check_file(path):
    print(f"--- Checking {path} ---")
    encodings = ['cp932', 'utf-8']
    
    for enc in encodings:
        try:
            print(f"Trying encoding: {enc}")
            # Read first 15 lines to inspect structure manually
            with open(path, 'r', encoding=enc) as f:
                lines = [f.readline().strip() for _ in range(15)]
            
            print("First 15 lines content:")
            for i, line in enumerate(lines):
                print(f"{i}: {line}")
                
            print(f"Successfully read with {enc}")
            break
        except UnicodeDecodeError:
            print(f"Failed with {enc}")
        except Exception as e:
            print(f"Error: {e}")

for f in files:
    check_file(f)
