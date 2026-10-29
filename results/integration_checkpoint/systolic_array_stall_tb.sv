`timescale 1ns/1ps

module systolic_array_stall_tb;
    localparam integer N = 2;

    logic clk = 0;
    logic rst = 1;
    logic advance;

    logic signed [7:0] a_in [N];
    logic signed [7:0] b_in [N];
    logic a_valid_in [N];
    logic b_valid_in [N];

    wire signed [31:0] c_out [N][N];
    wire a_valid_out [N][N];
    wire b_valid_out [N][N];

    integer A [N][N];
    integer B [N][N];
    integer expected;
    integer errors = 0;
    integer i, j, k, t;

    systolic_array_stall #(
        .N(N),
        .DATA_WIDTH(8),
        .ACC_WIDTH(32)
    ) dut (
        .clk(clk),
        .rst(rst),
        .advance(advance),
        .a_in(a_in),
        .b_in(b_in),
        .a_valid_in(a_valid_in),
        .b_valid_in(b_valid_in),
        .c_out(c_out),
        .a_valid_out(a_valid_out),
        .b_valid_out(b_valid_out)
    );

    always #5 clk = ~clk;

    initial begin
        A[0][0] = 1; A[0][1] = 2;
        A[1][0] = 3; A[1][1] = 4;
        B[0][0] = 5; B[0][1] = 6;
        B[1][0] = 7; B[1][1] = 8;

        advance = 1;
        for (i = 0; i < N; i = i + 1) begin
            a_in[i] = 0;
            b_in[i] = 0;
            a_valid_in[i] = 0;
            b_valid_in[i] = 0;
        end

        repeat (2) @(negedge clk);
        rst = 0;

        // Five scheduled wavefront slots for a 2x2 array.
        // A row is skewed by its row index; B column by its column.
        for (t = 0; t < 5; t = t + 1) begin
            @(negedge clk);

            // Deliberate global stall at slot 2.
            if (t == 2) begin
                advance = 0;
                for (i = 0; i < N; i = i + 1) begin
                    a_in[i] = 0;
                    b_in[i] = 0;
                    a_valid_in[i] = 0;
                    b_valid_in[i] = 0;
                end
                @(negedge clk);
            end

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
        end

        @(negedge clk);
        for (i = 0; i < N; i = i + 1) begin
            a_in[i] = 0;
            b_in[i] = 0;
            a_valid_in[i] = 0;
            b_valid_in[i] = 0;
        end

        repeat (N+3) @(negedge clk);

        for (i = 0; i < N; i = i + 1) begin
            for (j = 0; j < N; j = j + 1) begin
                expected = 0;
                for (k = 0; k < N; k = k + 1)
                    expected = expected + A[i][k] * B[k][j];

                $display("C[%0d][%0d]: expected=%0d actual=%0d",
                         i, j, expected, $signed(c_out[i][j]));

                if ($signed(c_out[i][j]) !== expected)
                    errors = errors + 1;
            end
        end

        if (errors != 0)
            $fatal(1, "FAIL: %0d GEMM mismatches", errors);

        $display("PASS: 2x2 stall-aware systolic GEMM");
        $finish;
    end
endmodule
