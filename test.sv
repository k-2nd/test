    always_comb begin
        if (axi_read_addr >= DDR_MODEL_BASE) begin
            mem_index = (axi_read_addr - DDR_MODEL_BASE) >> 5;
        end else begin
            // シミュレーション実行時のみエラーメッセージを表示して停止
            // synthesis translate_off
            $error("[AXI_RD] CRITICAL: Invalid access address 0x%h. Address is below DDR_MODEL_BASE.", axi_read_addr);
            $fatal(1, "Out of range address detected in always_comb.");
            // synthesis translate_on
            
            mem_index = '0; // 文法上の代入（fatalで止まるため実際には通りません）
        end
    end
