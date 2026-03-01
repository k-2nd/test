class MLPreprocessor:
    def __init__(self, file_map=None):
        # 外部からマップを渡せるようにすると、テスト時などにパスを差し替えやすくなります
        self.file_map = file_map
        # BRAM array 等の初期化（省略）
        self.input_vector = []

    def load_input_data(self, key="in"):
        """
        FILE_MAP のキーを指定してデータを読み込む
        """
        # マップから Path オブジェクトを取得
        if self.file_map is None or key not in self.file_map:
            raise ValueError(f"Key '{key}' not found in file map.")
        
        input_file = self.file_map[key]

        # 1. 存在チェック (Pathオブジェクトのメソッド)
        if not input_file.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")

        # 2. 読み込み (Pathオブジェクトをそのまま open に渡せる)
        self.input_vector = []
        with open(input_file, 'r') as f:
            for line in f:
                line = line.strip()
                # コメント行や空行をスキップ
                if not line or line.startswith(('/', '#')):
                    continue
                # 16進数文字列を数値に変換
                if len(line) == 64:
                    self.input_vector.append(int(line, 16))
        
        print(f"Loaded {len(self.input_vector)} lines from {input_file.name}")


# 1. まずマップを定義（画像2枚目の内容）
FILE_MAP = {
    "in":  DATA_DIR / "input" / "test_input.mem",
    "out": DATA_DIR / "generated" / "preprocessed_data.mem",
}

# 2. クラスにマップを渡してインスタンス化
preprocessor = MLPreprocessor(file_map=FILE_MAP)

# 3. 実行
preprocessor.load_input_data("in")
