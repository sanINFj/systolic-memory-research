`timescale 1ns/1ps

module banked_sram_tb;

    localparam NUM_BANKS  = 8;
    localparam ENQ_WIDTH  = 16;
    localparam ADDR_WIDTH = 13;
    localparam TAG_WIDTH  = 8;

    logic clk;
    logic rst;

    logic [ENQ_WIDTH-1:0]
        req_valid;

    logic [2:0]
        req_bank [ENQ_WIDTH];

    logic [
        ENQ_WIDTH*ADDR_WIDTH-1:0
    ]
        req_addr;

    logic [
        ENQ_WIDTH*TAG_WIDTH-1:0
    ]
        req_tag;

    logic [NUM_BANKS-1:0]
        rsp_valid;

    logic [
        NUM_BANKS*8-1:0
    ]
        rsp_data;

    logic [
        NUM_BANKS*TAG_WIDTH-1:0
    ]
        rsp_tag;

    logic overflow;

    integer i;


    // ========================================================
    // DUT
    // ========================================================

    banked_sram dut (
        .clk(clk),
        .rst(rst),

        .req_valid(req_valid),
        .req_bank(req_bank),
        .req_addr(req_addr),
        .req_tag(req_tag),

        .rsp_valid(rsp_valid),
        .rsp_data(rsp_data),
        .rsp_tag(rsp_tag),

        .overflow(overflow)
    );


    // ========================================================
    // CLOCK
    // ========================================================

    initial begin
        clk = 1'b0;

        forever #5 clk = ~clk;
    end


    // ========================================================
    // CLEAR REQUESTS
    // ========================================================

    task clear_requests;

        integer j;

        begin

            req_valid = '0;
            req_addr  = '0;
            req_tag   = '0;

            for (
                j = 0;
                j < ENQ_WIDTH;
                j = j + 1
            ) begin

                req_bank[j] = '0;

            end

        end

    endtask


    // ========================================================
    // RESPONSE CHECKER
    // ========================================================

    always @(posedge clk) begin

        for (
            i = 0;
            i < NUM_BANKS;
            i = i + 1
        ) begin

            if (rsp_valid[i]) begin

                $display(
                    "time=%0t bank=%0d tag=%0h data=%0h",
                    $time,
                    i,
                    rsp_tag[
                        i*TAG_WIDTH
                        +:
                        TAG_WIDTH
                    ],
                    rsp_data[
                        i*8
                        +:
                        8
                    ]
                );

                // ------------------------------------------------
                // TEST 1B DATA CHECK
                //
                // Expected:
                // bank 0 -> A0
                // bank 1 -> A1
                // ...
                // bank 7 -> A7
                // ------------------------------------------------

                if (
                    rsp_tag[
                        i*TAG_WIDTH
                        +:
                        TAG_WIDTH
                    ] >= 8'h30
                    &&
                    rsp_tag[
                        i*TAG_WIDTH
                        +:
                        TAG_WIDTH
                    ] <= 8'h37
                ) begin

                    if (
                        rsp_data[
                            i*8
                            +:
                            8
                        ]
                        !==
                        (8'hA0 + i)
                    ) begin

                        $display("");
                        $display(
                            "FAIL: SRAM data mismatch"
                        );

                        $display(
                            "bank=%0d expected=%0h got=%0h",
                            i,
                            8'hA0 + i,
                            rsp_data[
                                i*8
                                +:
                                8
                            ]
                        );

                        $finish;

                    end

                end

            end

        end

    end


    // ========================================================
    // TEST SEQUENCE
    // ========================================================

    initial begin

        // ----------------------------------------------------
        // INITIALIZATION
        // ----------------------------------------------------

        rst = 1'b1;

        clear_requests();


        // ----------------------------------------------------
        // INITIALIZE SRAM
        //
        // Known values allow us to verify that the request
        // actually reaches the correct SRAM bank/address.
        // ----------------------------------------------------

        dut.mem[0][0] = 8'hA0;
        dut.mem[1][1] = 8'hA1;
        dut.mem[2][2] = 8'hA2;
        dut.mem[3][3] = 8'hA3;
        dut.mem[4][4] = 8'hA4;
        dut.mem[5][5] = 8'hA5;
        dut.mem[6][6] = 8'hA6;
        dut.mem[7][7] = 8'hA7;


        // ----------------------------------------------------
        // RELEASE RESET
        // ----------------------------------------------------

        #20;

        rst = 1'b0;


        // ====================================================
        // TEST 1
        // One request per bank
        // ====================================================

        $display("");
        $display(
            "=============================================="
        );
        $display(
            "TEST 1: One request per bank"
        );
        $display(
            "=============================================="
        );

        @(negedge clk);

        for (
            i = 0;
            i < 8;
            i = i + 1
        ) begin

            req_valid[i] = 1'b1;

            req_bank[i] = i[2:0];

            req_addr[
                i*ADDR_WIDTH
                +:
                ADDR_WIDTH
            ] = i;

            req_tag[
                i*TAG_WIDTH
                +:
                TAG_WIDTH
            ] = 8'h10 + i;

        end


        @(negedge clk);

        clear_requests();


        repeat (4)
            @(negedge clk);


        // ====================================================
        // TEST 1B
        // Verify actual SRAM data
        // ====================================================

        $display("");
        $display(
            "=============================================="
        );
        $display(
            "TEST 1B: SRAM data correctness"
        );
        $display(
            "=============================================="
        );

        @(negedge clk);

        for (
            i = 0;
            i < 8;
            i = i + 1
        ) begin

            req_valid[i] = 1'b1;

            req_bank[i] = i[2:0];

            req_addr[
                i*ADDR_WIDTH
                +:
                ADDR_WIDTH
            ] = i;

            req_tag[
                i*TAG_WIDTH
                +:
                TAG_WIDTH
            ] = 8'h30 + i;

        end


        @(negedge clk);

        clear_requests();


        repeat (4)
            @(negedge clk);


        // ====================================================
        // TEST 2
        // Eight requests to one bank
        //
        // This verifies FIFO serialization.
        // ====================================================

        $display("");
        $display(
            "=============================================="
        );
        $display(
            "TEST 2: Eight requests to bank 0"
        );
        $display(
            "=============================================="
        );

        @(negedge clk);

        for (
            i = 0;
            i < 8;
            i = i + 1
        ) begin

            req_valid[i] = 1'b1;

            req_bank[i] = 3'd0;

            req_addr[
                i*ADDR_WIDTH
                +:
                ADDR_WIDTH
            ] = 13'd100 + i;

            req_tag[
                i*TAG_WIDTH
                +:
                TAG_WIDTH
            ] = 8'h20 + i;

        end


        @(negedge clk);

        clear_requests();


        repeat (12)
            @(negedge clk);


        // ====================================================
        // FINAL CHECK
        // ====================================================

        if (overflow) begin

            $display("");
            $display(
                "FAIL: FIFO overflow detected"
            );

        end
        else begin

            $display("");
            $display(
                "PASS: banked SRAM FIFO test completed"
            );

        end


        $finish;

    end

endmodule
