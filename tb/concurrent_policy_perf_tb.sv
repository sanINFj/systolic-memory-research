`timescale 1ns/1ps

module concurrent_policy_perf_tb #(
    parameter integer BANK_POLICY = 0,
    parameter integer M = 8,
    parameter integer K = 8,
    parameter integer N = 8
);

    localparam integer BANKS = 8;
    localparam integer LANES = 16;
    localparam integer AW = 13;
    localparam integer TW = 8;
    localparam integer TOTAL = M*K + K*N;

    reg clk = 0;
    reg rst = 1;

    reg [LANES-1:0] req_valid = 0;
    reg [2:0] req_bank [LANES];
    reg [LANES*AW-1:0] req_addr = 0;
    reg [LANES*TW-1:0] req_tag = 0;

    wire [BANKS-1:0] rsp_valid;
    wire [BANKS*8-1:0] rsp_data;
    wire [BANKS*TW-1:0] rsp_tag;
    wire overflow;

    reg is_A;
    reg [7:0] row, index;
    reg [15:0] map_K, map_N;
    wire [2:0] mapped_bank;
    wire [12:0] mapped_addr;

    integer expected_data [0:TOTAL-1];
    integer seen [0:TOTAL-1];

    integer i, j, lane, sent, received;
    integer errors, cycles, issue_cycles, drain_cycles;
    integer id, row_id, col_id, operand_is_A;
    integer timeout_count;

    // Performance instrumentation
    reg measure_enable = 0;
    integer issue_cycle [0:TOTAL-1];
    integer latency_sum, max_latency, latency_value;
    integer request_count, response_count, latency_samples;
    integer overflow_cycle_count;

    integer bank_busy_cycles [0:BANKS-1];
    integer bank_req_count [0:BANKS-1];
    integer bank_occ_sum [0:BANKS-1];
    integer bank_max_occ [0:BANKS-1];
    integer bank_full_cycles [0:BANKS-1];

    integer monitor_b, monitor_lane, monitor_req_delta;

    always #100 clk = ~clk;

    bank_mapper #(.BANK_POLICY(BANK_POLICY)) mapper (
        .is_A(is_A),
        .row(row),
        .index(index),
        .K(map_K),
        .N(map_N),
        .bank(mapped_bank),
        .local_addr(mapped_addr)
    );

    banked_sram #(
        .NUM_BANKS(BANKS),
        .BANK_SIZE(8192),
        .ADDR_WIDTH(AW),
        .TAG_WIDTH(TW),
        .ENQ_WIDTH(LANES),
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

    task automatic clear_requests;
        integer x;
        begin
            req_valid = 0;
            req_addr = 0;
            req_tag = 0;
            for (x=0; x<LANES; x=x+1)
                req_bank[x] = 0;
        end
    endtask

    task automatic collect_responses;
        integer b;
        integer tag_value;
        reg [7:0] data_value;
        begin
            for (b=0; b<BANKS; b=b+1) begin
                if (rsp_valid[b]) begin
                    tag_value = rsp_tag[b*TW +: TW];
                    data_value = rsp_data[b*8 +: 8];

                    if (tag_value < 0 || tag_value >= TOTAL) begin
                        $display("FAIL: invalid response tag %0d", tag_value);
                        errors = errors + 1;
                    end
                    else begin
                        if (seen[tag_value] != 0) begin
                            $display("FAIL: duplicate response tag %0d", tag_value);
                            errors = errors + 1;
                        end
                        else begin
                            seen[tag_value] = 1;
                            received = received + 1;

                            latency_value = cycles - issue_cycle[tag_value];
                            if (latency_value < 0) begin
                                $display("FAIL: invalid latency for tag %0d", tag_value);
                                errors = errors + 1;
                            end else begin
                                latency_sum = latency_sum + latency_value;
                                latency_samples = latency_samples + 1;
                                if (latency_value > max_latency)
                                    max_latency = latency_value;
                            end

                            if (data_value !== expected_data[tag_value][7:0]) begin
                                $display(
                                    "FAIL: tag=%0d expected=%02h got=%02h",
                                    tag_value,
                                    expected_data[tag_value][7:0],
                                    data_value
                                );
                                errors = errors + 1;
                            end
                        end
                    end
                end
            end
        end
    endtask

    genvar perf_b;
    generate
        for (perf_b=0; perf_b<BANKS; perf_b=perf_b+1) begin : PERF_MONITOR
            integer occ_now;
            integer req_delta;
            integer lane_idx;

            always @(posedge clk) begin
                if (rst) begin
                    bank_busy_cycles[perf_b] <= 0;
                    bank_req_count[perf_b] <= 0;
                    bank_occ_sum[perf_b] <= 0;
                    bank_max_occ[perf_b] <= 0;
                    bank_full_cycles[perf_b] <= 0;
                end else if (measure_enable) begin
                    occ_now = dut.BANK_FIFO[perf_b].fifo_inst.count;
                    req_delta = 0;

                    for (lane_idx=0; lane_idx<LANES; lane_idx=lane_idx+1)
                        if (req_valid[lane_idx] &&
                            req_bank[lane_idx] == perf_b)
                            req_delta = req_delta + 1;

                    bank_req_count[perf_b] <=
                        bank_req_count[perf_b] + req_delta;

                    if (dut.BANK_FIFO[perf_b].fifo_inst.service_valid)
                        bank_busy_cycles[perf_b] <=
                            bank_busy_cycles[perf_b] + 1;

                    bank_occ_sum[perf_b] <=
                        bank_occ_sum[perf_b] + occ_now;

                    if (occ_now > bank_max_occ[perf_b])
                        bank_max_occ[perf_b] <= occ_now;

                    if (occ_now == 32)
                        bank_full_cycles[perf_b] <=
                            bank_full_cycles[perf_b] + 1;
                end
            end
        end
    endgenerate

    integer req_delta_global, rsp_delta_global;
    always @(posedge clk) begin
        req_delta_global = 0;
        rsp_delta_global = 0;

        if (!rst && measure_enable) begin
            for (monitor_lane=0; monitor_lane<LANES;
                 monitor_lane=monitor_lane+1)
                if (req_valid[monitor_lane])
                    req_delta_global = req_delta_global + 1;

            for (monitor_b=0; monitor_b<BANKS; monitor_b=monitor_b+1)
                if (rsp_valid[monitor_b])
                    rsp_delta_global = rsp_delta_global + 1;
        end

        if (rst) begin
            request_count <= 0;
            response_count <= 0;
            latency_sum <= 0;
            max_latency <= 0;
            latency_samples <= 0;
            overflow_cycle_count <= 0;
        end else if (measure_enable) begin
            request_count <= request_count + req_delta_global;
            response_count <= response_count + rsp_delta_global;
            if (overflow)
                overflow_cycle_count <= overflow_cycle_count + 1;
        end
    end

    initial begin
        errors = 0;
        sent = 0;
        received = 0;
        cycles = 0;
        issue_cycles = 0;
        drain_cycles = 0;
        timeout_count = 0;
        latency_sum = 0;
        max_latency = 0;
        latency_samples = 0;
        request_count = 0;
        response_count = 0;
        overflow_cycle_count = 0;
        measure_enable = 0;

        for (i=0; i<TOTAL; i=i+1)
            issue_cycle[i] = -1;

        clear_requests();

        for (i=0; i<TOTAL; i=i+1) begin
            seen[i] = 0;
            expected_data[i] = 0;
        end

        for (i=0; i<BANKS; i=i+1)
            for (j=0; j<8192; j=j+1)
                dut.mem[i][j] = 0;

        repeat (4) @(negedge clk);
        rst = 0;

        // Initialize A at the addresses selected by this bank policy.
        for (i=0; i<M; i=i+1) begin
            for (j=0; j<K; j=j+1) begin
                is_A = 1;
                row = i;
                index = j;
                map_K = K;
                map_N = N;
                #1;
                dut.mem[mapped_bank][mapped_addr] =
                    8'h20 + ((i*7 + j*3) & 8'h3f);
            end
        end

        // Initialize B at the addresses selected by this bank policy.
        for (i=0; i<K; i=i+1) begin
            for (j=0; j<N; j=j+1) begin
                is_A = 0;
                row = i;
                index = j;
                map_K = K;
                map_N = N;
                #1;
                dut.mem[mapped_bank][mapped_addr] =
                    8'h80 + ((i*7 + j*3) & 8'h3f);
            end
        end

        $display("Bank policy ID: %0d", BANK_POLICY);
        $display("Concurrent operand-read workload: A=%0dx%0d, B=%0dx%0d",
                 M, K, K, N);
        $display("Total operand requests: %0d", TOTAL);

        // Start the measurement window immediately before first request.
        measure_enable = 1;

        // Issue batches while collecting responses continuously.
        while (sent < TOTAL) begin
            @(negedge clk);
            clear_requests();
            lane = 0;

            while (lane < LANES && sent < TOTAL) begin
                id = sent;
                issue_cycle[id] = cycles + 1;

                if (id < M*K) begin
                    operand_is_A = 1;
                    row_id = id / K;
                    col_id = id % K;
                end
                else begin
                    operand_is_A = 0;
                    row_id = (id - M*K) / N;
                    col_id = (id - M*K) % N;
                end

                is_A = operand_is_A;
                row = row_id;
                index = col_id;
                map_K = K;
                map_N = N;
                #1;

                req_valid[lane] = 1'b1;
                req_bank[lane] = mapped_bank;
                req_addr[lane*AW +: AW] = mapped_addr;
                req_tag[lane*TW +: TW] = id;

                if (operand_is_A)
                    expected_data[id] =
                        8'h20 + ((row_id*7 + col_id*3) & 8'h3f);
                else
                    expected_data[id] =
                        8'h80 + ((row_id*7 + col_id*3) & 8'h3f);

                lane = lane + 1;
                sent = sent + 1;
            end

            // Requests are sampled at this rising edge.
            @(posedge clk);
            #2;
            cycles = cycles + 1;
            issue_cycles = issue_cycles + 1;

            if (overflow) begin
                $display("FAIL: overflow during issue");
                errors = errors + 1;
            end

            // Capture responses that arrived during request issuance.
            collect_responses();
        end

        @(negedge clk);
        clear_requests();

        // Continue collecting until every response is accounted for.
        timeout_count = 0;
        while (received < TOTAL && timeout_count < 10000) begin
            @(posedge clk);
            #2;
            cycles = cycles + 1;
            drain_cycles = drain_cycles + 1;
            timeout_count = timeout_count + 1;

            if (overflow) begin
                $display("FAIL: overflow during drain");
                errors = errors + 1;
            end

            collect_responses();
        end

        measure_enable = 0;

        if (received != TOTAL) begin
            $display("FAIL: only %0d of %0d responses received",
                     received, TOTAL);
            errors = errors + 1;
        end

        for (i=0; i<TOTAL; i=i+1) begin
            if (seen[i] != 1) begin
                $display("FAIL: missing response tag %0d", i);
                errors = errors + 1;
            end
        end

        if (errors == 0)
            $display("PASS: all %0d concurrent-workload responses verified",
                     TOTAL);
        else
            $display("FAIL: %0d errors", errors);

        $display("Request issue cycles: %0d", issue_cycles);
        $display("Drain/response collection cycles: %0d", drain_cycles);
        $display("Total measured cycles: %0d", cycles);

        $display("PERF_SUMMARY,policy=%0d,M=%0d,K=%0d,N=%0d,requests=%0d,responses=%0d,cycles=%0d,latency_avg=%0f,latency_max=%0d,overflow_cycles=%0d",
            BANK_POLICY, M, K, N, request_count, received, cycles,
            latency_samples ? (1.0*latency_sum/latency_samples) : 0.0,
            max_latency, overflow_cycle_count);

        $display("BANK_METRICS,bank,requests,busy_cycles,utilization,max_fifo,avg_fifo,full_cycles");
        for (i=0; i<BANKS; i=i+1)
            $display("BANK_METRICS,%0d,%0d,%0d,%0f,%0d,%0f,%0d",
                i, bank_req_count[i], bank_busy_cycles[i],
                cycles ? (1.0*bank_busy_cycles[i]/cycles) : 0.0,
                bank_max_occ[i],
                cycles ? (1.0*bank_occ_sum[i]/cycles) : 0.0,
                bank_full_cycles[i]);

        if (overflow_cycle_count != 0) begin
            $display("FAIL: overflow was observed during measurement");
            $fatal(1, "FIFO overflow");
        end

        if (errors == 0)
            $finish;
        else
            $fatal(1, "Concurrent policy benchmark failed");
    end

endmodule
