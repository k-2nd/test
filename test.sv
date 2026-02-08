    end else begin
        $display("[TB] ERROR: DDR weight file not found!");
        $display("[TB] Expected: input/model_ddr_image.mem");
        $fatal(1, "Simulation halted due to missing input file.");
    end
