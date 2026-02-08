// --- モジュールの先頭付近に記述 ---
localparam string INPUT_FILE = "input/ml_input.mem";

// ... 中略 ...

initial begin
    // Initialize to zero first
    for (int i = 0; i < NUM_INPUT_LINES; i++) begin
        test_vectors[i] = 256'h0;
    end

    // くくりだした localparam を使用
    if ($fopen(INPUT_FILE, "r") != 0) begin
        $readmemh(INPUT_FILE, test_vectors);
        $display("[TB] Loaded: %s", INPUT_FILE);
    end else begin
        $display("[TB] ERROR: Test vector file not found!");
        $display("[TB] Expected: %s", INPUT_FILE);
        $fatal(1, "Critical failure: %s is required for simulation.", INPUT_FILE);
    end
end
