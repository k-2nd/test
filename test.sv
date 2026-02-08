    end else begin
        $display("[TB] ERROR: Test vector file not found!");
        $display("[TB] Expected: input/ml_input.mem");
        // ダミーデータ生成を削除し、シミュレーションを強制終了させる
        $fatal(1, "Critical failure: ml_input.mem is required for simulation.");
    end
