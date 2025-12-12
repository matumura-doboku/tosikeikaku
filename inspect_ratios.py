
import os
import json
import pandas as pd

# Path setup
app_root = os.getcwd()
pop_file_path = os.path.join(app_root, 'data', 'statistical', 'tblT001101H34.csv')
print(f"Reading {pop_file_path}")

try:
    if os.path.exists(pop_file_path):
        df_pop = pd.read_csv(pop_file_path, dtype={'KEY_CODE': str})
        
        # Cols
        cols = ['T001101001', 'T001101004', 'T001101010', 'T001101019']
        print("Columns found check:", all(c in df_pop.columns for c in cols))
        
        # Calculate max ratio
        max_ratio = 0
        max_row = None
        
        for index, row in df_pop.iterrows():
            try:
                total = int(row['T001101001'])
                p65 = int(row['T001101019'])
                
                if total > 0:
                    ratio = float(f"{(p65 / total * 100):.1f}")
                    if ratio > max_ratio:
                        max_ratio = ratio
                        max_row = row
            except Exception:
                continue
                
        print(f"Max 65+ Ratio found: {max_ratio}")
        if max_row is not None:
             print(f"Row data: Total={max_row['T001101001']}, 65+={max_row['T001101019']}")
             
    else:
        print("File not found")
except Exception as e:
    print(f"Error: {e}")
