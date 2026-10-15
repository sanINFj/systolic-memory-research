`timescale 1ns/1ps

module end_to_end_tb;

    localparam N = 8;
    localparam DATA_WIDTH = 8;
    localparam ACC_WIDTH = 32;
    localparam ENQ_WIDTH = 16;
    localparam ADDR_WIDTH = 13;
    localparam TAG_WIDTH = 8;

    logic clk, rst;

    logic [ENQ_WIDTH-1:0] req_valid;
    logic [2:0] req_bank [ENQ_WIDTH];
    logic [ENQ_WIDTH*ADDR_WIDTH-1:0] req_addr;
    logic [ENQ_WIDTH*TAG_WIDTH-1:0] req_tag;

    wire [7:0] rsp_valid;
    wire [8*8-1:0] rsp_data;
    wire [8*TAG_WIDTH-1:0] rsp_tag;
    wire overflow;

    logic map_is_A;
    logic [7:0] map_row, map_index;
    logic [15:0] map_K, map_N;
    wire [2:0] map_bank;
    wire [12:0] map_local_addr;

    logic signed [DATA_WIDTH-1:0] a_in [N];
    logic signed [DATA_WIDTH-1:0] b_in [N];
    wire signed [ACC_WIDTH-1:0] c_out [N][N];

    logic signed [7:0] A_buf [0:N-1][0:N-1];
    logic signed [7:0] B_buf [0:N-1][0:N-1];

    integer A_ref [0:N-1][0:N-1];
    integer B_ref [0:N-1][0:N-1];

    integer i, j, k, t;
    integer addr, expected, errors;
    integer bank_id, local_addr;
    integer tag_counter;
    logic [7:0] fetched;

    bank_mapper #(
        .BANK_POLICY(0)
    ) mapper (
        .is_A(map_is_A),
        .row(map_row),
        .index(map_index),
        .K( map_K),
        .N( map_N),
        .bank(map_bank),
        .local_addr(map_local_addr)
    );

    banked_sram #(
        .NUM_BANKS(8),
        .BANK_SIZE(8192),
        .ADDR_WIDTH(13),
        .TAG_WIDTH(8),
        .ENQ_WIDTH(16),
        .FIFO_DEPTH(32)
    ) memory (
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

    systolic_array #(
        .N(N),
        .DATA_WIDTH(DATA_WIDTH),
        .ACC_WIDTH(ACC_WIDTH)
    ) array_dut (
        .clk(clk),
        .rst(rst),
        .a_in(a_in),
        .b_in(b_in),
        .c_out(c_out)
    );

    always #5 clk = ~clk;

    // Fetch one byte using the real mapper and SRAM request/response path.
    task automatic fetch_byte(
        input logic operand_a,
        input integer row_i,
        input integer index_i,
        input integer tag_i,
        output logic [7:0] value
    );
        integer bk;
        integer la;
        begin
            map_is_A = operand_a;
            map_row = row_i;
            map_index = index_i;
            #1;

            bk = map_bank;
            la = map_local_addr;

            @(negedge clk);
            req_valid = '0;
            req_addr = '0;
            req_tag = '0;

            req_bank[0] = bk;
            req_addr[0 +: ADDR_WIDTH] = la;
            req_tag[0 +: TAG_WIDTH] = tag_i;
            req_valid[0] = 1'b1;

            // Request is accepted at the next rising edge.
            @(negedge clk);
            req_valid[0] = 1'b0;

            // Wait for the matching tagged response.
            while (
                !(rsp_valid[bk] &&
                  rsp_tag[bk*TAG_WIDTH +: TAG_WIDTH] == tag_i)
            ) begin
                @(negedge clk);
            end

            value = rsp_data[bk*8 +: 8];

            if (overflow)
                $fatal(1, "SRAM FIFO overflow during operand fetch");
        end
    endtask

    initial begin
        $dumpfile("results/end_to_end.vcd");
        $dumpvars(0, end_to_end_tb);

        clk = 0;
        rst = 1;
        req_valid = '0;
        req_addr = '0;
        req_tag = '0;

        map_is_A = 1'b0;
        map_row = 0;
        map_index = 0;
        map_K = N;
        map_N = N;

        for (i = 0; i < ENQ_WIDTH; i = i + 1)
            req_bank[i] = 0;

        for (i = 0; i < N; i = i + 1) begin
            a_in[i] = 0;
            b_in[i] = 0;

            for (j = 0; j < N; j = j + 1) begin
                A_ref[i][j] = i + j + 1;
                B_ref[i][j] = i + j + 1;
            end
        end

        // Preload the simulated SRAM with row-major A and B.
        // This is testbench initialization, not a hardware write port.
        for (i = 0; i < N; i = i + 1) begin
            for (j = 0; j < N; j = j + 1) begin
                addr = i*N + j;
                memory.mem[addr % 8][addr / 8] = A_ref[i][j];

                addr = 32768 + i*N + j;
                memory.mem[addr % 8][addr / 8] = B_ref[i][j];
            end
        end

        repeat (2) @(posedge clk);
        @(negedge clk);
        rst = 0;

        $display("");
        $display("==============================================");
        $display(" END-TO-END: BANKED SRAM -> 8x8 SYSTOLIC ARRAY");
        $display(" Bank policy: modulo | SRAM capacity: 64 KB");
        $display("==============================================");

        // Stage 1: read all operands through mapper + SRAM + FIFOs.
        tag_counter = 0;

        $display("[1/3] Fetching matrix A from banked SRAM...");
        for (i = 0; i < N; i = i + 1) begin
            for (j = 0; j < N; j = j + 1) begin
                fetch_byte(1'b1, i, j, tag_counter, fetched);
                A_buf[i][j] = fetched;
                tag_counter = tag_counter + 1;
            end
        end

        $display("[1/3] Fetching matrix B from banked SRAM...");
        for (i = 0; i < N; i = i + 1) begin
            for (j = 0; j < N; j = j + 1) begin
                fetch_byte(1'b0, i, j, tag_counter, fetched);
                B_buf[i][j] = fetched;
                tag_counter = tag_counter + 1;
            end
        end

        $display("[1/3] All 128 operand bytes returned successfully.");

        // Stage 2: inject skewed operands into the systolic array.
        $display("[2/3] Executing matrix multiplication...");

        for (t = 0; t <= 2*N-2; t = t + 1) begin
            @(negedge clk);

            for (i = 0; i < N; i = i + 1) begin
                if ((t >= i) && ((t-i) < N))
                    a_in[i] = A_buf[i][t-i];
                else
                    a_in[i] = 0;
            end

            for (j = 0; j < N; j = j + 1) begin
                if ((t >= j) && ((t-j) < N))
                    b_in[j] = B_buf[t-j][j];
                else
                    b_in[j] = 0;
            end
        end

        @(negedge clk);
        for (i = 0; i < N; i = i + 1) begin
            a_in[i] = 0;
            b_in[i] = 0;
        end

        // Allow the final wavefront to propagate through the array.
        repeat (N+2) @(posedge clk);
        #1;

        // Stage 3: check every output against reference GEMM.
        $display("[3/3] Checking all 64 output elements...");

        errors = 0;
        for (i = 0; i < N; i = i + 1) begin
            for (j = 0; j < N; j = j + 1) begin
                expected = 0;

                for (k = 0; k < N; k = k + 1)
                    expected = expected +
                               A_ref[i][k] * B_ref[k][j];

                if ($signed(c_out[i][j]) !== expected) begin
                    $display(
                        "FAIL C[%0d][%0d]: expected %0d, got %0d",
                        i, j, expected, $signed(c_out[i][j])
                    );
                    errors = errors + 1;
                end
            end
        end

        $display("");
        $display("Output matrix C:");
        for (i = 0; i < N; i = i + 1) begin
            for (j = 0; j < N; j = j + 1)
                $write("%0d ", $signed(c_out[i][j]));
            $display("");
        end

        if (errors == 0) begin
            $display("");
            $display("PASS: END-TO-END GEMM VERIFIED");
            $display("128 SRAM reads completed; 64/64 outputs match.");
        end
        else begin
            $display("FAIL: %0d output mismatches", errors);
            $fatal(1, "End-to-end verification failed");
        end

        $finish;
    end

endmodule
