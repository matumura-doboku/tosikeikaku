import pandas as pd
import networkx as nx
import numpy as np
import yaml
import collections
import os
import sys
import math
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Set

# ==========================================
# 0. 初期設定 & ユーティリティ (Config & Utils)
# ==========================================

DEFAULT_CONFIG = {
    "periods": [{"key": "AM_PEAK", "window": "07:00-09:00"}],
    "assignment": {"increments": [1.0]}, # Single step for speed
    "route_choice": {"theta": 0.1, "k_paths": 1}, # Dijkstra
    "bpr": {"alpha": 0.15, "beta": 4.0},
    "units": {
        "production": {"pop": 0.4, "emp": 0.0},
        "attraction": {"pop": 0.1, "emp": 0.4}
    }
}

class MeshUtils:
    """JISメッシュコード(標準地域メッシュ)のユーティリティ"""
    
    @staticmethod
    def parse_mesh_code(code: str) -> Tuple[int, int, int, int]:
        """
        メッシュコードを解析し、正規化された座標(lat, lon相当のインデックス)を返す。
        対応: 1次, 2次, 3次, 4次(1/2地域)
        Return: (lat_index, lon_index, scale_level, code_type)
        ※ここでは簡易的に、絶対的な「位置ID」ではなく、隣接判定用のロジックのみ実装する。
        """
        c = str(code)
        length = len(c)
        
        # 3次メッシュ (8桁)
        if length == 8:
            # 1次
            y1 = int(c[0:2])
            x1 = int(c[2:4])
            # 2次
            y2 = int(c[4:5])
            x2 = int(c[5:6])
            # 3次
            y3 = int(c[6:7])
            x3 = int(c[7:8])
            return (y1, x1, y2, x2, y3, x3, 0, 0), 3
            
        # 4次メッシュ (9桁 - 2分の1地域メッシュ)
        elif length >= 9:
            base = c[0:8]
            sub = int(c[8])
            # 4次: 1=SW, 2=SE, 3=NW, 4=NE
            # 座標系として 3次メッシュを 2x2 に分割した座標を返す
            y1 = int(c[0:2]); x1 = int(c[2:4])
            y2 = int(c[4:5]); x2 = int(c[5:6])
            y3 = int(c[6:7]); x3 = int(c[7:8])
            
            # 内部座標 (0,0) ~ (1,1)
            sy = 0 if sub in [1, 2] else 1
            sx = 0 if sub in [1, 3] else 1
            return (y1, x1, y2, x2, y3, x3, sy, sx), 4
            
        return None, 0

    @staticmethod
    def get_neighbor(code: str, direction: str) -> Optional[str]:
        """
        指定された方向(n, s, e, w)の隣接メッシュコードを返す。
        簡易実装: 数値計算で隣接コードを算出する(繰り上がり処理含む)。
        注: 厳密なJIS仕様(緯度経度変換)までは実装せず、コード体系の規則性を利用する。
        """
        parsed, level = MeshUtils.parse_mesh_code(code)
        if not parsed: return None
        
        y1, x1, y2, x2, y3, x3, sy, sx = parsed
        
        # 移動量
        dy, dx = 0, 0
        if direction == 'n': dy = 1
        elif direction == 's': dy = -1
        elif direction == 'e': dx = 1
        elif direction == 'w': dx = -1
        
        # 4次メッシュレベルでの加算
        if level == 4:
            ny, nx_ = sy + dy, sx + dx
            
            # 繰り上がり/繰り下がり処理 (再帰はせず、フラットに処理)
            carry_y, carry_x = 0, 0
            
            # Sub-mesh (0-1 range)
            if ny > 1: ny -= 2; carry_y = 1
            elif ny < 0: ny += 2; carry_y = -1
            
            if nx_ > 1: nx_ -= 2; carry_x = 1
            elif nx_ < 0: nx_ += 2; carry_x = -1
            
            # 3次メッシュ (0-9 range)
            y3 += carry_y; x3 += carry_x
            carry_y, carry_x = 0, 0
            if y3 > 9: y3 -= 10; carry_y = 1
            elif y3 < 0: y3 += 10; carry_y = -1
            
            if x3 > 9: x3 -= 10; carry_x = 1
            elif x3 < 0: x3 += 10; carry_x = -1
            
            # 2次メッシュ (0-7 range)
            y2 += carry_y; x2 += carry_x
            carry_y, carry_x = 0, 0
            if y2 > 7: y2 -= 8; carry_y = 1
            elif y2 < 0: y2 += 8; carry_y = -1
            if x2 > 7: x2 -= 8; carry_x = 1
            elif x2 < 0: x2 += 8; carry_x = -1
            
            # 1次メッシュ (Lat:0-99, Lon:0-99 assumed)
            y1 += carry_y; x1 += carry_x
            
            # sub code reconstruction
            # 0,0->1(SW), 0,1->2(SE), 1,0->3(NW), 1,1->4(NE)
            sub_map = {(0,0):1, (0,1):2, (1,0):3, (1,1):4}
            new_sub = sub_map.get((ny, nx_), 1)
            
            return f"{y1:02}{x1:02}{y2}{x2}{y3}{x3}{new_sub}"
            
        return None # 3次以下は未実装(今回は4次メッシュ前提)

