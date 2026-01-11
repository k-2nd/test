## 1. 論理シミュレーションの概要

* 目的        ：論理回路をコンピュータ上で擬似的に動作させ、実機動作前に機能の正当性を検証する。
* メリット    ：実機では観測困難な内部信号の波形確認や、発生頻度の低いイレギュラーな状態を意図的に再現したテストが可能。
* テストベンチ：検証対象（DUT）に入力を与え、出力を観測するための仕組み。設計者が別途作成する必要がある。


## 2. シミュレーションのレベル

設計段階に応じて、以下の5つのレベルでシミュレーションを実行できる。

| シミュレーションの種類             | 実行タイミング | 検証内容（主な目的）                           | 特徴・備考                                               |
| Behavioral                     | 設計初期 (RTL) | アルゴリズムやロジックが論理的に正しいか       | HDLソースを直接動かす。設計デバッグのメイン。            |
| Post-Synthesis Functional      | 論理合成後     | 合成によって回路構成が意図せず変化していないか | ゲートレベルの網表を使用。合成ツールの最適化バグ等を確認。|
| Post-Synthesis Timing          | 論理合成後     | 論理素子の推定遅延を含めても動作するか         | 素子ごとの推定遅延を考慮。配置前のタイミング問題の予測。  |
| Post-Implementation Functional | 配置配線後     | 最終的な配置において論理機能が維持されているか | 実チップ上の配置・配線後の接続情報に基づいた機能検証。    |
| Post-Implementation Timing     | 配置配線後     | 実機の動作に最も近いタイミング検証             | 配線遅延（SDF）を全て含む。最終的な動作保証用。          |


## 3. シミュレーション実行手順

### 3.1 Behavioral Simulation（論理検証）

RTLソースを直接シミュレーションする手法。高速であり、論理バグの早期発見に適している。

#### 方法A：TCLコマンドによる実行

1. プロジェクト作成     ：`source mcdma_sg_fft.tcl`
2. シミュレーション設定 ：
    * `create_fileset -simset {name}` でfileset作成。
    * `add_files` でテストベンチ（.sv）とデータ（.mem）を追加。
    * `set_property top` でトップモジュールを指定。
    * `generate_target Simulation` でBDのモデルを生成。
3. 実行                 ：`launch_simulation -simset sim_ml_pipe`

#### 方法B：GUI操作による実行

1. Sources → Add Sources を選択。
2. Add or create simulation sources を指定。
3. テストベンチファイルを追加。
4. 追加したファイルを右クリック → Set as Top（太字＋アイコン表示を確認）。
5. Run Simulation → Run Behavioral Simulation を実行。


### 3.2 Post-Implementation Timing Simulation（タイミング検証）

配置配線後のネットリストとSDF（遅延情報）を使用する。実チップに極めて近い動作検証が可能。

#### 方法A：TCLコマンドによる実行

1. 合成・実装       ：`launch_runs impl_1` を実行し、完了を待機。
2. 環境設定         ：fileset作成、ファイル追加、トップ指定を行う。
3. ネットリスト生成 ：実装デザインを開き（`open_run impl_1`）、`write_verilog -mode timesim` でSDF注釈付きネットリストを出力。
4. SDF生成          ：`write_sdf -file {timing.sdf}` で遅延情報を出力。
5. 実行             ：`launch_simulation -mode post-implementation -type timing`

#### 方法B：GUI操作による実行

1. Run Synthesis および Run Implementation を順に完了させる。
2. Flow Navigator の SIMULATION を選択。
3. Run Post-Implementation Timing Simulation を実行。


## 4. SDFファイルとは

SDF（Standard Delay Format）は、合成・配置配線後の実際の遅延情報を記録したファイルであり、タイミングシミュレーションに不可欠な要素である。

### 4.1. 生成プロセス

1. 前提条件：Block Design → Synthesis → Implementation の順でフローを完了させる。
2. 生成方法：
    * TCL：`open_run impl_1` の後、`write_sdf` コマンドを実行。
    * GUI：実装デザインを開き、File → Export → Export Simulation Files から出力。


## 5. FPGA開発の推奨ステップ

### 5.1：論理検証（Behavioral Simulation）の完遂

まず論理バグがないことを完全に保証する。FPGAでのML処理結果が、Python等のモデルによる結果と（量子化誤差を除き）一致することを確認する。

### 5.2：タイミングレポートの精査

ImplementationでNegative値が出た場合、即座にシミュレーションを行うのではなく、レポートを精査する。

* WNS (Worst Negative Slack)：負値の場合、要求クロックに対して回路の計算が間に合っていない。
* セットアップ時間エラー    ：データ到着が遅れ、立ち上がりに間に合わず不定（X）や誤値を取り込む。
* ホールド時間エラー        ：データ変化が早すぎ、現在のデータが保持できずに不定（X）となる。

### 5.3：RTLレベルでの修正（パイプライン化）

タイミングエラーの主因は、1クロック内に複雑な論理を詰め込みすぎることにある。

* 対策  ：レジスタを挿入して処理を分割（パイプライン化）する。
* 再検証：修正後、必ずステップ5.1（論理検証）に戻り、機能が損なわれていないか再確認する。

### 5.4：Post-Implementation Simulation（必要な場合のみ）

物理遅延を含めた最終確認。レポートが合格（Positive）であれば省略されることも多いが、実機で発生する稀なデータ化け等の原因究明には不可欠である。
