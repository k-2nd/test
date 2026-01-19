import re
import numpy as np

def parse_h_file_to_dict(file_path):
    """
    Cヘッダーファイルから配列名と数値リストを抽出する
    """
    params = {}
    
    # 正規表現のパターン:
    # s16 (配列名) [ (サイズ) ] = { (中身) };
    # ※改行を含めてマッチさせるために re.DOTALL を使用
    pattern = re.compile(r's16\s+(\w+)\[\d+\]\s*=\s*\{(.*?)\};', re.DOTALL)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        matches = pattern.findall(content)
        
        for name, values_str in matches:
            # カンマ区切りの文字列を数値リストに変換（改行や空白を除去）
            values = [int(v.strip()) for v in values_str.split(',') if v.strip()]
            params[name] = np.array(values, dtype=np.int16)
            print(f"Parsed {name}: {len(values)} elements")
            
    except FileNotFoundError:
        print(f"Error: {file_path} が見つかりません。")
        
    return params

# --- 使用例 ---
# params = parse_h_file_to_dict('model1.h')
# weight_layer1 = params.get('weight_layer1')