# ==========================================
# 1. データ読み込み (Data Loading)
# ==========================================

class SimulationData:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.zones: List[str] = []
        self.demand: pd.DataFrame = pd.DataFrame()
        self.hinagata_cols: List[str] = []
        self.network_graph: nx.DiGraph = nx.DiGraph()
        
    def load(self):
        print(f"Loading data from {self.data_dir}...")
        
        # 1. 雛形CSV (カラム定義のみ取得)
        hina_path = os.path.join(self.data_dir, "hinagata.csv")
        try:
            df_hina = pd.read_csv(hina_path, dtype=str, nrows=1)
            self.hinagata_cols = df_hina.columns.tolist()
        except Exception as e:
            print(f"Warning: Could not check hinagata columns: {e}")
            # フォールバックカラム
            self.hinagata_cols = ["key_code", "juusinkukaku_kansen_n", "juusinkukaku_kansen_s", 
                                  "juusinkukaku_kansen_e", "juusinkukaku_kansen_w"]

        # 2. 統計データ読み込み (Population & Employees)
        # tblT001101H34.csv (人口), tblT001108H34.csv (従業者) と仮定
        stats_dir = os.path.join(self.data_dir, "statistical")
        pop_file = os.path.join(stats_dir, "tblT001101H34.csv")
        emp_file = os.path.join(stats_dir, "tblT001108H34.csv")
        
        df_pop = self._safe_read_csv(pop_file, "KEY_CODE")
        df_emp = self._safe_read_csv(emp_file, "KEY_CODE")
        
        # マージ
        if not df_pop.empty:
            df_main = df_pop
            if not df_emp.empty:
                df_main = pd.merge(df_pop, df_emp, on="KEY_CODE", how="outer", suffixes=("_pop", "_emp"))
        elif not df_emp.empty:
            df_main = df_emp
        else:
            print("Error: No statistical data found. Using dummy data.")
            df_main = pd.DataFrame({"KEY_CODE": ["513204612", "513204614"], "T001101001": [100, 200]})

        self.demand = self._calculate_demand(df_main)
        self.zones = self.demand["zone_id"].astype(str).unique().tolist()
        print(f"Loaded {len(self.zones)} zones.")

    def _safe_read_csv(self, path, key_col):
        if not os.path.exists(path):
            return pd.DataFrame()
        try:
            # エンコーディング対応 (Shift-JIS or UTF-8)
            try:
                return pd.read_csv(path, dtype={key_col: str}, encoding="utf-8")
            except:
                return pd.read_csv(path, dtype={key_col: str}, encoding="cp932")
        except:
            return pd.DataFrame()

    def _calculate_demand(self, df: pd.DataFrame) -> pd.DataFrame:
        """統計値からP/Aを算出"""
        # カラム名の特定 (T...001 が総数と仮定)
        pop_col = next((c for c in df.columns if c.startswith("T001101001")), None)
        emp_col = next((c for c in df.columns if c.startswith("T001108001")), None)
        
        # 数値変換 (エラーは0に)
        if pop_col:
            df[pop_col] = pd.to_numeric(df[pop_col], errors='coerce').fillna(0)
        if emp_col:
            df[emp_col] = pd.to_numeric(df[emp_col], errors='coerce').fillna(0)
            
        demands = []
        for _, row in df.iterrows():
            pop = float(row.get(pop_col, 0)) if pop_col else 0
            emp = float(row.get(emp_col, 0)) if emp_col else 0
            
            # 原単位法
            prod = pop * DEFAULT_CONFIG["units"]["production"]["pop"] + emp * DEFAULT_CONFIG["units"]["production"]["emp"]
            attr = pop * DEFAULT_CONFIG["units"]["attraction"]["pop"] + emp * DEFAULT_CONFIG["units"]["attraction"]["emp"]
            
            if prod > 0 or attr > 0:
                demands.append({
                    "zone_id": str(row["KEY_CODE"]),
                    "production": prod,
                    "attraction": attr
                })
        return pd.DataFrame(demands)

