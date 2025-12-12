
import json
import os
from mesh_utils import MeshGridMapper

# Load GeoJSON
path = 'grid/messyude-ta001.geojson'
if not os.path.exists(path):
    print("File not found.")
    exit()

with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Loaded {len(data['features'])} features.")

mapper = MeshGridMapper()
codes = [f['properties']['KEY_CODE'] for f in data['features']]
mapper.fit(codes)

print(f"Grid Size: {mapper.cols} x {mapper.rows}")
print(f"X Range: {mapper.min_x} - {mapper.max_x}")
print(f"Y Range: {mapper.min_y} - {mapper.max_y}")

# Test a few corners
first = codes[0]
print(f"First ({first}): {mapper.get_grid_coords(first)}")
last = codes[-1]
print(f"Last ({last}): {mapper.get_grid_coords(last)}")
