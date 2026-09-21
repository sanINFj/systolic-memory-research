module systolic_array #(
    parameter N          = 8,
    parameter DATA_WIDTH = 8,
    parameter ACC_WIDTH  = 32
) (
    input  logic clk,
    input  logic rst,

    input  logic signed [DATA_WIDTH-1:0] a_in [N],
    input  logic signed [DATA_WIDTH-1:0] w_in [N],

    input  logic signed [ACC_WIDTH-1:0] psum_in [N],

    output logic signed [ACC_WIDTH-1:0] psum_out [N]
);

    logic signed [DATA_WIDTH-1:0] a_pipe [N][N];
    logic signed [DATA_WIDTH-1:0] w_pipe [N][N];

    logic signed [ACC_WIDTH-1:0] psum_pipe [N][N];

    genvar i, j;

    generate
        for (i = 0; i < N; i++) begin : ROW
            for (j = 0; j < N; j++) begin : COL

                logic signed [DATA_WIDTH-1:0] pe_a_in;
                logic signed [DATA_WIDTH-1:0] pe_w_in;
                logic signed [ACC_WIDTH-1:0]  pe_psum_in;

                logic signed [DATA_WIDTH-1:0] pe_a_out;
                logic signed [DATA_WIDTH-1:0] pe_w_out;
                logic signed [ACC_WIDTH-1:0]  pe_psum_out;

                if (j == 0)
                    assign pe_a_in = a_in[i];
                else
                    assign pe_a_in = a_pipe[i][j-1];

                if (i == 0)
                    assign pe_w_in = w_in[j];
                else
                    assign pe_w_in = w_pipe[i-1][j];

                if (j == 0)
                    assign pe_psum_in = psum_in[i];
                else
                    assign pe_psum_in = psum_pipe[i][j-1];

                pe #(
                    .DATA_WIDTH(DATA_WIDTH),
                    .ACC_WIDTH(ACC_WIDTH)
                ) pe_inst (
                    .clk(clk),
                    .rst(rst),

                    .a_in(pe_a_in),
                    .w_in(pe_w_in),
                    .psum_in(pe_psum_in),

                    .a_out(pe_a_out),
                    .w_out(pe_w_out),
                    .psum_out(pe_psum_out)
                );

                assign a_pipe[i][j]    = pe_a_out;
                assign w_pipe[i][j]    = pe_w_out;
                assign psum_pipe[i][j] = pe_psum_out;

            end
        end
    endgenerate

    for (genvar k = 0; k < N; k++) begin
        assign psum_out[k] = psum_pipe[k][N-1];
    end

endmodule
