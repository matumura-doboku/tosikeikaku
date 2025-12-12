import pandas as pd

file_path = r'c:\Users\gyoru\Desktop\city_lite\data\statistical\tblT001101H34.txt'

with open(file_path, 'r', encoding='cp932') as f:
    lines = [f.readline().strip() for _ in range(20)]

print("Line 0 (Header):")
print(lines[0])
print("\nScanning for Japanese line...")
for i, line in enumerate(lines):
    if i == 0: continue
    if len(line) > 10 and ',' in line: # Candidate for data or label
        print(f"Line {i}: {line}")
        # Check split count
        header_cols = len(lines[0].split(','))
        line_cols = len(line.split(','))
        print(f"Header cols: {header_cols}, This line cols: {line_cols}")
