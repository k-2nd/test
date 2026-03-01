class MLCalculator:
    def __init__(self, file_map=None):
        self.file_map = file_map
        # デバッグ用出力ファイルがあれば削除しておく処理
        # FILE_MAP['out_t'] (旧 OUTPUT_DEBUG_TXT) を使用
        if self.file_map['out_t'].exists():
            self.file_map['out_t'].unlink() # unlink() はファイルの削除

    def output_result(self, phase, data):
        """Output intermediate layer result."""
        output_result_to_file(self.file_map['out_t'], phase, data, mode='a')

    def output_final(self, data):
        """Output final layer result."""
        output_result_to_file(self.file_map['out_t'], LAST_LAYER_SECTION, data, mode='a')

    def load_data(self):
        norm_values = []
        # 入力データ: FILE_MAP['in'] (旧 INPUT_DATA)
        with open(self.file_map['in']) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('//'):
                    norm_values.append(to_signed16(int(line, 16)))
        
        self.norm_data_int = np.array(norm_values, dtype=np.int64)
        self.norm_data_float = self.norm_data_int.astype(np.float64)

        # DDRイメージ: FILE_MAP['ddr_img'] (旧 INPUT_DDR_IMAGE)
        ddr_file = self.file_map['ddr_img']
        self.input_ddr_words = load_ddr_image(ddr_file)

        # アドレスマップ: FILE_MAP['ddr_map'] (旧 INPUT_DDR_ADDRESS_MAP)
        addr_map_file = self.file_map['ddr_map']
        self.sections = parse_address_map(addr_map_file)
