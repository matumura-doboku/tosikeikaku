# routing_spec.md — 経路アルゴリズム手順

## 0. 用語
- `len_km`: リンク長[km]
- `base_speed_kmh`: 自由流速度[km/h]（線種別）
- `base_time_multiplier`: 線種別の自由流補正
- `alpha, beta`: BPRパラメータ（線種・車線別）
- `capacity_per_lane_vph`: 1車線容量[台/時]
- `lanes`: 車線数（片方向）
- `signal_density_per_km`: 信号密度[基/km]
- `stop_delay_sec_per_signal`: 1信号当たりの平均停止遅延[秒]
- `period_delay_multiplier`: 時間帯倍率
- `turn/add_delay_sec, conflict_multiplier`: 右左折ペナルティ
- `base_transfer_penalty_sec`: 線種乗換ペナルティの基礎[秒]
- `m_default`: 魅力度係数（曜日×時間×施設×規模）

## 1. ゾーン需要（発生P・集中A）の決定
1. ゾーン内施設を施設種別・規模にマッチングし、時間別の `m_default` を合成（加重平均または単純和）して魅力度 `M_z(h)` を得る。
2. 人口・従業員など基礎量 `N_z` と線種/延長スコアから、P_z(h), A_z(h) を比例配分。
   - 例: `A_z(h) ∝ N_z * M_z(h)`、`P_z(h) ∝ N_z * W_z`（W_z は就業/通学/私用の重み）。
3. 需要表はダブルコンストレインドでスケール合わせ。

## 2. エッジ所要時間の算出
1. 自由流時間 `t0 = len_km / base_speed_kmh * 60 * base_time_multiplier`。
2. 信号遅延 `t_sig = signal_density_per_km * len_km * stop_delay_sec_per_signal / 60`。
3. 容量 `C = capacity_per_lane_vph * lanes`、フロー `v` は逐次割当の累積。
4. BPR: `t_bpr = (t0 + t_sig) * (1 + alpha * (v/C)^beta)`。
5. 時間帯倍率: `t_edge = t_bpr * period_delay_multiplier`。
6. 交差点進入時に、該当する `intersection_type` の `base_delay_sec/60` を加算。
7. 交差点での右左折時に、`add_delay_sec/60 * conflict_multiplier` を加算。
8. 線種乗換時に、`base_transfer_penalty_sec + lane差ペナルティ` を加算（分単位に変換）。
9. 合計で `cost_edge_minutes` を得る。

## 3. 線種重み・近接補正（経路選択の“嗜好”）
1. OD 直線距離 `d_od_km` を距離帯にビン割りし、車種ごとに `Nat/Pref/Muni/Other` 重みを取得。
   - 経路探索時、各エッジの `cost_edge_minutes` をクラス重みで割って「好まれる道路」を優遇。
2. オリジン重心からの住宅距離 `d_origin_res_m` により、`Muni/Other` のローカル流入補正を乗ずる。
3. デスティネーション近傍距離 `d_dest_m` により、ラストマイルの `Muni/Other` 許容補正を乗ずる。
4. Truck は全距離帯で `Muni/Other` 重みが小さくなる設定。

## 4. 経路選択（多項ロジット）
- 代替経路 i のコスト `C_i` に対し、選択確率 `p_i = exp(-theta * C_i) / Σ exp(-theta * C_j)`。
- theta は `routing_params.yaml` の `route_choice.theta` で調整。

## 5. 割当（incremental assignment）
- 需要の30%→50%→20%を順に最短経路へ配分し、その都度リンクフロー `v` を更新して BPR 再計算。

## 6. 出力
- `od_boundary_hourly.csv`: 時間×境界ゾーン（方角）ごとの流入出、平均時間、平均コスト。
- `od_centroid_hourly.csv`: 時間×重心ゾーンごとの発生・集中・内部完結、平均時間・コスト。

## 7. 妥当性チェック
- 魅力度のサイズ階層単調性（S<=M<=L<=XL）。
- 主要施設でピーク時間が活動窓内に収まる。
- 幹線流量が距離増加で相対的に増加（ラインホール重み）。
- Truck の生活道路利用は最小限（ラストマイルを除く）。


<!-- DETOUR-ADDENDUM START -->
## 追加：迂回ロジック（渋滞検知→影響範囲→再配分→再評価）

