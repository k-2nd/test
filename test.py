import re
import struct
import matplotlib.pyplot as plt

def parse_bram_hex(file_path):
    """
    短い方のファイル (layer11_2bias.txt) をパースする。
    1ワード4バイト、リトルエンディアン、Q10.5として変換。
    """
    values = []
    with open(file_path, 'r') as f:
        for line in f:
            # [00] などのインデックスを除去し、ヘキサ文字列のみ抽出
            match = re.search(r'\]\s*([0-9a-fA-F]+)', line)
            if not match:
                continue
            
            hex_str = match.group(1)
            # 4バイト(8文字)ごとに区切って処理
            for i in range(0, len(hex_str), 8):
                word_hex = hex_str[i:i+8]
                if len(word_hex) < 8:
                    continue
                
                # リトルエンディアンとしてバイト列に変換し、等価な符号付き32bit整数として解釈
                byte_data = bytes.fromhex(word_hex)
                # 'I' はリトルエンディアン32bit(無符号)、'i'は符号付き
                val_int = struct.unpack('<i', byte_data)[0]
                
                # Q10.5 変換 (32.0 で割る)
                val_float = val_int / 32.0
                values.append(val_float)
    
    return values[:128]  # 念のため128個に制限

def parse_emulator_float(file_path, section_name="[Layer11_output2]"):
    """
    長い方のファイル (mlp_emulator_result.txt) をパースする。
    指定したセクションの [Float] 以下の値を抽出。
    """
    values = []
    found_section = False
    in_float_block = False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if section_name in line:
                found_section = True
                continue
            if found_section and "[Float]" in line:
                in_float_block = True
                continue
            if in_float_block and "[" in line and "[Float]" not in line:
                # 次のセクション（例: [Hex]）が来たら終了
                break
            
            if in_float_block and line:
                # パイプ | や空白で分割して数値化
                parts = line.split('|')
                for p in parts:
                    p = p.strip()
                    if p:
                        try:
                            values.append(float(p))
                        except ValueError:
                            continue
    
    return values[:128]

def plot_comparison(bram_data, emu_data):
    """
    折れ線グラフで比較表示
    """
    plt.figure(figsize=(12, 6))
    plt.plot(bram_data, label='BRAM (Simulation/Q10.5)', marker='o', markersize=3, alpha=0.8)
    plt.plot(emu_data, label='Emulator (Float)', linestyle='--', alpha=0.8)
    
    plt.title('Comparison: BRAM Dump vs Emulator Output')
    plt.xlabel('Index')
    plt.ylabel('Value')
    plt.grid(True, which='both', linestyle='--', alpha=0.5)
    plt.legend()
    
    plt.tight_layout()
    plt.show()

# --- 実行セクション ---
# ファイル名は実際の環境に合わせて変更してください
bram_file = 'layer11_2bias.txt'
emu_file = 'mlp_emulator_result.txt'

try:
    bram_vals = parse_bram_hex(bram_file)
    emu_vals = parse_emulator_float(emu_file)

    print(f"BRAMデータ数: {len(bram_vals)}")
    print(f"Emulatorデータ数: {len(emu_vals)}")

    if len(bram_vals) > 0 and len(emu_vals) > 0:
        plot_comparison(bram_vals, emu_vals)
    else:
        print("エラー: データが正しく読み込めませんでした。ファイルパスやフォーマットを確認してください。")

except Exception as e:
    print(f"実行エラー: {e}")