# ==========================================
# 2. ネットワーク構築 (Network Builder)
# ==========================================

class NetworkBuilder:
    def __init__(self, zones: List[str]):
        self.zones = set(zones)
        self.G = nx.DiGraph()
        
    def build(self):
        print("Building Abstract Graph...")
        # 1. ノード作成
        for z in self.zones:
            # 重心
            self.G.add_node(f"{z}_C", type="centroid", zone=z)
            # 境界 (N, S, E, W)
            for d in ['n', 's', 'e', 'w']:
                node_id = f"{z}_{d.upper()}"
                self.G.add_node(node_id, type="boundary", zone=z, direction=d)
                
                # ゾーン内リンク (C <-> Boundary)
                # 距離: 重心から端までは約 250m~500m (4次メッシュは一辺約500m) -> 0.25km
                self.G.add_edge(f"{z}_C", node_id, length=0.25, capacity=500, free_speed=30, type="internal_out")
                self.G.add_edge(node_id, f"{z}_C", length=0.25, capacity=500, free_speed=30, type="internal_in")

        # 2. 通過リンク (Boundary -> Boundary in same zone)
        # N->S, S->N, E->W, W->E (直進のみ許可するとシンプル、だが右左折も本来はある)
        # ここでは簡易化のため、全結合 (N->S, N->E, N->W ...)
        for z in self.zones:
            boundaries = [f"{z}_{d}" for d in ['N', 'S', 'E', 'W']]
            for b1 in boundaries:
                for b2 in boundaries:
                    if b1 != b2:
                        # 通過コスト: 距離 0.5km
                        self.G.add_edge(b1, b2, length=0.5, capacity=1000, free_speed=40, type="passing")

        # 3. 隣接ゾーン接続 (Network Logic)
        print("Connecting Neighbors...")
        count = 0
        for z in self.zones:
            # 北の隣接
            n_code = MeshUtils.get_neighbor(z, 'n')
            if n_code and n_code in self.zones:
                # 自身のNと隣接のSを接続
                u, v = f"{z}_N", f"{n_code}_S"
                self.G.add_edge(u, v, length=0.01, capacity=9999, free_speed=60, type="connector") # 仮想リンク
                self.G.add_edge(v, u, length=0.01, capacity=9999, free_speed=60, type="connector")
                count += 1
                
            # 東の隣接
            e_code = MeshUtils.get_neighbor(z, 'e')
            if e_code and e_code in self.zones:
                # 自身のEと隣接のWを接続
                u, v = f"{z}_E", f"{e_code}_W"
                self.G.add_edge(u, v, length=0.01, capacity=9999, free_speed=60, type="connector")
                self.G.add_edge(v, u, length=0.01, capacity=9999, free_speed=60, type="connector")
                count += 1
                
        print(f"  Added {count} inter-zone connections.")
        return self.G

# ==========================================
# 3. シミュレーション (Traffic Assignment)
# ==========================================

