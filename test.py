# --- 1. Load Keras model ---
print(f"\n[1] Loading Keras model: {FILE_MAP['model']}")
if not FILE_MAP['model'].exists():
    print(f"    [ERROR] Model file not found: {FILE_MAP['model']}")
    return

model = load_model(FILE_MAP['model'], compile=False)
model.summary()

# ... (中略) ...

# --- 2. Load preprocessed data ---
print(f"\n[2] Loading preprocessed data: {FILE_MAP['in']}")
if not FILE_MAP['in'].exists():
    print(f"    [ERROR] Input file not found: {FILE_MAP['in']}")
    print(f"    Run 01_preprocessor.py first.")
    return

raw_int = []
with open(FILE_MAP['in']) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('//') and not line.startswith('#'):
            raw_int.append(to_signed16(int(line, 16)))
