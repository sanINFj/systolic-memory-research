`timescale 1ns/1ps

// ============================================================
// SRAM Bank Mapping
// ============================================================
//
// Fixed architecture:
//
//     8 banks
//     8 KB per bank
//
// Policies:
//
//     0 = modulo
//     1 = split
//     2 = operand-aware
//     3 = xor
//
// Operand convention:
//
//     A:
//         row  = output row i
//         index = K coordinate
//
//     B:
//         row  = K coordinate
//         index = output column j
//
// The mapping formulas match the Python banking_model.py.
//
// ============================================================

module bank_mapper #(
    parameter BANK_POLICY = 0
) (
    input logic is_A,

    input logic [7:0] row,

    input logic [7:0] index,

    input logic [15:0] K,

    input logic [15:0] N,

    output logic [2:0] bank,

    output logic [12:0] local_addr
);

    logic [31:0] global_addr;

    always_comb begin

        global_addr = 32'd0;

        bank = 3'd0;

        // ----------------------------------------------------
        // Physical row-major byte address.
        //
        // A:
        //     address = row * K + index
        //
        // B:
        //     address = 32768 + row * N + index
        //
        // B starts at 32 KB.
        // ----------------------------------------------------

        if (is_A) begin

            global_addr =
                row * K
                + index;

        end
        else begin

            global_addr =
                32'd32768
                + row * N
                + index;

        end

        // ----------------------------------------------------
        // Policy
        // ----------------------------------------------------

        case (BANK_POLICY)

            // ----------------------------------------------
            // MODULO
            // ----------------------------------------------

            0: begin

                bank =
                    global_addr[2:0];

            end

            // ----------------------------------------------
            // SPLIT
            //
            // A → banks 0..3
            // B → banks 4..7
            // ----------------------------------------------

            1: begin

                if (is_A) begin

                    bank =
                        row[1:0];

                end
                else begin

                    bank =
                        3'b100
                        | index[1:0];

                end

            end

            // ----------------------------------------------
            // OPERAND-AWARE
            //
            // A row i → bank i
            // B column j → bank (j + 4) mod 8
            // ----------------------------------------------

            2: begin

                if (is_A) begin

                    bank =
                        row[2:0];

                end
                else begin

                    bank =
                        index[2:0]
                        + 3'd4;

                end

            end

            // ----------------------------------------------
            // XOR
            //
            // A → row XOR K
            // B → K XOR column
            // ----------------------------------------------

            3: begin

                if (is_A) begin

                    bank =
                        row[2:0]
                        ^ index[2:0];

                end
                else begin

                    bank =
                        row[2:0]
                        ^ index[2:0];

                end

            end

            default: begin

                bank = 3'd0;

            end

        endcase

        // ----------------------------------------------------
        // Local address.
        //
        // Each bank stores 8192 bytes.
        //
        // Divide physical byte address by 8 to obtain the
        // bank-local word/byte index under interleaving.
        //
        // For split/operand-aware/xor, the bank organization
        // is logical, so modulo-style physical local addressing
        // is used as the first RTL model.
        // ----------------------------------------------------

        local_addr =
            global_addr[15:3];

    end

endmodule
