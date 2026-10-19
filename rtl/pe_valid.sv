`timescale 1ns/1ps

module pe_valid #(
    parameter integer DATA_WIDTH = 8,
    parameter integer ACC_WIDTH  = 32
) (
    input  logic clk,
    input  logic rst,

    input  logic signed [DATA_WIDTH-1:0] a_in,
    input  logic signed [DATA_WIDTH-1:0] b_in,
    input  logic a_valid_in,
    input  logic b_valid_in,

    output logic signed [DATA_WIDTH-1:0] a_out,
    output logic signed [DATA_WIDTH-1:0] b_out,
    output logic a_valid_out,
    output logic b_valid_out,

    output logic signed [ACC_WIDTH-1:0] acc_out,
    output logic mac_valid
);

    logic signed [2*DATA_WIDTH-1:0] product;

    always_comb begin
        product = a_in * b_in;
    end

    always_ff @(posedge clk) begin
        if (rst) begin
            a_out       <= '0;
            b_out       <= '0;
            a_valid_out <= 1'b0;
            b_valid_out <= 1'b0;
            acc_out     <= '0;
            mac_valid   <= 1'b0;
        end else begin
            // Propagate each operand and its validity independently.
            a_out       <= a_in;
            b_out       <= b_in;
            a_valid_out <= a_valid_in;
            b_valid_out <= b_valid_in;

            // Accumulate only when both operands are valid.
            mac_valid <= a_valid_in && b_valid_in;

            if (a_valid_in && b_valid_in)
                acc_out <= acc_out + product;
        end
    end

endmodule
