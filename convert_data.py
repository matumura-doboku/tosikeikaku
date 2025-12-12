import pandas as pd
import os

files = [
    r'c:\Users\gyoru\Desktop\city_lite\data\statistical\tblT001101H34.txt',
    r'c:\Users\gyoru\Desktop\city_lite\data\statistical\tblT001108H34.txt',
    r'c:\Users\gyoru\Desktop\city_lite\data\statistical\tblT001164H34.txt'
]

output_dir = r'c:\Users\gyoru\Desktop\city_lite\data\statistical\clean'
os.makedirs(output_dir, exist_ok=True)

for file_path in files:
    filename = os.path.basename(file_path)
    print(f"Processing {filename}...")
    
    try:
        with open(file_path, 'r', encoding='cp932') as f:
            lines = f.readlines()
            
        # Line 0: English Header
        header_en = lines[0].strip().split(',')
        
        # Line 8: Japanese Header (Assuming fixed position based on analysis)
        # We need to find the line that has the same number of columns as header_en
        header_jp_line_idx = -1
        for i in range(1, 15):
            line_cols = lines[i].strip().split(',')
            if len(line_cols) == len(header_en):
                header_jp_line_idx = i
                break
        
        if header_jp_line_idx == -1:
            print(f"  WARNING: Could not find matching Japanese header line for {filename}")
            header_jp = ["Unknown"] * len(header_en)
            data_start_idx = 1 # Fallback
        else:
            header_jp = lines[header_jp_line_idx].strip().split(',')
            data_start_idx = header_jp_line_idx + 1
            print(f"  Found Japanese header at line {header_jp_line_idx}")

        # Extract Data
        data_lines = lines[data_start_idx:]
        
        # 1. Save Clean Data CSV (English Headers)
        clean_csv_path = os.path.join(output_dir, filename.replace('.txt', '.csv'))
        with open(clean_csv_path, 'w', encoding='utf-8') as f:
            f.write(','.join(header_en) + '\n')
            for line in data_lines:
                f.write(line)
        print(f"  Saved clean CSV: {clean_csv_path}")
        
        # 2. Save Mapping CSV
        mapping_csv_path = os.path.join(output_dir, filename.replace('.txt', '_mapping.csv'))
        df_map = pd.DataFrame({
            'code': header_en,
            'label': header_jp
        })
        df_map.to_csv(mapping_csv_path, index=False, encoding='utf-8-sig')
        print(f"  Saved mapping CSV: {mapping_csv_path}")

    except Exception as e:
        print(f"  ERROR processing {filename}: {e}")
