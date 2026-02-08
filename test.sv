    // Create directory if not exists (Reset directory)
    initial begin
        // 一旦削除して、作り直す
        $system($sformatf("rm -rf %s %s %s", DIRNAME_RESULTS, DIRNAME_BRAM, DIRNAME_WB));
        $system($sformatf("mkdir -p %s %s %s", DIRNAME_RESULTS, DIRNAME_BRAM, DIRNAME_WB));
    end
