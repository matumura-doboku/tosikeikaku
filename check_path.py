import os

root_path = os.getcwd()
grid_dir = os.path.join(root_path, 'grid')
file_path = os.path.join(grid_dir, 'messyude-ta001.geojson')

print(f"Root path: {root_path}")
print(f"Grid dir: {grid_dir}")
print(f"Grid dir exists: {os.path.exists(grid_dir)}")
print(f"File path: {file_path}")
print(f"File exists: {os.path.exists(file_path)}")

if os.path.exists(grid_dir):
    print("Contents of grid dir:")
    for f in os.listdir(grid_dir):
        print(f" - {f}")