class TrafficSimulator:
    def __init__(self, graph: nx.DiGraph, config: dict):
        self.G = graph
        self.config = config
        
    def _bpr_cost(self, free_time, flow, capacity):
        alpha = self.config["bpr"]["alpha"]
        beta = self.config["bpr"]["beta"]
        if capacity <= 0: return float('inf')
        return free_time * (1.0 + alpha * (flow / capacity) ** beta)

    def run(self, demand_df: pd.DataFrame):
        print("Starting Incremental Assignment...")
        
        # 1. Init Flows
        for u, v, d in self.G.edges(data=True):
            d['flow'] = 0.0
            t0 = (d['length'] / d['free_speed']) * 60 # minutes
            d['free_time'] = t0
            d['cost'] = t0
            d['weight'] = t0 # for pathfinding

        # 2. OD Pair Generation (Vectorized)
        zones = demand_df["zone_id"].values
        P = demand_df["production"].values
        A = demand_df["attraction"].values
        total_a = A.sum()
        
        if total_a == 0:
            print("Warning: Total Attraction is 0.")
            return self.G

        print("  Calculating OD Matrix...")
        # メモリ節約のため、ループではなく行列演算を行うが、14000^2は重いのでチャンク処理するか
        # または、条件を満たすものだけ抽出
        # Flow = P[i] * A[j] / TotalA > 0.1
        # => P[i] * A[j] > 0.1 * TotalA
        threshold = 0.1 * total_a
        
        od_flows = []
        # Pが大きい順に処理して枝刈りするなど工夫可能だが、Numpyなら一瞬
        # ただし行列生成(1.6GB)に注意
        try:
            # Full Matrix is acceptable for 14k zones (approx 1.5GB doubles)
            Mat = np.outer(P, A)
            rows, cols = np.where(Mat > threshold)
            
            # extract
            vals = Mat[rows, cols] / total_a
            
            # Map indices to zone IDs
            # zones[rows] -> Origin, zones[cols] -> Dest
            # Vectorized append is hard, assume list comprehension is fast enough for sparse
            # or better: iterate arrays
            print(f"  Found {len(vals)} significant OD pairs.")
            
            # 2.4Mは多すぎるので、デモ用にトップ100に絞る
            LIMIT_OD = 100
            if len(vals) > LIMIT_OD:
                print(f"  Limiting to top {LIMIT_OD} pairs for performance...")
                # ソートして上位を取得 (argsrotは昇順なので後ろから)
                top_indices = np.argsort(vals)[-LIMIT_OD:]
                rows = rows[top_indices]
                cols = cols[top_indices]
                vals = vals[top_indices]

            for r, c, v in zip(rows, cols, vals):
                if r == c: continue
                od_flows.append((f"{zones[r]}_C", f"{zones[c]}_C", v))
                
        except MemoryError:
            print("  Memory Error with full matrix. Switching to chunked iteration.")
            # Fallback
            for i, p in enumerate(P):
                if p <= 0: continue
                # Vectorized row check
                row_flows = p * A 
                # Filter
                indices = np.where(row_flows > threshold)[0]
                for j in indices:
                    if i == j: continue
                    od_flows.append((f"{zones[i]}_C", f"{zones[j]}_C", row_flows[j]/total_a))

        print(f"  Generated {len(od_flows)} OD pairs.")

        # 3. Incremental Assignment Loop
        steps = self.config["assignment"]["increments"]
        k_paths = self.config["route_choice"]["k_paths"]
        theta = self.config["route_choice"]["theta"]
        
        for step_idx, fraction in enumerate(steps):
            print(f"  Step {step_idx+1}/{len(steps)}: Assigning {fraction*100:.0f}% demand")
            
            # Update Costs
            for u, v, d in self.G.edges(data=True):
                d['cost'] = self._bpr_cost(d['free_time'], d['flow'], d['capacity'])
                d['weight'] = d['cost']

            # Assign Flow
            for o, d, total_vol in od_flows:
                vol = total_vol * fraction
                
                try:
                    # K-Shortest Paths (Yen's is slow, use only 1 if K=1 or simple)
                    if k_paths > 1:
                        paths = list(nx.shortest_simple_paths(self.G, o, d, weight='weight'))
                        paths = paths[:k_paths]
                    else:
                        paths = [nx.shortest_path(self.G, o, d, weight='weight')]
                except nx.NetworkXNoPath:
                    continue
                
                if not paths: continue

                # Logit Probabilities
                path_costs = [sum(self.G[u][v]['weight'] for u, v in zip(p[:-1], p[1:])) for p in paths]
                min_c = min(path_costs)
                exp_costs = [math.exp(-theta * (c - min_c)) for c in path_costs]
                sum_exp = sum(exp_costs)
                probs = [e/sum_exp for e in exp_costs]
                
                # Add Flow
                for p, prob in zip(paths, probs):
                    add = vol * prob
                    for u, v in zip(p[:-1], p[1:]):
                        self.G[u][v]['flow'] += add

        print("Simulation Completed.")
        return self.G

