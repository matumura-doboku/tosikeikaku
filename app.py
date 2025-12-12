import os
import json
from flask import Flask, render_template, jsonify, request
import pandas as pd
import threading

# Import Simulators
import advanced_city_simulator as acs
from city_grid import CityGrid
from mesh_utils import MeshGridMapper
import numpy as np

app = Flask(__name__)

# --- Traffic Simulator Globals ---
SIM_DATA = None
SIM_GRAPH = None
SIM_SIMULATOR = None
SIM_LOCK = threading.Lock()
LAST_RESULT = None

# --- City Grid Simulator Globals ---
CITY_SIM = CityGrid()
MESH_MAPPER = MeshGridMapper()
CITY_LOCK = threading.Lock()

def initialize_simulator():
    global SIM_DATA, SIM_GRAPH, SIM_SIMULATOR
    print("Initializing Traffic Simulator...")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, 'data')
    
    # 1. Data Load
    SIM_DATA = acs.SimulationData(data_dir)
    try:
        SIM_DATA.load()
    except Exception as e:
        print(f"Error loading simulation data: {e}")
        return

    # 2. Graph Build
    builder = acs.NetworkBuilder(SIM_DATA.zones)
    SIM_GRAPH = builder.build()
    
    # 3. Simulator Init
    SIM_SIMULATOR = acs.TrafficSimulator(SIM_GRAPH, acs.DEFAULT_CONFIG)
    print("Traffic Simulator Initialized.")

def initialize_city_grid(filter_codes=None):
    global CITY_SIM, MESH_MAPPER
    print(f"Initializing City Grid Model... Filter={len(filter_codes) if filter_codes else 'None'}")
    directory = os.path.join(app.root_path, 'grid')
    filename = 'messyude-ta001.geojson'
    file_path = os.path.join(directory, filename)
    
    if not os.path.exists(file_path):
        print(f"Error: Grid file not found at {file_path}")
        return

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            geojson_data = json.load(f)
            
        # Filter if requested
        if filter_codes:
            filter_set = set(str(c) for c in filter_codes)
            geojson_data['features'] = [
                f for f in geojson_data['features'] 
                if str(f['properties'].get('KEY_CODE')) in filter_set
            ]

        # 1. Fit Mapper
        codes = [f['properties'].get('KEY_CODE') for f in geojson_data['features'] if f['properties'].get('KEY_CODE')]
        
        if not codes:
            print("Error: No codes found.")
            return

        MESH_MAPPER = MeshGridMapper() # Reset
        MESH_MAPPER.fit(codes)
        print(f"Mesh Mapper fitted: {MESH_MAPPER.cols}x{MESH_MAPPER.rows}")
        
        # 2. Init Grid
        with CITY_LOCK:
            CITY_SIM = CityGrid() # Reset
            CITY_SIM.set_mapper(MESH_MAPPER)
            CITY_SIM.sync_from_geojson(geojson_data) # Loads Pop if present in GeoJSON

            # 3. Load population & elderly share from statistical CSV
            pop_csv = os.path.join(app.root_path, 'data', 'statistical', 'tblT001101H34.csv')
            if os.path.exists(pop_csv):
                CITY_SIM.load_population_and_elderly_from_stat(pop_csv, elderly_col="T001101022", total_col="T001101001")

            # 4. Set accessibility from GeoJSON benrido property (already written)
            acc_grid = np.zeros((CITY_SIM.height, CITY_SIM.width), dtype=np.float32)
            mapped = 0
            for feat in geojson_data.get('features', []):
                props = feat.get('properties', {})
                code = str(props.get('KEY_CODE', ''))
                coords = MESH_MAPPER.get_grid_coords(code)
                if not coords:
                    continue
                x, y = coords
                try:
                    val = float(props.get('benrido', 0))
                except Exception:
                    val = 0.0
                acc_grid[y, x] = val
                mapped += 1
            CITY_SIM.set_accessibility(acc_grid)
            CITY_SIM.base_land_price = np.ones((CITY_SIM.height, CITY_SIM.width), dtype=np.float32) * 10.0 + (CITY_SIM.population / 10.0)
            print(f"Mapped benrido accessibility to {mapped} grid cells.")
            
        print("City Grid Model Initialized.")
        
    except Exception as e:
        print(f"Error init City Grid: {e}")

