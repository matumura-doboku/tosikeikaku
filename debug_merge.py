import json
import pandas as pd
import os

# Check GeoJSON
geojson_path = r'c:\Users\gyoru\Desktop\city_lite\grid\messyude-ta001.geojson'
print(f"Checking GeoJSON: {geojson_path}")
if os.path.exists(geojson_path):
    with open(geojson_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        if data['features']:
            print("First feature properties:")
            props = data['features'][0]['properties']
            for k, v in props.items():
                print(f"  {k}: {v}")
        else:
            print("No features found in GeoJSON")
else:
    print("GeoJSON file not found")

print("-" * 20)

# Check CSV (Corrected Path)
csv_path = r'c:\Users\gyoru\Desktop\city_lite\data\statistical\tblT001101H34.csv'
print(f"Checking CSV: {csv_path}")
if os.path.exists(csv_path):
    # Try reading with different encodings if utf-8 fails, though pandas usually handles csv well
    try:
        df = pd.read_csv(csv_path, dtype={'KEY_CODE': str}, encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(csv_path, dtype={'KEY_CODE': str}, encoding='cp932')
        
    print("CSV Columns:", df.columns.tolist())
    print("First 5 rows KEY_CODE:")
    print(df['KEY_CODE'].head())
else:
    print("CSV file not found")
