# --- Path Settings ---
BASE_DIR = Path(__file__).resolve().parent.parent # プロジェクトルート
DATA_DIR = BASE_DIR / "data"

# 中間生成・結果用パス
OUTPUT_MAP = {
    "fpga": DATA_DIR / "fpgasim_output" / "sim_output.mem",
    "ml":   DATA_DIR / "generated" / "ml_calc_result.txt",
    "res_t": DATA_DIR / "result" / "comp_result.txt",
    "res_i": DATA_DIR / "result" / "comp_result.png",
}

# 必要なディレクトリを自動生成
for p in OUTPUT_MAP.values():
    p.parent.mkdir(parents=True, exist_ok=True)
