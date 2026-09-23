`timescale 1ns/1ps

// ============================================================
// Banked SRAM Testbench
// ============================================================
//
// Tests:
//
//   1. One request to each of 8 banks.
//      Expected: all 8 banks can service in parallel.
//
//   2. Eight requests to bank 0.
//      Expected: requests are serialized by the bank FIFO.
//
// This test focuses on:
//
//   request routing
//   FIFO behavior
//   one-read-per-bank-per-cycle
//   response tags
//
// ============================================================

module banked_sram_tb;

    localparam NUM_BANKS = 8;
    localparam ENQ_WIDTH = 16;
    localparam ADDR_WIDTH = 13;
    localparam TAG_WIDTH = 8;

    logic clk;
    logic rst;

    // --------------------------------------------------------
    // Request interface
    // --------------------------------------------------------

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

    // --------------------------------------------------------
    // Response interface
    // --------------------------------------------------------

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

    // --------------------------------------------------------
    // DUT
    // --------------------------------------------------------

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

    // --------------------------------------------------------
    // Clock
    // --------------------------------------------------------

    initial begin

        clk = 1'b0;

        forever #5 clk = ~clk;

    end

    // --------------------------------------------------------
    // Clear request interface
    // --------------------------------------------------------

    task clear_requests;

        integer j;

        begin

            req_valid = '0;

            req_addr = '0;

            req_tag = '0;

            for (
                j = 0;
                j < ENQ_WIDTH;
                j = j + 1
            ) begin

                req_bank[j] = '0;

            end

        end

    endtask

    // --------------------------------------------------------
    // Main test
    // --------------------------------------------------------

    initial begin

        rst = 1'b1;

        clear_requests();

        #20;

        rst = 1'b0;

        // ====================================================
        // TEST 1
        //
        // One request to every bank.
        //
        // All eight banks should be able to service one
        // request in parallel.
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
            ] =
                8'h10 + i;

        end

        @(negedge clk);

        clear_requests();

        repeat (4)
            @(negedge clk);

        // ====================================================
        // TEST 2
        //
        // Eight requests all target bank 0.
        //
        // The FIFO must serialize them.
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
            ] =
                13'd100 + i;

            req_tag[
                i*TAG_WIDTH
                +:
                TAG_WIDTH
            ] =
                8'h20 + i;

        end

        @(negedge clk);

        clear_requests();

        repeat (12)
            @(negedge clk);

        // ====================================================
        // Result
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

    // --------------------------------------------------------
    // Response monitor
    // --------------------------------------------------------

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

            end

        end

    end

endmodule
