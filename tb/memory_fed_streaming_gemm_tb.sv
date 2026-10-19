`timescale 1ns/1ps

module memory_fed_streaming_gemm_tb;
    localparam integer N = 2;
    localparam integer ENQ_WIDTH = 16;
    localparam integer ADDR_WIDTH = 13;
    localparam integer TAG_WIDTH = 8;

    logic clk = 0, rst = 1;
    logic [ENQ_WIDTH-1:0] req_valid = '0;
    logic [2:0] req_bank [ENQ_WIDTH];
    logic [ENQ_WIDTH*ADDR_WIDTH-1:0] req_addr = '0;
    logic [ENQ_WIDTH*TAG_WIDTH-1:0] req_tag = '0;

    wire [7:0] rsp_valid;
    wire [63:0] rsp_data, rsp_tag;
    wire overflow;

    logic map_is_A = 0;
    logic [7:0] map_row = 0, map_index = 0;
    logic [15:0] map_K = N, map_N = N;
    wire [2:0] map_bank;
    wire [12:0] map_local_addr;

    logic signed [7:0] A [N][N], B [N][N];
    logic got_A [N][N], got_B [N][N];
    integer C_ref [N][N];

    logic signed [7:0] a_in [N], b_in [N];
    logic a_valid_in [N], b_valid_in [N];
    logic advance = 1;
    wire signed [31:0] c_out [N][N];
    wire a_valid_out [N][N], b_valid_out [N][N];

    integer requests_issued = 0, responses_received = 0;
    integer total_cycles = 0, stall_cycles = 0, errors = 0;
    integer i, j, k, rb, rt, rr, rc, expected;
    integer timeout_count, issue_row, issue_col, issue_is_A;

    bank_mapper #(.BANK_POLICY(0)) mapper (
        .is_A(map_is_A), .row(map_row), .index(map_index),
        .K(map_K), .N(map_N), .bank(map_bank),
        .local_addr(map_local_addr)
    );

    banked_sram #(
        .NUM_BANKS(8), .BANK_SIZE(8192),
        .ADDR_WIDTH(ADDR_WIDTH), .TAG_WIDTH(TAG_WIDTH),
        .ENQ_WIDTH(ENQ_WIDTH), .FIFO_DEPTH(32)
    ) memory (
        .clk(clk), .rst(rst), .req_valid(req_valid),
        .req_bank(req_bank), .req_addr(req_addr), .req_tag(req_tag),
        .rsp_valid(rsp_valid), .rsp_data(rsp_data),
        .rsp_tag(rsp_tag), .overflow(overflow)
    );

    systolic_array_stall #(.N(N), .DATA_WIDTH(8), .ACC_WIDTH(32)) dut (
        .clk(clk), .rst(rst), .advance(advance),
        .a_in(a_in), .b_in(b_in),
        .a_valid_in(a_valid_in), .b_valid_in(b_valid_in),
        .c_out(c_out), .a_valid_out(a_valid_out),
        .b_valid_out(b_valid_out)
    );

    always #5 clk = ~clk;

    // Responses are captured on falling edges, after SRAM registers them.
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

    // Issue one read through the real mapper and SRAM.
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

    // Wait for a particular operand, while the array remains held.
    task automatic wait_for_operand(
        input logic operand_a,
        input integer row_i,
        input integer col_i
    );
        integer waited;
        begin
            waited = 0;
            while (operand_a ? !got_A[row_i][col_i] :
                               !got_B[row_i][col_i]) begin
                @(negedge clk);
                total_cycles = total_cycles + 1;
                stall_cycles = stall_cycles + 1;
                waited = waited + 1;
                if (overflow) $fatal(1, "SRAM FIFO overflow");
                if (waited > 100)
                    $fatal(1, "Timeout waiting for operand A=%0d row=%0d col=%0d",
                           operand_a, row_i, col_i);
            end
        end
    endtask

    // Send one operand at a time, waiting for its real response.
    // This deliberately serial baseline validates the live memory/compute
    // handshake before introducing parallel requests and bank conflicts.
    task automatic fetch_operand(
        input logic operand_a,
        input integer row_i,
        input integer col_i,
        input integer tag_i
    );
        begin
            issue_read(operand_a, row_i, col_i, tag_i);
            wait_for_operand(operand_a, row_i, col_i);
        end
    endtask

    initial begin
        for (i = 0; i < ENQ_WIDTH; i = i + 1) req_bank[i] = 0;
        for (i = 0; i < N; i = i + 1) begin
            a_in[i] = 0; b_in[i] = 0;
            a_valid_in[i] = 0; b_valid_in[i] = 0;
            for (j = 0; j < N; j = j + 1) begin
                A[i][j] = 0; B[i][j] = 0;
                got_A[i][j] = 0; got_B[i][j] = 0;
                C_ref[i][j] = 0;
            end
        end

        repeat (2) @(negedge clk);

        // Reference matrices. The SRAM is populated in policy-0 layout.
        A[0][0] = 1; A[0][1] = 2;
        A[1][0] = 3; A[1][1] = 4;
        B[0][0] = 5; B[0][1] = 6;
        B[1][0] = 7; B[1][1] = 8;

        for (i = 0; i < N; i = i + 1)
            for (j = 0; j < N; j = j + 1) begin
                C_ref[i][j] = 0;
                for (k = 0; k < N; k = k + 1)
                    C_ref[i][j] = C_ref[i][j] + A[i][k] * B[k][j];
                memory.mem[(i*N+j)%8][(i*N+j)/8] = A[i][j];
                memory.mem[(32768+i*N+j)%8][(32768+i*N+j)/8] = B[i][j];
            end

        rst = 0;
        $display("Streaming memory-fed GEMM: %0dx%0d, policy 0", N, N);

        // Use the systolic wavefront schedule:
        // A[i][k] enters at t=i+k; B[k][j] enters at t=k+j.
        // Fetch only the operands needed for the current wavefront.
        // The array is held while each required SRAM response arrives.
        for (k = 0; k <= 2*N-2; k = k + 1) begin
            advance = 0;

            // Fetch A operands whose row and reduction index sum to t.
            for (i = 0; i < N; i = i + 1) begin
                j = k - i;
                if (j >= 0 && j < N)
                    fetch_operand(1'b1, i, j, i*N+j);
            end

            // Fetch B operands whose reduction index and column sum to t.
            for (j = 0; j < N; j = j + 1) begin
                i = k - j;
                if (i >= 0 && i < N)
                    fetch_operand(1'b0, i, j, 4+i*N+j);
            end

            // Inject this wavefront. Invalid lanes stay invalid.
            @(negedge clk);
            for (i = 0; i < N; i = i + 1) begin
                j = k - i;
                if (j >= 0 && j < N) begin
                    a_in[i] = A[i][j];
                    a_valid_in[i] = 1;
                end else begin
                    a_in[i] = 0;
                    a_valid_in[i] = 0;
                end
            end

            for (j = 0; j < N; j = j + 1) begin
                i = k - j;
                if (i >= 0 && i < N) begin
                    b_in[j] = B[i][j];
                    b_valid_in[j] = 1;
                end else begin
                    b_in[j] = 0;
                    b_valid_in[j] = 0;
                end
            end

            advance = 1;
            @(negedge clk);
            total_cycles = total_cycles + 1;

            advance = 0;
            for (i = 0; i < N; i = i + 1) begin
                a_in[i] = 0;
                b_in[i] = 0;
                a_valid_in[i] = 0;
                b_valid_in[i] = 0;
            end
        end

        // Flush the final registered wavefront through the array.
        advance = 1;
        repeat (N+2) begin
            @(negedge clk);
            total_cycles = total_cycles + 1;
        end
        advance = 0;

        for (i = 0; i < N; i = i + 1)
            for (j = 0; j < N; j = j + 1) begin
                expected = C_ref[i][j];
                $display("C[%0d][%0d]: expected=%0d actual=%0d",
                         i, j, expected, $signed(c_out[i][j]));
                if ($signed(c_out[i][j]) !== expected) errors = errors + 1;
            end

        $display("Requests issued: %0d", requests_issued);
        $display("Responses received: %0d", responses_received);
        $display("Measured cycles (wait + compute/flush): %0d", total_cycles);
        $display("Operand-wait/stall cycles: %0d", stall_cycles);

        if (responses_received != 8)
            $fatal(1, "Expected 8 responses, got %0d", responses_received);
        if (errors != 0)
            $fatal(1, "FAIL: %0d output mismatches", errors);

        $display("PASS: streaming memory-fed GEMM baseline");
        $finish;
    end
endmodule
