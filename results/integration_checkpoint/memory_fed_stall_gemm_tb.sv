`timescale 1ns/1ps

module memory_fed_stall_gemm_tb;
    localparam integer N = 2;
    localparam integer ENQ_WIDTH = 16;
    localparam integer ADDR_WIDTH = 13;
    localparam integer TAG_WIDTH = 8;

    logic clk = 0, rst = 1;
    logic [ENQ_WIDTH-1:0] req_valid;
    logic [2:0] req_bank [ENQ_WIDTH];
    logic [ENQ_WIDTH*ADDR_WIDTH-1:0] req_addr;
    logic [ENQ_WIDTH*TAG_WIDTH-1:0] req_tag;

    wire [7:0] rsp_valid;
    wire [63:0] rsp_data;
    wire [63:0] rsp_tag;
    wire overflow;

    logic map_is_A;
    logic [7:0] map_row, map_index;
    logic [15:0] map_K, map_N;
    wire [2:0] map_bank;
    wire [12:0] map_local_addr;

    logic signed [7:0] A [N][N];
    logic signed [7:0] B [N][N];
    logic got_A [N][N], got_B [N][N];
    integer C_ref [N][N];

    logic signed [7:0] a_in [N], b_in [N];
    logic a_valid_in [N], b_valid_in [N];
    logic advance;
    wire signed [31:0] c_out [N][N];
    wire a_valid_out [N][N], b_valid_out [N][N];

    integer requests_issued = 0;
    integer responses_received = 0;
    integer total_cycles = 0;
    integer stall_cycles = 0;
    integer errors = 0;
    integer i, j, k, lane, tag, rb, rt, rr, rc;
    integer expected, all_ready, timeout_count;

    bank_mapper #(.BANK_POLICY(0)) mapper (
        .is_A(map_is_A), .row(map_row), .index(map_index),
        .K(map_K), .N(map_N),
        .bank(map_bank), .local_addr(map_local_addr)
    );

    banked_sram #(
        .NUM_BANKS(8), .BANK_SIZE(8192),
        .ADDR_WIDTH(ADDR_WIDTH), .TAG_WIDTH(TAG_WIDTH),
        .ENQ_WIDTH(ENQ_WIDTH), .FIFO_DEPTH(32)
    ) memory (
        .clk(clk), .rst(rst),
        .req_valid(req_valid), .req_bank(req_bank),
        .req_addr(req_addr), .req_tag(req_tag),
        .rsp_valid(rsp_valid), .rsp_data(rsp_data),
        .rsp_tag(rsp_tag), .overflow(overflow)
    );

    systolic_array_stall #(.N(N), .DATA_WIDTH(8), .ACC_WIDTH(32)) dut (
        .clk(clk), .rst(rst), .advance(advance),
        .a_in(a_in), .b_in(b_in),
        .a_valid_in(a_valid_in), .b_valid_in(b_valid_in),
        .c_out(c_out),
        .a_valid_out(a_valid_out), .b_valid_out(b_valid_out)
    );

    always #5 clk = ~clk;

    // Capture all bank responses at the falling edge.
    // Tags 0..3 are A; tags 4..7 are B.
    always @(negedge clk) begin
        if (!rst) begin
            for (rb = 0; rb < 8; rb = rb + 1) begin
                if (rsp_valid[rb]) begin
                    rt = rsp_tag[rb*TAG_WIDTH +: TAG_WIDTH];

                    if (rt < 4) begin
                        rr = rt / N;
                        rc = rt % N;
                        A[rr][rc] = $signed(rsp_data[rb*8 +: 8]);
                        got_A[rr][rc] = 1;
                    end else if (rt < 8) begin
                        rr = (rt-4) / N;
                        rc = (rt-4) % N;
                        B[rr][rc] = $signed(rsp_data[rb*8 +: 8]);
                        got_B[rr][rc] = 1;
                    end else begin
                        $fatal(1, "Unexpected response tag %0d", rt);
                    end

                    responses_received = responses_received + 1;
                end
            end
        end
    end

    // Issue one mapped SRAM read. Requests use lane 0.
    task automatic issue_read(
        input logic operand_a,
        input integer row_i,
        input integer col_i,
        input integer tag_i
    );
        integer bank_i, addr_i;
        begin
            @(negedge clk);
            map_is_A = operand_a;
            map_row = row_i;
            map_index = col_i;
            map_K = N;
            map_N = N;
            #1;
            bank_i = map_bank;
            addr_i = map_local_addr;

            req_valid = '0;
            req_addr = '0;
            req_tag = '0;
            req_bank[0] = bank_i;
            req_addr[0 +: ADDR_WIDTH] = addr_i;
            req_tag[0 +: TAG_WIDTH] = tag_i;
            req_valid[0] = 1'b1;

            @(negedge clk);
            req_valid[0] = 1'b0;
            requests_issued = requests_issued + 1;
        end
    endtask

    // Wait for actual SRAM response flags, with a timeout.
    task automatic wait_for_all_operands;
        integer ready;
        begin
            timeout_count = 0;
            ready = 0;
            while (!ready) begin
                @(negedge clk);
                total_cycles = total_cycles + 1;
                ready = 1;
                for (integer x = 0; x < N; x = x + 1)
                    for (integer y = 0; y < N; y = y + 1)
                        if (!got_A[x][y] || !got_B[x][y])
                            ready = 0;

                if (!ready)
                    stall_cycles = stall_cycles + 1;
                if (overflow)
                    $fatal(1, "SRAM FIFO overflow");
                timeout_count = timeout_count + 1;
                if (timeout_count > 200)
                    $fatal(1, "Timed out waiting for operand responses");
            end
        end
    endtask

    initial begin
        req_valid = '0;
        req_addr = '0;
        req_tag = '0;
        map_is_A = 0;
        map_row = 0;
        map_index = 0;
        map_K = N;
        map_N = N;
        advance = 1;

        for (i = 0; i < ENQ_WIDTH; i = i + 1)
            req_bank[i] = 0;

        for (i = 0; i < N; i = i + 1) begin
            a_in[i] = 0;
            b_in[i] = 0;
            a_valid_in[i] = 0;
            b_valid_in[i] = 0;
            for (j = 0; j < N; j = j + 1) begin
                A[i][j] = 0;
                B[i][j] = 0;
                got_A[i][j] = 0;
                got_B[i][j] = 0;
                C_ref[i][j] = 0;
            end
        end

        repeat (2) @(negedge clk);

        // Reset matrix values and expected outputs.
        A[0][0] = 1; A[0][1] = 2;
        A[1][0] = 3; A[1][1] = 4;
        B[0][0] = 5; B[0][1] = 6;
        B[1][0] = 7; B[1][1] = 8;

        for (i = 0; i < N; i = i + 1)
            for (j = 0; j < N; j = j + 1) begin
                C_ref[i][j] = 0;
                for (k = 0; k < N; k = k + 1)
                    C_ref[i][j] = C_ref[i][j] +
                                  A[i][k] * B[k][j];
            end

        // Policy-0 physical SRAM layout: bank = address % 8,
        // local address = address / 8.
        for (i = 0; i < N; i = i + 1)
            for (j = 0; j < N; j = j + 1) begin
                memory.mem[(i*N+j)%8][(i*N+j)/8] = A[i][j];
                memory.mem[(32768+i*N+j)%8][(32768+i*N+j)/8] = B[i][j];
            end

        rst = 0;
        $display("Memory-fed stall-aware GEMM: 2x2, policy 0");

        // Fetch all operands through the mapper and real SRAM interface.
        for (i = 0; i < N; i = i + 1)
            for (j = 0; j < N; j = j + 1)
                issue_read(1'b1, i, j, i*N+j);

        for (i = 0; i < N; i = i + 1)
            for (j = 0; j < N; j = j + 1)
                issue_read(1'b0, i, j, 4+i*N+j);

        wait_for_all_operands();

        if (responses_received != 8)
            $fatal(1, "Expected 8 SRAM responses, got %0d",
                   responses_received);

        // Drive the complete skewed systolic wavefront.
        // For an N x N array, inject inputs over 2*N-1 cycles.
        // Row i receives A[i][t-i]; column j receives B[t-j][j].
        for (integer t = 0; t < 2*N-1; t = t + 1) begin
            @(negedge clk);

            advance = 1;

            for (i = 0; i < N; i = i + 1) begin
                if ((t >= i) && ((t-i) < N)) begin
                    a_in[i] = A[i][t-i];
                    a_valid_in[i] = 1;
                end else begin
                    a_in[i] = 0;
                    a_valid_in[i] = 0;
                end
            end

            for (j = 0; j < N; j = j + 1) begin
                if ((t >= j) && ((t-j) < N)) begin
                    b_in[j] = B[t-j][j];
                    b_valid_in[j] = 1;
                end else begin
                    b_in[j] = 0;
                    b_valid_in[j] = 0;
                end
            end

            total_cycles = total_cycles + 1;
        end

        // Allow the final wavefront to reach the next rising edge.
        @(negedge clk);

        // Flush the remaining wavefront through the array.
        for (i = 0; i < N; i = i + 1) begin
            a_in[i] = 0;
            b_in[i] = 0;
            a_valid_in[i] = 0;
            b_valid_in[i] = 0;
        end
        repeat (N+2) begin
            @(negedge clk);
            total_cycles = total_cycles + 1;
        end

        for (i = 0; i < N; i = i + 1)
            for (j = 0; j < N; j = j + 1) begin
                expected = C_ref[i][j];
                $display("C[%0d][%0d]: expected=%0d actual=%0d",
                         i, j, expected, $signed(c_out[i][j]));
                if ($signed(c_out[i][j]) !== expected)
                    errors = errors + 1;
            end

        $display("Requests issued: %0d", requests_issued);
        $display("Responses received: %0d", responses_received);
        $display("Measured post-fetch compute/flush cycles: %0d",
                 total_cycles);
        $display("Operand-wait/stall counter: %0d", stall_cycles);

        if (errors != 0)
            $fatal(1, "FAIL: %0d output mismatches", errors);

        $display("PASS: memory-fed stall-aware 2x2 GEMM");
        $finish;
    end
endmodule
