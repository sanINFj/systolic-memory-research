module bank_mapper #(
    parameter integer BANK_POLICY = 0
) (
    input  wire        is_A,
    input  wire [7:0]  row,
    input  wire [7:0]  index,
    input  wire [15:0] K,
    input  wire [15:0] N,
    output reg  [2:0]  bank,
    output reg  [12:0] local_addr
);

    // Policies:
    // 0 = modulo interleaving
    // 1 = split A/B banks
    // 2 = operand-aware mapping
    // 3 = XOR mapping
    //
    // local_full is retained at 32 bits so the testbench can detect
    // addresses outside the 8192-byte physical bank capacity.

    reg [31:0] global_addr;
    reg [31:0] local_full;
    reg [31:0] row_value;
    reg [31:0] index_value;
    reg [31:0] k_value;
    reg [31:0] n_value;
    reg [31:0] groups;
    reg [31:0] row_group;
    reg [31:0] index_group;

    always @* begin
        row_value   = row;
        index_value = index;
        k_value     = (K == 0) ? 1 : K;
        n_value     = (N == 0) ? 1 : N;

        global_addr = 0;
        local_full  = 0;
        bank        = 0;
        local_addr  = 0;
        groups      = 0;
        row_group   = 0;
        index_group = 0;

        if (is_A)
            global_addr = row_value * k_value + index_value;
        else
            global_addr = 32'd32768 + row_value * n_value + index_value;

        case (BANK_POLICY)

            // Policy 0: contiguous global byte layout, modulo-8 banks.
            0: begin
                bank       = global_addr[2:0];
                local_full = global_addr >> 3;
            end

            // Policy 1: A uses banks 0-3; B uses banks 4-7.
            1: begin
                if (is_A) begin
                    bank       = row_value % 4;
                    local_full = (row_value / 4) * k_value + index_value;
                end
                else begin
                    bank       = 4 + (index_value % 4);
                    groups     = (n_value + 3) / 4;
                    local_full = row_value * groups + (index_value / 4);
                end
            end

            // Policy 2: A is banked by row; B is banked by column.
            // The B region starts at local address 4096.
            2: begin
                if (is_A) begin
                    bank       = row_value % 8;
                    local_full = (row_value / 8) * k_value + index_value;
                end
                else begin
                    bank       = (index_value + 4) % 8;
                    groups     = (n_value + 7) / 8;
                    local_full = 4096 + row_value * groups
                                      + (index_value / 8);
                end
            end

            // Policy 3: XOR bank selection with compact, collision-free
            // local indexing for each bank.
            3: begin
                if (is_A) begin
                    bank       = (row_value[2:0] ^ index_value[2:0]);
                    groups     = (k_value + 7) / 8;
                    row_group  = row_value / 8;
                    index_group = index_value / 8;
                    local_full = row_group * groups * 8
                               + index_group * 8
                               + (row_value % 8);
                end
                else begin
                    bank       = (row_value[2:0] ^ index_value[2:0]);
                    groups     = (n_value + 7) / 8;
                    row_group  = row_value / 8;
                    index_group = index_value / 8;
                    local_full = 4096
                               + row_group * groups * 8
                               + index_group * 8
                               + (row_value % 8);
                end
            end

            default: begin
                bank       = 0;
                local_full = 0;
            end
        endcase

        local_addr = local_full[12:0];
    end

endmodule
