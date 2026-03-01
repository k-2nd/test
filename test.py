class MLPreprocessor:
    def __init__(self, file_map):
        self.file_map = file_map
        # BRAM初期化などはそのまま
        self.bram0 = np.zeros(8192, dtype=np.uint8)
        self.bram2 = np.zeros(8192, dtype=np.uint8)
        self.input_vector = []

    def load_input_data(self):
        """画像2枚目のロジック"""
        target = self.file_map["in"] # マップから取得
        
        if not target.exists():
            raise FileNotFoundError(f"Input file not found: {target}")

        self.input_vector = []
        with open(target, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith(('/', '#')): continue
                if len(line) == 64:
                    self.input_vector.append(int(line, 16))

    def save_results(self):
        """画像3枚目のロジック"""
        target = self.file_map["out"]
        
        with open(target, 'w') as f:
            for i in range(96):
                addr = i * 2
                val = int(self.bram2[addr]) | (int(self.bram2[addr+1]) << 8)
                f.write(f"{val:04x}\n")
        
        # デバッグモードならトレースも保存
        if globals().get('DEBUG_MODE'): # DEBUG_MODEが定義されていれば
            self.save_trace_data()

    def save_trace_data(self):
        """画像3枚目の詳細ログ出力"""
        target = self.file_map["trace"]
        
        with open(target, 'w') as f:
            # 元のコードにある複雑なヘッダー・ログ出力ロジックをここに
            f.write(f"--- Trace Data: {target.name} ---\n")
            # ... (中略) ...
