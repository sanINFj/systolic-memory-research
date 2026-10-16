`timescale 1ns/1ps

module banked_sram_concurrent_tb;

    localparam integer NUM_BANKS = 8;
    localparam integer BANK_SIZE = 8192;
    localparam integer NUM_REQS = 16;
    localparam integer ADDR_WIDTH = 13;
    localparam integer TAG_WIDTH = 8;

    logic clk = 0;
    logic rst = 1;

    logic [NUM_REQS-1:0] req_valid = '0;
    logic [2:0] req_bank [NUM_REQS];
    logic [NUM_REQS*ADDR_WIDTH-1:0] req_addr = '0;
    logic [NUM_REQS*TAG_WIDTH-1:0] req_tag = '0;

    wire [NUM_BANKS-1:0] rsp_valid;
    wire [NUM_BANKS*8-1:0] rsp_data;
    wire [NUM_BANKS*TAG_WIDTH-1:0] rsp_tag;
    wire overflow;

    integer i;
    integer b;
    integer tag_id;
    integer cycle_count = 0;
    integer response_count = 0;
    integer timeout_count = 0;
    logic [NUM_REQS-1:0] seen_tags = '0;

    always #5 clk = ~clk;

    banked_sram #(
        .NUM_BANKS(NUM_BANKS),
        .BANK_SIZE(BANK_SIZE),
        .ADDR_WIDTH(ADDR_WIDTH),
        .TAG_WIDTH(TAG_WIDTH),
        .ENQ_WIDTH(NUM_REQS),
        .FIFO_DEPTH(32)
    ) dut (
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

    initial begin
        $dumpfile("results/banked_sram_concurrent.vcd");
        $dumpvars(0, banked_sram_concurrent_tb);

        for (i = 0; i < NUM_REQS; i = i + 1)
            req_bank[i] = 0;

        repeat (3) @(negedge clk);
        rst = 0;

        // Two requests per bank, with distinct tags.
        // Both requests to each bank read the same initialized byte.
        for (i = 0; i < NUM_REQS; i = i + 1) begin
            b = i % NUM_BANKS;
            req_valid[i] = 1'b1;
            req_bank[i] = b;
            req_addr[i*ADDR_WIDTH +: ADDR_WIDTH] = b;
            req_tag[i*TAG_WIDTH +: TAG_WIDTH] = i;
        end

        // Keep requests stable through the next rising edge.
        @(posedge clk);
        @(negedge clk);
        req_valid = '0;

        while ((response_count < NUM_REQS) &&
               (timeout_count < 100)) begin
            @(negedge clk);
            cycle_count = cycle_count + 1;

            for (i = 0; i < NUM_BANKS; i = i + 1) begin
                if (rsp_valid[i]) begin
                    tag_id = rsp_tag[i*TAG_WIDTH +: TAG_WIDTH];

                    if (tag_id >= NUM_REQS) begin
                        $display("FAIL: invalid tag %0d", tag_id);
                        $fatal(1);
                    end

                    if (seen_tags[tag_id]) begin
                        $display("FAIL: duplicate tag %0d", tag_id);
                        $fatal(1);
                    end

                    if (rsp_data[i*8 +: 8] !==
                        (8'h40 + (tag_id % NUM_BANKS))) begin
                        $display("FAIL: tag %0d data mismatch: got %h expected %h",
                                 tag_id, rsp_data[i*8 +: 8],
                                 (8'h40 + (tag_id % NUM_BANKS)));
                        $fatal(1);
                    end

                    seen_tags[tag_id] = 1'b1;
                    response_count = response_count + 1;
                end
            end

            if (overflow) begin
                $display("FAIL: FIFO overflow asserted");
                $fatal(1);
            end

            timeout_count = timeout_count + 1;
        end

        if (response_count != NUM_REQS) begin
            $display("FAIL: got %0d/%0d responses",
                     response_count, NUM_REQS);
            $fatal(1);
        end

        $display("PASS: all %0d concurrent-request responses verified",
                 response_count);
        $display("Response collection window: %0d cycles", cycle_count);
        $display("This is a directed RTL test, not a GEMM benchmark.");
        $finish;
    end

    // Initialize known values after the DUT has been elaborated.
    initial begin
        #1;
        for (integer j = 0; j < NUM_BANKS; j = j + 1)
            dut.mem[j][j] = 8'h40 + j;
    end

    initial begin
        #2000;
        $display("FAIL: simulation timeout");
        $fatal(1);
    end

endmodule
