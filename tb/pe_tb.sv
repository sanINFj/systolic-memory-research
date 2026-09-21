`timescale 1ns/1ps

module pe_tb;

    localparam DATA_WIDTH = 8;
    localparam ACC_WIDTH  = 32;

    logic clk;
    logic rst;

    logic signed [DATA_WIDTH-1:0] a_in;
    logic signed [DATA_WIDTH-1:0] w_in;
    logic signed [ACC_WIDTH-1:0] psum_in;

    logic signed [DATA_WIDTH-1:0] a_out;
    logic signed [DATA_WIDTH-1:0] w_out;
    logic signed [ACC_WIDTH-1:0] psum_out;

    pe #(
        .DATA_WIDTH(DATA_WIDTH),
        .ACC_WIDTH(ACC_WIDTH)
    ) dut (
        .clk(clk),
        .rst(rst),
        .a_in(a_in),
        .w_in(w_in),
        .psum_in(psum_in),
        .a_out(a_out),
        .w_out(w_out),
        .psum_out(psum_out)
    );

    always #5 clk = ~clk;

    initial begin
        $dumpfile("results/pe.vcd");
        $dumpvars(0, pe_tb);

        clk = 0;
        rst = 1;

        a_in = 0;
        w_in = 0;
        psum_in = 0;

        #12;

        rst = 0;

        // 3 * 4 + 5 = 17
        a_in = 3;
        w_in = 4;
        psum_in = 5;

        #10;

        if (psum_out !== 17) begin
            $display("ERROR: expected 17, got %0d", psum_out);
            $finish;
        end

        $display("PASS: PE MAC result = %0d", psum_out);

        $finish;
    end

endmodule
