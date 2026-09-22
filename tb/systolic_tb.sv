`timescale 1ns/1ps

module systolic_tb;

    localparam N          = 8;
    localparam DATA_WIDTH = 8;
    localparam ACC_WIDTH  = 32;

    logic clk;
    logic rst;

    logic signed [DATA_WIDTH-1:0] a_in [N];
    logic signed [DATA_WIDTH-1:0] b_in [N];

    wire signed [ACC_WIDTH-1:0] c_out [N][N];

    /*
     * DUT
     */
    systolic_array #(
        .N(N),
        .DATA_WIDTH(DATA_WIDTH),
        .ACC_WIDTH(ACC_WIDTH)
    ) dut (
        .clk(clk),
        .rst(rst),
        .a_in(a_in),
        .b_in(b_in),
        .c_out(c_out)
    );

    /*
     * 100 MHz clock
     */
    always #5 clk = ~clk;

    /*
     * Test matrices.
     *
     * A[i][k] = i + k + 1
     * B[k][j] = k + j + 1
     *
     * This gives every PE a different result,
     * making timing/data errors easy to detect.
     */
    integer A [0:N-1][0:N-1];
    integer B [0:N-1][0:N-1];

    integer i;
    integer j;
    integer k;
    integer t;

    integer expected;
    integer errors;

    initial begin

        /*
         * VCD
         */
        $dumpfile("results/systolic_8x8.vcd");
        $dumpvars(0, systolic_tb);

        /*
         * -------------------------
         * INITIALIZE CLOCK/RESET
         * -------------------------
         */

        clk = 1'b0;
        rst = 1'b1;

        for (i = 0; i < N; i = i + 1) begin
            a_in[i] = 0;
            b_in[i] = 0;
        end

        /*
         * Create matrices.
         */
        for (i = 0; i < N; i = i + 1) begin
            for (j = 0; j < N; j = j + 1) begin

                A[i][j] = i + j + 1;
                B[i][j] = i + j + 1;

            end
        end

        /*
         * Hold reset for two complete cycles.
         */
        repeat (2) @(posedge clk);

        /*
         * Release reset at a safe clock edge.
         */
        @(negedge clk);
        rst = 1'b0;

        /*
         * -------------------------
         * SYSTOLIC DATA INJECTION
         * -------------------------
         *
         * A[i][k] enters row i at:
         *
         *     t = i + k
         *
         * B[k][j] enters column j at:
         *
         *     t = j + k
         *
         * Therefore:
         *
         *     A[i][k] and B[k][j]
         *
         * meet at PE(i,j) at:
         *
         *     t = i + j + k
         */

        for (t = 0; t <= 2*N-2; t = t + 1) begin

            /*
             * Change inputs while clock is LOW.
             */
            @(negedge clk);

            /*
             * -------------------------
             * A STREAM
             * -------------------------
             */

            for (i = 0; i < N; i = i + 1) begin

                a_in[i] = 0;

                for (k = 0; k < N; k = k + 1) begin

                    if (t == i + k)
                        a_in[i] = A[i][k];

                end

            end

            /*
             * -------------------------
             * B STREAM
             * -------------------------
             */

            for (j = 0; j < N; j = j + 1) begin

                b_in[j] = 0;

                for (k = 0; k < N; k = k + 1) begin

                    if (t == j + k)
                        b_in[j] = B[k][j];

                end

            end

            /*
             * Print first few cycles for debugging.
             */
            if (t < 3) begin

                $display(
                    "Injection cycle %0d",
                    t
                );

                $display(
                    "  A = %0d %0d %0d %0d %0d %0d %0d %0d",
                    a_in[0],
                    a_in[1],
                    a_in[2],
                    a_in[3],
                    a_in[4],
                    a_in[5],
                    a_in[6],
                    a_in[7]
                );

                $display(
                    "  B = %0d %0d %0d %0d %0d %0d %0d %0d",
                    b_in[0],
                    b_in[1],
                    b_in[2],
                    b_in[3],
                    b_in[4],
                    b_in[5],
                    b_in[6],
                    b_in[7]
                );

            end

        end

        /*
         * -------------------------
         * CLEAR INPUTS
         * -------------------------
         */

        @(negedge clk);

        for (i = 0; i < N; i = i + 1) begin
            a_in[i] = 0;
            b_in[i] = 0;
        end

        /*
         * -------------------------
         * WAIT FOR ARRAY TO DRAIN
         * -------------------------
         *
         * Last useful product occurs at:
         *
         *     (N-1) + (N-1) + (N-1)
         *
         *     = 3*N - 3
         *
         * For N=8:
         *
         *     3*8 - 3 = 21 cycles
         *
         * We wait substantially longer.
         */
        repeat (15) @(posedge clk);

        /*
         * Move to the falling edge before checking.
         *
         * This avoids racing with nonblocking
         * assignments inside the PEs.
         */
        @(negedge clk);

        /*
         * -------------------------
         * CHECK RESULTS
         * -------------------------
         */

        errors = 0;

        $display("");
        $display("========================================");
        $display("8x8 SYSTOLIC GEMM RESULTS");
        $display("========================================");

        for (i = 0; i < N; i = i + 1) begin

            for (j = 0; j < N; j = j + 1) begin

                expected = 0;

                for (k = 0; k < N; k = k + 1) begin

                    expected =
                        expected +
                        A[i][k] * B[k][j];

                end

                $display(
                    "C[%0d][%0d] = %0d    expected = %0d",
                    i,
                    j,
                    c_out[i][j],
                    expected
                );

                if (c_out[i][j] !== expected) begin
                    errors = errors + 1;
                end

            end

        end

        /*
         * -------------------------
         * FINAL RESULT
         * -------------------------
         */

        $display("");
        $display("========================================");

        if (errors == 0) begin

            $display("PASS: 8x8 systolic GEMM");

        end
        else begin

            $display(
                "FAIL: %0d errors",
                errors
            );

        end

        $display("========================================");

        $finish;

    end

endmodule