# Initialize on startup
if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    # Run in threads to not block startup if heavy
    t1 = threading.Thread(target=initialize_simulator)
    t2 = threading.Thread(target=initialize_city_grid)
    t1.start()
    t2.start()

@app.route('/')
def index():
    return render_template('index.html')

# Load Road Data (Global)
ROAD_DATA = None
try:
    road_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'roads', 'hirosima', 'roads.geojson')
    if os.path.exists(road_path):
        with open(road_path, 'r', encoding='utf-8') as f:
            ROAD_DATA = json.load(f)
    print("Road data loaded successfully.")
except Exception as e:
    print(f"Error loading road data: {e}")


@app.route('/api/roads')
def get_roads():
    try:
        n = float(request.args.get('north'))
        s = float(request.args.get('south'))
        e_lng = float(request.args.get('east'))
        w_lng = float(request.args.get('west'))
    except (TypeError, ValueError):
        return jsonify({'type': 'FeatureCollection', 'features': []}), 400

    if not ROAD_DATA:
        return jsonify({'type': 'FeatureCollection', 'features': []})

    filtered_features = []
    
    # Simple Bounding Box Filter strategy
    for feature in ROAD_DATA['features']:
        geom = feature.get('geometry')
        if not geom: continue
        
        coords = []
        g_type = geom['type']
        
        if g_type == 'LineString':
            coords = geom['coordinates']
        elif g_type == 'MultiLineString' or g_type == 'Polygon':
            for part in geom['coordinates']:
                coords.extend(part)
        elif g_type == 'MultiPolygon':
             for poly in geom['coordinates']:
                 for ring in poly:
                     coords.extend(ring)
        
        f_min_x, f_min_y = 180, 90
        f_max_x, f_max_y = -180, -90
        has_points = False
        
        for p in coords:
            lon, lat = p[0], p[1]
            if lon < f_min_x: f_min_x = lon
            if lon > f_max_x: f_max_x = lon
            if lat < f_min_y: f_min_y = lat
            if lat > f_max_y: f_max_y = lat
            has_points = True
            
        if has_points:
            # Check overlap
            if (f_min_x <= e_lng and f_max_x >= w_lng and
                f_min_y <= n and f_max_y >= s):
                filtered_features.append(feature)

    return jsonify({
        'type': 'FeatureCollection',
        'features': filtered_features
    })

# --- Traffic Simulation Endpoints ---

