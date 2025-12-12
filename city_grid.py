import numpy as np
import json
import math
import pandas as pd

class CityGrid:
    def __init__(self, width=100, height=100):
        self.width = width
        self.height = height
        
        # --- Dynamic Layers (2D Float Arrays) ---
        # 1. Population Layer: Number of people per cell
        self.population = np.zeros((height, width), dtype=np.float32)
        # 2. Land Price Layer: Unit price per cell (kept for compatibility)
        self.land_price = np.zeros((height, width), dtype=np.float32)
        # 3. Accessibility (ACC) Layer: Score of convenience
        self.acc = np.zeros((height, width), dtype=np.float32)
        
        # --- Static / Attribute Layers ---
        self.base_land_price = np.ones((height, width), dtype=np.float32) * 10.0
        self.zone_type = np.zeros((height, width), dtype=np.int32)
        self.elderly_share = np.zeros((height, width), dtype=np.float32)

        # Time step counter
        self.current_year = 0

        # Mapping helpers
        self.mapper = None

    def reset(self):
        """Resets dynamic layers to initial state."""
        self.acc.fill(0)
        self.population.fill(0)
        self.land_price.fill(0)
        self.elderly_share.fill(0)
        self.current_year = 0
        # Land price might depend on base_land_price, so maybe reset to base?
        # For now, we recalculate it in step_simulation, so initialization here is fine.
        
    def set_mapper(self, mapper):
        """Sets the MeshGridMapper to convert between Mesh Codes and Grid coords."""
        self.mapper = mapper
        # Resize grid if mapper dimensions differ?
        # Ideally CityGrid is initialized with mapper.cols/rows.
        if mapper.cols != self.width or mapper.rows != self.height:
            print(f"Resize Grid: {self.width}x{self.height} -> {mapper.cols}x{mapper.rows}")
            self.width = mapper.cols
            self.height = mapper.rows
            self.population = np.zeros((self.height, self.width), dtype=np.float32)
            self.land_price = np.zeros((self.height, self.width), dtype=np.float32)
            self.acc = np.zeros((self.height, self.width), dtype=np.float32)
            self.base_land_price = np.ones((self.height, self.width), dtype=np.float32) * 10.0
            self.zone_type = np.zeros((self.height, self.width), dtype=np.int32)
            self.elderly_share = np.zeros((self.height, self.width), dtype=np.float32)
        self.current_year = 0

    def sync_from_geojson(self, geojson_data, mapper=None):
        """
        Populate grid from GeoJSON features using POP_TOTAL and other props.
        """
        if mapper:
            self.set_mapper(mapper)
        
        if not self.mapper:
            print("Error: No mapper set for CityGrid.")
            return

        print("Syncing Grid from GeoJSON...")
        for feature in geojson_data['features']:
            props = feature.get('properties', {})
            mesh_code = props.get('KEY_CODE')
            if not mesh_code: continue
            
            coords = self.mapper.get_grid_coords(mesh_code)
            if not coords: continue
            
            x, y = coords
            
            # Bounds check
            if 0 <= x < self.width and 0 <= y < self.height:
                # 1. Population
                pop = props.get('POP_TOTAL', 0)
                try:
                    pop = float(pop)
                except:
                    pop = 0
                self.population[y, x] = pop
                
                # 2. Base Land Price (Mock: Higher if Pop is high initially?)
                # Or randomize/use property
                # Let's simple heuristic: Base Price = 10 + (Pop / 100)
                self.base_land_price[y, x] = 10.0 + (pop / 10.0)

                # 3. Accessibility from property if present
                if 'benrido' in props:
                    try:
                        self.acc[y, x] = float(props.get('benrido', 0))
                    except Exception:
                        pass

    def add_facility_effect(self, x, y, impact_radius, weight):
        """
        Adds accessibility score around a facility using array slicing (Stamping).
        Efficiently updates ACC without iterating whole grid.
        """
        # 1. Define bounds to handle edges
        x_start = max(0, x - impact_radius)
        x_end = min(self.width, x + impact_radius + 1)
        y_start = max(0, y - impact_radius)
        y_end = min(self.height, y + impact_radius + 1)
        
        # 2. Create the distance kernel (simplified decay)
        # Using Manhattan distance for performance
        # ogrid returns open grids which are memory efficient for broadcasting
        # We need coordinates relative to the center (x, y)
        ry, rx = np.ogrid[y_start-y:y_end-y, x_start-x:x_end-x]
        dist = np.abs(rx) + np.abs(ry) # Manhattan distance
        
        # 3. Calculate impact (Linear decay: Weight at center, 0 at edge)
        # impact = weight * (1 - dist / radius)
        # We add 1.0 to radius divisor to avoid division by zero or immediate zeroing
        impact = np.maximum(0, weight * (1 - dist / (impact_radius + 1.0)))
        
        # 4. Apply stamp to grid
        self.acc[y_start:y_end, x_start:x_end] += impact

    def set_accessibility(self, acc_grid):
        """Sets the accessibility layer directly from a 2D array."""
        if acc_grid.shape == (self.height, self.width):
            self.acc = acc_grid.astype(np.float32)
        else:
            print(f"Error: Shape mismatch. Grid {self.width}x{self.height} vs Input {acc_grid.shape}")

    def compute_benrido_from_statistical(self, facility_csv, mapping_csv, include_gender=False, spread=True):
        """
        Build an accessibility (acc) layer from facility stats and benrido mapping.
        - facility_csv: data/statistical/tblT001164H34.csv
        - mapping_csv: data/statistical/tblT001164H34_mapping_with_benrido.csv
        - include_gender: include 男/女別列をカウントに入れるかどうか
        - spread: Trueなら距離減衰で周辺セルへ拡散、Falseならセル内のみ
        """
        if not self.mapper:
            print("Error: No mapper set for CityGrid. Call set_mapper() first.")
            return None

        # 1) benridoマッピングの読み込み
        df_map = pd.read_csv(mapping_csv)
        if not include_gender:
            df_map = df_map[~df_map["label"].astype(str).str.contains("男-|女-", regex=True, na=False)]
        code_to_benrido = {
            str(row["code"]): float(row["benrido"])
            for _, row in df_map.iterrows()
            if str(row["code"]).startswith("T") and float(row["benrido"]) > 0
        }
        if not code_to_benrido:
            print("Warning: No benrido codes found in mapping.")
            return None

        # 2) 施設データの読み込み
        df_fac = pd.read_csv(facility_csv)
        if "KEY_CODE" not in df_fac.columns:
            print("Error: facility_csv must contain KEY_CODE column.")
            return None

        acc_grid = np.zeros((self.height, self.width), dtype=np.float32)

        for row in df_fac.itertuples(index=False):
            mesh_code = str(row.KEY_CODE)
            coords = self.mapper.get_grid_coords(mesh_code)
            if not coords:
                continue
            x, y = coords

            contributions = []
            max_benrido = 0.0
            for code, ben in code_to_benrido.items():
                if code not in df_fac.columns:
                    continue
                val = getattr(row, code)
                try:
                    count = float(val)
                except Exception:
                    continue
                if count <= 0:
                    continue
                weight = ben / 5.0  # 1.0 when benrido=5
                # 1 - exp(-count) で施設数の逓減効果を入れる
                impact_center = weight * (1.0 - math.exp(-count))
                impact_center = max(0.0, min(1.0, impact_center))
                contributions.append(impact_center)
                max_benrido = max(max_benrido, ben)

            if not contributions:
                continue

            # セル内の合成（1 - ∏(1-impact) で上限1に近づく）
            center_impact = 1.0 - float(np.prod([1.0 - c for c in contributions]))
            self._stamp_impact(acc_grid, x, y, center_impact, max_benrido, spread)

        self.acc = acc_grid
        return acc_grid

    def _stamp_impact(self, acc_grid, x, y, impact, max_benrido, spread):
        """
        1セルもしくは近傍セルにimpactを合成（上限1）。
        benridoが大きいほど減衰（短距離）。小さいほど広く効く。
        """
        if impact <= 0:
            return

        if not spread or max_benrido <= 0:
            acc_grid[y, x] = 1.0 - (1.0 - acc_grid[y, x]) * (1.0 - impact)
            return

        # decay: benrido=5 -> 1セル程度, benrido=1 -> 5セル程度
        decay_cells = 1.0 + (5.0 - max_benrido)
        radius = max(1, int(math.ceil(decay_cells * 3)))

        x_start = max(0, x - radius)
        x_end = min(self.width, x + radius + 1)
        y_start = max(0, y - radius)
        y_end = min(self.height, y + radius + 1)

        for yy in range(y_start, y_end):
            for xx in range(x_start, x_end):
                manhattan = abs(xx - x) + abs(yy - y)
                if manhattan > radius:
                    continue
                attenuated = impact * math.exp(-manhattan / decay_cells)
                if attenuated <= 0:
                    continue
                acc_grid[yy, xx] = 1.0 - (1.0 - acc_grid[yy, xx]) * (1.0 - attenuated)

    def load_population_and_elderly_from_stat(self, pop_csv, elderly_col="T001101022", total_col="T001101001"):
        """
        メッシュ統計から人口と高齢者割合をセットする。
        - pop_csv: data/statistical/tblT001101H34.csv
        - elderly_col: 例 'T001101022' (75歳以上人口 総数)
        - total_col: 総人口列
        """
        if not self.mapper:
            print("Error: No mapper set for CityGrid. Call set_mapper() first.")
            return
        df = pd.read_csv(pop_csv)
        if "KEY_CODE" not in df.columns or elderly_col not in df.columns or total_col not in df.columns:
            print("Error: pop_csv missing required columns.")
            return

        self.population.fill(0)
        self.elderly_share.fill(0)
        for row in df.itertuples(index=False):
            code = str(row.KEY_CODE)
            coords = self.mapper.get_grid_coords(code)
            if not coords:
                continue
            x, y = coords
            try:
                total = float(getattr(row, total_col))
                elderly = float(getattr(row, elderly_col))
            except Exception:
                continue
            if total < 0:
                total = 0
            if elderly < 0:
                elderly = 0
            self.population[y, x] = total
            self.elderly_share[y, x] = elderly / total if total > 0 else 0.0

    def step_simulation(self, total_population=None, params=None):
        """
        Executes one simulation step with Feedback Loop:
        Pop (t-1) -> Land Price (t) -> Utility (t) -> Pop (t)
        """
        if params is None:
            # beta: Impact of ACC on Utility
            # inertia: Staying ratio when moving to new distribution
            # density_penalty: reduce utility by current density (optional)
            # attrition_base: baseline population decline
            # attrition_elderly_factor: additional decline proportional to elderly_share
            params = {
                'beta': 1.0,
                'inertia': 0.7,
                'density_penalty': 0.0,
                'attrition_base': 0.0,
                'attrition_elderly_factor': 0.05
            }
            
        # Use current total population if not specified
        if total_population is None:
            total_population = np.sum(self.population)

        # Utility from benrido (acc) minus optional density penalty
        utility = (self.acc * params.get('beta', 1.0)) - (self.population * params.get('density_penalty', 0.0))

        # Softmax redistribution
        max_util = np.max(utility)
        exp_utility = np.exp(utility - max_util)
        sum_exp = np.sum(exp_utility)
        if sum_exp > 0:
            prob_distribution = exp_utility / sum_exp
            target_pop = prob_distribution * total_population
            inertia = params.get('inertia', 0.7)
            new_pop = (self.population * inertia) + (target_pop * (1.0 - inertia))
        else:
            new_pop = self.population.copy()

        # Attrition based on elderly share
        attr_base = params.get('attrition_base', 0.0)
        attr_elder = params.get('attrition_elderly_factor', 0.05)
        attrition_rate = attr_base + attr_elder * self.elderly_share
        attrition_rate = np.clip(attrition_rate, 0.0, 1.0)
        self.population = new_pop * (1.0 - attrition_rate)

        # Update year counter
        self.current_year += 1
            
    def get_mapped_params(self):
        """
        Returns a dictionary keyed by Mesh Code with current state.
        {
          "5132...": { "land_price": 123.4, "population": 500, "acc": 5.5 }
        }
        """
        if not self.mapper:
            return {}
            
        result = {}
        for mesh_code, (x, y) in self.mapper.mapping.items():
            if 0 <= x < self.width and 0 <= y < self.height:
                result[mesh_code] = {
                    "land_price": float(self.land_price[y, x]),
                    "population": float(self.population[y, x]),
                    "acc": float(self.acc[y, x])
                }
        return result

    def to_json(self):
        """Export current state for frontend visualization."""
        # Using .tolist() converts NumPy arrays to standard Python lists for JSON serialization
        return {
            "width": self.width,
            "height": self.height,
            "year": self.current_year,
            "max_stats": {
                "price": float(np.max(self.land_price)),
                "pop": float(np.max(self.population)),
                "acc": float(np.max(self.acc))
            },
            "total_stats": {
                "price": float(np.sum(self.land_price)),
                "pop": float(np.sum(self.population))
            },
            "layers": {
                "land_price": self.land_price.tolist(),
                "population": self.population.tolist(),
                "acc": self.acc.tolist()
            }
        }

if __name__ == "__main__":
    # Simple test for Phase 1 verification
    print("Initializing CityGrid...")
    city = CityGrid(width=20, height=20)
    
    print("Adding Station at (10, 10)...")
    city.add_facility_effect(10, 10, impact_radius=5, weight=10.0)
    
    print("Running Simulation Step...")
    city.step_simulation(total_population=1000)
    
    stats = city.to_json()["max_stats"]
    print(f"Simulation Result: Max Price={stats['price']:.2f}, Max Pop={stats['pop']:.2f}")
    
    # Check if population concentrated near station
    center_pop = city.population[10, 10]
    edge_pop = city.population[0, 0]
    print(f"Center Pop: {center_pop:.2f}, Edge Pop: {edge_pop:.2f}")
    
    if center_pop > edge_pop:
        print("SUCCESS: Population concentrated near facility.")
    else:
        print("FAILURE: Population did not concentrate.")
