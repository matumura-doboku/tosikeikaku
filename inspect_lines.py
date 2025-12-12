import pandas as pd

file_path = r'c:\Users\gyoru\Desktop\city_lite\data\statistical\tblT001101H34.txt'

print(f"--- Reading {file_path} ---")
with open(file_path, 'r', encoding='cp932') as f:
    lines = [f.readline().strip() for _ in range(15)]

for i, line in enumerate(lines):
    print(f"Line {i}: {line[:100]}...") # Truncate for display
