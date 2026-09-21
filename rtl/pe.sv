module pe #(
    parameter DATA_WIDTH = 8,
    parameter ACC_WIDTH  = 32
) (
    input  logic                         clk,
    input  logic                         rst,

    input  logic signed [DATA_WIDTH-1:0] a_in,
    input  logic signed [DATA_WIDTH-1:0] w_in,

    input  logic signed [ACC_WIDTH-1:0]  psum_in,

    output logic signed [DATA_WIDTH-1:0] a_out,
    output logic signed [DATA_WIDTH-1:0] w_out,

    output logic signed [ACC_WIDTH-1:0]  psum_out
);

    always_ff @(posedge clk) begin
        if (rst) begin
            a_out    <= '0;
            w_out    <= '0;
            psum_out <= '0;
        end
        else begin
            a_out    <= a_in;
            w_out    <= w_in;
            psum_out <= psum_in + (a_in * w_in);
        end
    end

endmodule