この章は、既存の「BPR→ロジット→逐次割当」に対し最小改造で迂回を再現するための追記です。
実際の挿入箇所：
- §4 直後に **4.1 迂回モード（渋滞ペナルティの適用）**
- §5 と §6 の間に **5.1 迂回再配分ループ**
- §7 末尾に **7.1 追加の評価指標（迂回）**
- 末尾に **8. ルーティングパラメータ追加**

---

### 4.1 迂回モード（渋滞ペナルティの適用）
**目的**：渋滞リンク（R>R_on）を通る候補経路のコストを高め、代替経路を選びやすくする。

**定義（文章で先に）**
1) 各リンクの混雑度を `R = v / (capacity_per_lane_vph * lanes)` として計算する。
2) 渋滞判定は `R > R_on` でオン、`R < R_off` でオフ（ヒステリシス）。
3) 迂回モード `detour.enabled=true` のとき、次の追加コストを適用：
   - 渋滞リンク通過ごとに `penalties.congestion_penalty_sec` を加算。
   - 渋滞直近の流入リンクにも `penalties.near_congestion_penalty_sec` を任意で加算。
   - 生活道路の利用には `penalties.local_street_extra_sec` を加算（線種と車格で重み付け）。
   - 右左折ごとに `penalties.turn_per_intersection_sec` を加算。
4) これらのペナルティを含めた `C_i` を §4 のロジットに渡す（渋滞経由の候補は選ばれにくくなる）。

---

### 5.1 迂回再配分ループ
**目的**：ボトルネック上流の“超過分”だけを代替経路に再配分し、数回の反復で収束させる。

**流れ**
1) 渋滞リンク集合 `B = {link | R > R_on}` を抽出し、最小容量リンクを“ボトルネック代表”とする。
2) 各ボトルネックから**上流方向**に影響範囲をとる（距離 `D_up_km` または `k_hop`）。
3) 影響範囲内リンクの**超過流量**を `overflow = max(0, v - C * R_target)` として求める。
4) 迂回比率 `p = clip(alpha_detour * (R_bottleneck - 1.0), 0, p_max)` を計算。
5) 影響範囲内の各 OD（または近似OD）に対し、`overflow * p` を **k最短路**へロジット分配：
   - 候補 i の所要時間 `T_i` から `share_i = exp(-theta * T_i) / Σ exp(-theta * T_j)`。
6) フロー更新は振動回避のため**減衰** `gamma` を適用：
   - `v_new = gamma * v_reassigned + (1 - gamma) * v_old`
7) BPR で所要時間を再計算し、**総走行時間の改善率**がしきい値未満（`detour_convergence_improve_pct`）か、反復回数上限（`detour_iterations_max`）に達したら停止。

---

### 7.1 追加の評価指標（迂回）
- 代表ボトルネック周辺の `R_after` が **0.9±0.1** に近づく。
- 生活道路の `R` が **0.6〜0.85** に収まり“受け皿”になっている。
- 代替経路の右左折回数・信号密度が過剰でない（安全で妥当）。
- 逃がした台数／率、平均所要時間、総走行時間の改善率をダッシュボードで可視化。

---

## 8. ルーティングパラメータ追加（routing_params.yaml）
```yaml
detour:
  enabled: false        # 互換性維持のため初期はOFF
  R_on: 0.95            # 渋滞判定オン
  R_off: 0.85           # 渋滞解除
  R_target: 0.90        # 緩和目標R
  D_up_km: 1.5          # 影響上流距離（または）
  k_hop: 5              # 影響ホップ数
  k_alt: 3              # 候補経路本数
  alpha_detour: 0.6     # 迂回比率の傾き
  p_max: 0.4            # 1サイクルで逃がす上限比率
  gamma: 0.7            # 流量更新の減衰
  penalties:
    congestion_penalty_sec: 30         # 渋滞リンク通過
    near_congestion_penalty_sec: 10    # 渋滞直近流入
    local_street_extra_sec: 40         # 生活道路追加
    turn_per_intersection_sec: 10      # 右左折
assignment:
  detour_iterations_max: 5
  detour_convergence_improve_pct: 1.0  # 総走行時間の改善率しきい
route_choice:
  theta: 0.15
```

<!-- DETOUR-ADDENDUM END -->

