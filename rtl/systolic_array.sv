`timescale 1ns/1ps

module systolic_array #(
    parameter N          = 2,
    parameter DATA_WIDTH = 8,
    parameter ACC_WIDTH  = 32
) (
    input  logic clk,
    input  logic rst,

    input  logic signed [DATA_WIDTH-1:0] a_in [N],
    input  logic signed [DATA_WIDTH-1:0] b_in [N],

    output wire signed [ACC_WIDTH-1:0] c_out [N][N]
);

    wire signed [DATA_WIDTH-1:0] a_wire [N][N+1];
    wire signed [DATA_WIDTH-1:0] b_wire [N+1][N];

    genvar i;
    genvar j;

    generate
        for (i = 0; i < N; i = i + 1) begin : A_INPUT
            assign a_wire[i][0] = a_in[i];
        end
    endgenerate

    generate
        for (j = 0; j < N; j = j + 1) begin : B_INPUT
            assign b_wire[0][j] = b_in[j];
        end
    endgenerate

    generate
        for (i = 0; i < N; i = i + 1) begin : ROW
            for (j = 0; j < N; j = j + 1) begin : COL

                pe #(
                    .DATA_WIDTH(DATA_WIDTH),
                    .ACC_WIDTH(ACC_WIDTH)
                ) pe_inst (
                    .clk(clk),
                    .rst(rst),

                    .a_in(a_wire[i][j]),
                    .b_in(b_wire[i][j]),

                    .a_out(a_wire[i][j+1]),
                    .b_out(b_wire[i+1][j]),

                    .acc_out(c_out[i][j])
                );

            end
        end
    endgenerate

endmodule
