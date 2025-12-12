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