# ==========================================
# 4. 集計と出力 (Aggregation & Export)
# ==========================================

class ResultAggregator:
    def __init__(self, graph: nx.DiGraph, output_cols: List[str]):
        self.G = graph
        self.cols = output_cols
        
    def aggregate(self) -> pd.DataFrame:
        print("Aggregating results...")
        data = collections.defaultdict(dict)
        
        for u, v, d in self.G.edges(data=True):
            f = d['flow']
            if f <= 0.1: continue
            
            # Node names: {Zone}_{Type}
            # Type: C, N, S, E, W
            u_parts = u.split('_')
            v_parts = v.split('_')
            z_u, t_u = u_parts[0], u_parts[1]
            z_v, t_v = v_parts[0], v_parts[1]
            
            # Case 1: 重心発 (Production) -> zone_id = z_u
            if t_u == 'C':
                # format: juusinkukaku_kansen_{dir}
                # t_v should be N, S, E, W
                direction = t_v.lower()
                col = f"juusinkukaku_kansen_{direction}"
                if col not in data[z_u]: data[z_u][col] = 0
                data[z_u][col] += f
                
            # Case 2: 通過 (Boundary -> Boundary in SAME Zone) -> zone_id = z_u (= z_v)
            elif z_u == z_v and t_u in ['N','S','E','W'] and t_v in ['N','S','E','W']:
                # format: kyoukaikukaku_kansen_{in}_{out}
                # in: t_u の名前 (N=top, S=bottom...)
                # out: t_v の方向 (n, s, e, w)
                
                pos_map = {'N': 'top', 'S': 'bottom', 'E': 'right', 'W': 'left'}
                in_pos = pos_map.get(t_u, '')
                out_dir = t_v.lower()
                
                col = f"kyoukaikukaku_kansen_{in_pos}_{out_dir}"
                if col not in data[z_u]: data[z_u][col] = 0
                data[z_u][col] += f
                
            # Case 3: ゾーン間接続 (Connector) -> 無視 (集計対象外) or 吸収
            # u=ZoneA_N, v=ZoneB_S. これは "Link" ではなく "Connection".
            # フローは ZoneA の Exit Flow, ZoneB の Entry Flow だが
            # 上記 Case 2 で「境界まで行くフロー」はカウント済。
            # 「境界から出るフロー」は Case 2 の output 側で捕捉される。
            pass

        # DataFrame化
        rows = []
        all_zones = set(data.keys())
        
        # 雛形カラムに従って行を作成
        for z in all_zones:
            row = {"key_code": z}
            metrics = data[z]
            for c in self.cols:
                if c == "key_code": continue
                row[c] = round(metrics.get(c, 0))
            rows.append(row)
            
        return pd.DataFrame(rows)

# ==========================================
# Main Execution Block
# ==========================================

if __name__ == "__main__":
    # パス設定
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    OUTPUT_FILE = os.path.join(DATA_DIR, "simulation_result_fixed.csv")
    
    # 1. データロード
    sim_data = SimulationData(DATA_DIR)
    sim_data.load()
    
    if len(sim_data.zones) == 0:
        print("Error: No zones found. Exiting.")
        sys.exit(1)
        
    # 2. グラフ構築
    builder = NetworkBuilder(sim_data.zones)
    G = builder.build()
    
    # 3. シミュレーション実行
    simulator = TrafficSimulator(G, DEFAULT_CONFIG)
    G_result = simulator.run(sim_data.demand)
    
    # 4. 集計・出力
    aggregator = ResultAggregator(G_result, sim_data.hinagata_cols)
    df_result = aggregator.aggregate()
    
    # 雛形のカラム順序を維持
    final_cols = [c for c in sim_data.hinagata_cols if c in df_result.columns]
    # key_code が無ければ追加
    if "key_code" not in final_cols and "key_code" in df_result.columns:
        final_cols.insert(0, "key_code")
        
    df_result = df_result[final_cols]
    
    # 保存
    print(f"Exporting to {OUTPUT_FILE}...")
    df_result.to_csv(OUTPUT_FILE, index=False)
    print("Done!")