@app.route('/api/simulate', methods=['POST'])
def run_simulation():
    global SIM_SIMULATOR, SIM_DATA, LAST_RESULT
    
    if SIM_SIMULATOR is None:
        initialize_simulator()
    
    if SIM_SIMULATOR is None:
        return jsonify({"error": "Simulator could not be initialized."}), 500

    try:
        with SIM_LOCK:
            G_result = SIM_SIMULATOR.run(SIM_DATA.demand)
            aggregator = acs.ResultAggregator(G_result, SIM_DATA.hinagata_cols)
            df_result = aggregator.aggregate()
            LAST_RESULT = df_result
            
            flow_cols = [c for c in df_result.columns if c != 'key_code']
            results = {}
            for _, row in df_result.iterrows():
                zid = str(row['key_code'])
                total_flow = sum(row[c] for c in flow_cols)
                if total_flow > 0:
                    results[zid] = {
                        'flow_Total': int(total_flow),
                        'details': row[flow_cols].to_dict()
                    }
                    
        return jsonify(results)

    except Exception as e:
        print(f"Simulation Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/report', methods=['GET'])
def get_report():
    global LAST_RESULT
    if LAST_RESULT is None:
        return jsonify({"status": "No data", "message": "Run simulation first."})
    
    df = LAST_RESULT
    flow_cols = [c for c in df.columns if c != 'key_code']
    
    total_flow_sum = df[flow_cols].sum().sum()
    zone_count = len(df)
    active_zones = (df[flow_cols].sum(axis=1) > 0).sum()
    
    df['total_flow'] = df[flow_cols].sum(axis=1)
    top_5 = df.nlargest(5, 'total_flow')[['key_code', 'total_flow']].to_dict('records')
    
    report = {
        "status": "Available",
        "summary": {
            "total_zones": int(zone_count),
            "active_traffic_zones": int(active_zones),
            "total_network_flow": int(total_flow_sum)
        },
        "top_congested_zones": top_5
    }

    # Add City Dynamics Stats if available
    with CITY_LOCK:
        if CITY_SIM:
            city_stats = CITY_SIM.to_json()
            report["city_model"] = {
                "max_land_price": city_stats["max_stats"]["price"],
                "max_population_cell": city_stats["max_stats"]["pop"],
                "total_population": city_stats["total_stats"]["pop"]
            }

    return jsonify(report)

# --- City Grid API ---

@app.route('/api/city/init', methods=['POST'])
def init_city():
    # Check for filter params
    mesh_codes = None
    try:
        data = request.get_json()
        if data and 'mesh_codes' in data:
            mesh_codes = data['mesh_codes']
    except:
        pass

    thread = threading.Thread(target=initialize_city_grid, args=(mesh_codes,))
    thread.start()
    return jsonify({"status": "Initializing City Grid...", "filtered": bool(mesh_codes)})



@app.route('/api/city/step', methods=['POST'])
def step_city():
    global CITY_SIM
    try:
        steps = 1
        try:
            data = request.get_json()
            if data and 'steps' in data:
                steps = max(1, int(data['steps']))
        except Exception:
            steps = 1

        with CITY_LOCK:
            for _ in range(steps):
                CITY_SIM.step_simulation()
            result = CITY_SIM.get_mapped_params()
            year = CITY_SIM.current_year
        return jsonify({"year": year, "results": result})
    except Exception as e:
        print(f"City Step Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/city/reset', methods=['POST'])
def reset_city():
    global CITY_SIM
    with CITY_LOCK:
        CITY_SIM.reset()
        # Re-sync if needed? Or just reset dynamic fields.
        # Ideally we re-run init logic without reading file if possible.
        # But for now reset() only clears accumulators.
        # We might want to reload population.
        initialize_city_grid() 
    return jsonify({"status": "City Grid Reset."})


@app.route('/grid-data')
def grid_data():
    try:
        directory = os.path.join(app.root_path, 'grid')
        filename = 'messyude-ta001.geojson'
        file_path = os.path.join(directory, filename)
        
        if not os.path.exists(file_path):
            return jsonify({"error": f"File not found: {file_path}"}), 404
            
        with open(file_path, 'r', encoding='utf-8') as f:
            geojson_data = json.load(f)

        # Merge Floor Area Data
        floor_file_path = os.path.join(app.root_path, 'data', 'yukamenseki', 'hirosima', 'yukamenseki_hirosima.csv')
        floor_map = {}
        if os.path.exists(floor_file_path):
            try:
                # 1行目はヘッダーなので自動的に処理されるが、念のため明示的に読み込む
                df_floor = pd.read_csv(floor_file_path, dtype={'KEY_CODE': str})
                # カラム名: KEY_CODE, total_floor_area
                floor_map = df_floor.set_index('KEY_CODE')['total_floor_area'].to_dict()
                print(f"Loaded {len(floor_map)} floor area records.")
            except Exception as e:
                print(f"Error loading floor area csv: {e}")

        # Merge Population Data (Static Verification Data)
        pop_file_path = os.path.join(app.root_path, 'data', 'statistical', 'tblT001101H34.csv')
        if os.path.exists(pop_file_path):
            df_pop = pd.read_csv(pop_file_path, dtype={'KEY_CODE': str})
            cols = ['T001101001', 'T001101002', 'T001101003', 'T001101004', 'T001101010', 'T001101019']
            pop_map = df_pop.set_index('KEY_CODE')[cols].to_dict('index')
            
            for feature in geojson_data['features']:
                key_code = str(feature['properties'].get('KEY_CODE', ''))
                
                # --- Population Stats ---
                if key_code in pop_map:
                    stats = pop_map[key_code]
                    
                    def safe_int(val):
                        try:
                            return int(val)
                        except:
                            return 0

                    total = safe_int(stats['T001101001'])
                    feature['properties']['POP_TOTAL'] = total
                    feature['properties']['POP_MALE'] = safe_int(stats['T001101002'])
                    feature['properties']['POP_FEMALE'] = safe_int(stats['T001101003'])
                    
                    if total > 0:
                        p_0_14 = safe_int(stats['T001101004'])
                        p_15_64 = safe_int(stats['T001101010'])
                        p_65_over = safe_int(stats['T001101019'])
                        
                        feature['properties']['RATIO_0_14'] = f"{(p_0_14 / total * 100):.1f}%"
                        feature['properties']['RATIO_15_64'] = f"{(p_15_64 / total * 100):.1f}%"
                        feature['properties']['RATIO_65_OVER'] = f"{(p_65_over / total * 100):.1f}%"
                        
                        feature['properties']['VAL_RATIO_0_14'] = min(float(f"{(p_0_14 / total * 100):.1f}"), 100.0)
                        feature['properties']['VAL_RATIO_15_64'] = min(float(f"{(p_15_64 / total * 100):.1f}"), 100.0)
                        feature['properties']['VAL_RATIO_65_OVER'] = min(float(f"{(p_65_over / total * 100):.1f}"), 100.0)
                    else:
                        feature['properties']['RATIO_0_14'] = "-"
                        feature['properties']['RATIO_15_64'] = "-" 
                        feature['properties']['RATIO_65_OVER'] = "-"
                        feature['properties']['VAL_RATIO_0_14'] = 0
                        feature['properties']['VAL_RATIO_15_64'] = 0
                        feature['properties']['VAL_RATIO_65_OVER'] = 0
                else:
                    feature['properties']['POP_TOTAL'] = 0
                    
                # --- Floor Area Stats ---
                # 床面積(㎡)
                floor_area = 0.0
                if key_code in floor_map:
                    try:
                        floor_area = float(floor_map[key_code])
                    except:
                        floor_area = 0.0
                
                feature['properties']['FLOOR_AREA'] = floor_area
                
                # 空き床面積(㎡) = 床面積 - (セル内人口 * １人当たりの仕様床面積(40㎡))
                pop = feature['properties'].get('POP_TOTAL', 0)
                required_area = pop * 40.0
                vacant_area = floor_area - required_area
                
                # データがないセルはなしでいい -> 床面積が0なら空きも0にしておくか、計算不可とするか
                # ここでは床面積がある場合のみ計算する
                if floor_area > 0:
                    feature['properties']['VACANT_FLOOR_AREA'] = round(vacant_area, 2)
                    
                    # 空き床面積率(%) = 空き床面積 / 床面積 * 100
                    # vacant_area could be negative if pop is overcrowded? 
                    # User didn't specify, but usually vacancy rate implies 0-100%. 
                    # If overcrowded, it might be negative vacancy? 
                    # Let's keep raw value but clamp rate for visualization if needed.
                    # Formula is simple: Vacant / Floor * 100
                    
                    rate = (vacant_area / floor_area) * 100.0
                    feature['properties']['VACANT_FLOOR_AREA_RATE'] = round(rate, 1)
                else:
                    feature['properties']['VACANT_FLOOR_AREA'] = 0
                    feature['properties']['VACANT_FLOOR_AREA_RATE'] = 0
                        
        return jsonify(geojson_data)
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
