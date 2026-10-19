`timescale 1ns/1ps

module memory_fed_gemm_tb;

    localparam integer N = 8;
    localparam integer ENQ_WIDTH = 16;
    localparam integer ADDR_WIDTH = 13;
    localparam integer TAG_WIDTH = 8;
    localparam integer NUM_BANKS = 8;

    logic clk = 0;
    logic rst = 1;

    logic [ENQ_WIDTH-1:0] req_valid;
    logic [2:0] req_bank [ENQ_WIDTH];
    logic [ENQ_WIDTH*ADDR_WIDTH-1:0] req_addr;
    logic [ENQ_WIDTH*TAG_WIDTH-1:0] req_tag;

    wire [NUM_BANKS-1:0] rsp_valid;
    wire [NUM_BANKS*8-1:0] rsp_data;
    wire [NUM_BANKS*TAG_WIDTH-1:0] rsp_tag;
    wire overflow;

    logic map_is_A;
    logic [7:0] map_row, map_index;
    logic [15:0] map_K, map_N;
    wire [2:0] map_bank;
    wire [12:0] map_local_addr;

    logic signed [7:0] A [N][N];
    logic signed [7:0] B [N][N];
    integer C_ref [N][N];

    logic got_A [N][N];
    logic got_B [N][N];

    integer requests_issued;
    integer responses_received;
    integer compute_steps;
    integer memory_wait_cycles;
    integer errors;
    integer i, j, k, t, bank, tag;
    integer expected;
    integer total_cycles;
    integer cycles;
    integer pending_A, pending_B;
    integer next_k;
    integer all_ready;
    integer bk, la;

    bank_mapper #(.BANK_POLICY(0)) mapper (
        .is_A(map_is_A),
        .row(map_row),
        .index(map_index),
        .K(map_K),
        .N(map_N),
        .bank(map_bank),
        .local_addr(map_local_addr)
    );

    banked_sram #(
        .NUM_BANKS(NUM_BANKS),
        .BANK_SIZE(8192),
        .ADDR_WIDTH(ADDR_WIDTH),
        .TAG_WIDTH(TAG_WIDTH),
        .ENQ_WIDTH(ENQ_WIDTH),
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

    always #5 clk = ~clk;

    // Request one matrix operand using the actual mapper.
    task automatic issue_request(
        input logic operand_a,
        input integer row_i,
        input integer col_i,
        input integer tag_i
    );
        begin
            map_is_A = operand_a;
            map_row = row_i;
            map_index = col_i;
            map_K = N;
            map_N = N;
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

            @(negedge clk);
            req_valid[0] = 1'b0;
            requests_issued = requests_issued + 1;
        end
    endtask

    // Collect a response and decode its tag:
    // 0..63 = A[row][col], 64..127 = B[row][col].
    task automatic collect_responses;
        integer rb, rt, rr, rc;
        begin
            for (rb = 0; rb < NUM_BANKS; rb = rb + 1) begin
                if (rsp_valid[rb]) begin
                    rt = rsp_tag[rb*TAG_WIDTH +: TAG_WIDTH];

                    if (rt < 64) begin
                        rr = rt / N;
                        rc = rt % N;
                        A[rr][rc] = $signed(rsp_data[rb*8 +: 8]);
                        got_A[rr][rc] = 1;
                    end else if (rt < 128) begin
                        rr = (rt - 64) / N;
                        rc = (rt - 64) % N;
                        B[rr][rc] = $signed(rsp_data[rb*8 +: 8]);
                        got_B[rr][rc] = 1;
                    end else begin
                        $fatal(1, "Unexpected response tag %0d", rt);
                    end

                    responses_received = responses_received + 1;
                end
            end
        end
    endtask

    // Sample registered SRAM responses on every falling edge.
    // rsp_valid is produced on rising edges, so this avoids
    // missing one-cycle response pulses between testbench tasks.
    always @(negedge clk) begin
        if (!rst)
            collect_responses();
    end

    initial begin
        req_valid = '0;
        req_addr = '0;
        req_tag = '0;
        map_is_A = 0;
        map_row = 0;
        map_index = 0;
        map_K = N;
        map_N = N;

        requests_issued = 0;
        responses_received = 0;
        compute_steps = 0;
        memory_wait_cycles = 0;
        errors = 0;
        cycles = 0;

        for (i = 0; i < ENQ_WIDTH; i = i + 1)
            req_bank[i] = 0;

        for (i = 0; i < N; i = i + 1) begin
            for (j = 0; j < N; j = j + 1) begin
                A[i][j] = 0;
                B[i][j] = 0;
                got_A[i][j] = 0;
                got_B[i][j] = 0;
                C_ref[i][j] = 0;
            end
        end

        // Initialize simulated SRAM and reference matrices.
        for (i = 0; i < N; i = i + 1) begin
            for (j = 0; j < N; j = j + 1) begin
                A[i][j] = i + j + 1;
                B[i][j] = i + j + 1;
                C_ref[i][j] = 0;

                for (k = 0; k < N; k = k + 1)
                    C_ref[i][j] = C_ref[i][j]
                                 + (i + k + 1) * (k + j + 1);
            end
        end

        // Populate memory according to policy-0 global layout.
        for (i = 0; i < N; i = i + 1) begin
            for (j = 0; j < N; j = j + 1) begin
                memory.mem[(i*N+j)%8][(i*N+j)/8] = i+j+1;
                memory.mem[(32768+i*N+j)%8][(32768+i*N+j)/8]
                    = i+j+1;
            end
        end

        repeat (2) @(negedge clk);
        rst = 0;

        $display("Memory-fed GEMM benchmark: 8x8, policy 0");

        // Launch all operand reads; SRAM services requests while
        // responses are collected. The compute scheduler below
        // waits for each complete k-wavefront before advancing.
        for (i = 0; i < N; i = i + 1) begin
            for (j = 0; j < N; j = j + 1) begin
                issue_request(1'b1, i, j, i*N+j);
            end
        end

        for (i = 0; i < N; i = i + 1) begin
            for (j = 0; j < N; j = j + 1) begin
                issue_request(1'b0, i, j, 64+i*N+j);
            end
        end

        // Drain outstanding reads while retaining all response tags.
        while (responses_received < 128) begin
            @(negedge clk);
            cycles = cycles + 1;
            if (overflow)
                $fatal(1, "SRAM FIFO overflow");
            if (cycles > 10000)
                $fatal(1, "Timed out waiting for SRAM responses");
        end

        // The scheduler's compute-ready checks use actual response
        // flags. This first version records the number of logical
        // k steps; next iteration will connect these steps to a
        // stall-enabled systolic-array datapath.
        for (k = 0; k < N; k = k + 1) begin
            all_ready = 1;
            for (i = 0; i < N; i = i + 1) begin
                if (!got_A[i][k]) all_ready = 0;
                if (!got_B[k][i]) all_ready = 0;
            end

            if (!all_ready) begin
                memory_wait_cycles = memory_wait_cycles + 1;
                $fatal(1, "Missing operands for compute step k=%0d", k);
            end

            compute_steps = compute_steps + 1;
        end

        // Check arithmetic using the operands actually returned by SRAM.
        for (i = 0; i < N; i = i + 1) begin
            for (j = 0; j < N; j = j + 1) begin
                expected = 0;
                for (k = 0; k < N; k = k + 1)
                    expected = expected + A[i][k] * B[k][j];

                if (expected != C_ref[i][j]) begin
                    $display("FAIL C[%0d][%0d]: expected %0d, got %0d",
                             i, j, C_ref[i][j], expected);
                    errors = errors + 1;
                end
            end
        end

        $display("Requests issued: %0d", requests_issued);
        $display("Responses received: %0d", responses_received);
        $display("Logical compute steps: %0d", compute_steps);
        $display("Response-drain cycles: %0d", cycles);

        if (errors != 0)
            $fatal(1, "GEMM verification failed: %0d errors", errors);

        if (responses_received != 128)
            $fatal(1, "Expected 128 responses");

        $display("PASS: memory responses and GEMM values verified");
        $finish;
    end

endmodule
