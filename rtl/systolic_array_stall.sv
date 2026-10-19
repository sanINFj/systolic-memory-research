`timescale 1ns/1ps

module systolic_array_stall #(
    parameter integer N = 2,
    parameter integer DATA_WIDTH = 8,
    parameter integer ACC_WIDTH = 32
) (
    input logic clk,
    input logic rst,
    input logic advance,

    input logic signed [DATA_WIDTH-1:0] a_in [N],
    input logic signed [DATA_WIDTH-1:0] b_in [N],
    input logic a_valid_in [N],
    input logic b_valid_in [N],

    output wire signed [ACC_WIDTH-1:0] c_out [N][N],
    output wire a_valid_out [N][N],
    output wire b_valid_out [N][N]
);

    wire signed [DATA_WIDTH-1:0] a_wire [N][N+1];
    wire signed [DATA_WIDTH-1:0] b_wire [N+1][N];

    wire a_valid_wire [N][N+1];
    wire b_valid_wire [N+1][N];

    genvar i, j;

    generate
        for (i = 0; i < N; i = i + 1) begin : A_INPUT
            assign a_wire[i][0] = a_in[i];
            assign a_valid_wire[i][0] = a_valid_in[i];
        end
        for (j = 0; j < N; j = j + 1) begin : B_INPUT
            assign b_wire[0][j] = b_in[j];
            assign b_valid_wire[0][j] = b_valid_in[j];
        end
    endgenerate

    generate
        for (i = 0; i < N; i = i + 1) begin : ROW
            for (j = 0; j < N; j = j + 1) begin : COL
                pe_stall #(
                    .DATA_WIDTH(DATA_WIDTH),
                    .ACC_WIDTH(ACC_WIDTH)
                ) pe_inst (
                    .clk(clk),
                    .rst(rst),
                    .advance(advance),
                    .a_in(a_wire[i][j]),
                    .b_in(b_wire[i][j]),
                    .a_valid_in(a_valid_wire[i][j]),
                    .b_valid_in(b_valid_wire[i][j]),
                    .a_out(a_wire[i][j+1]),
                    .b_out(b_wire[i+1][j]),
                    .a_valid_out(a_valid_wire[i][j+1]),
                    .b_valid_out(b_valid_wire[i+1][j]),
                    .acc_out(c_out[i][j])
                );

                assign a_valid_out[i][j] = a_valid_wire[i][j+1];
                assign b_valid_out[i][j] = b_valid_wire[i+1][j];
            end
        end
    endgenerate

endmodule
