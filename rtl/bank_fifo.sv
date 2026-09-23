`timescale 1ns/1ps

// ============================================================
// Bank FIFO
// ============================================================
//
// One FIFO belongs to one SRAM bank.
//
// Multiple requests may arrive in one cycle.
// At most one request is serviced per cycle.
//
// The enqueue interface uses PACKED vectors rather than
// unpacked array ports so that the design works cleanly with
// Icarus Verilog.
//
// ============================================================

module bank_fifo #(
    parameter ADDR_WIDTH = 13,
    parameter TAG_WIDTH  = 8,
    parameter DEPTH      = 32,
    parameter ENQ_WIDTH  = 16
) (
    input logic clk,
    input logic rst,

    // --------------------------------------------------------
    // Packed enqueue interface
    //
    // enq_valid[i]
    // enq_addr[i*ADDR_WIDTH +: ADDR_WIDTH]
    // enq_tag[i*TAG_WIDTH +: TAG_WIDTH]
    // --------------------------------------------------------

    input logic [ENQ_WIDTH-1:0]
        enq_valid,

    input logic [ENQ_WIDTH*ADDR_WIDTH-1:0]
        enq_addr,

    input logic [ENQ_WIDTH*TAG_WIDTH-1:0]
        enq_tag,

    // --------------------------------------------------------
    // Service interface
    // --------------------------------------------------------

    input logic service_enable,

    output logic service_valid,

    output logic [ADDR_WIDTH-1:0]
        service_addr,

    output logic [TAG_WIDTH-1:0]
        service_tag,

    // --------------------------------------------------------
    // Status
    // --------------------------------------------------------

    output logic [$clog2(DEPTH+1)-1:0]
        count,

    output logic overflow
);

    localparam PTR_WIDTH = $clog2(DEPTH);

    logic [ADDR_WIDTH-1:0]
        addr_mem [DEPTH];

    logic [TAG_WIDTH-1:0]
        tag_mem [DEPTH];

    logic [PTR_WIDTH-1:0]
        rd_ptr;

    logic [PTR_WIDTH-1:0]
        wr_ptr;

    integer i;
    integer accepted_count;

    logic do_service;

    // --------------------------------------------------------
    // FIFO head
    // --------------------------------------------------------

    always_comb begin

        if (count != 0) begin

            service_valid = 1'b1;

            service_addr =
                addr_mem[rd_ptr];

            service_tag =
                tag_mem[rd_ptr];

        end
        else begin

            service_valid = 1'b0;

            service_addr = '0;

            service_tag = '0;

        end

    end

    // --------------------------------------------------------
    // Sequential FIFO
    // --------------------------------------------------------

    always_ff @(posedge clk) begin

        if (rst) begin

            rd_ptr  <= '0;
            wr_ptr  <= '0;
            count   <= '0;
            overflow <= 1'b0;

        end
        else begin

            do_service =
                service_enable &&
                (count != 0);

            // Count incoming requests.

            accepted_count = 0;

            for (
                i = 0;
                i < ENQ_WIDTH;
                i = i + 1
            ) begin

                if (enq_valid[i]) begin

                    accepted_count =
                        accepted_count + 1;

                end

            end

            // ------------------------------------------------
            // Overflow check.
            //
            // If one request is serviced in the same cycle,
            // that service frees one FIFO slot.
            // ------------------------------------------------

            if (
                count
                + accepted_count
                - (do_service ? 1 : 0)
                > DEPTH
            ) begin

                overflow <= 1'b1;

            end
            else begin

                // ------------------------------------------------
                // Write incoming requests.
                // ------------------------------------------------

                accepted_count = 0;

                for (
                    i = 0;
                    i < ENQ_WIDTH;
                    i = i + 1
                ) begin

                    if (enq_valid[i]) begin

                        addr_mem[
                            (wr_ptr + accepted_count)
                            % DEPTH
                        ] <=
                            enq_addr[
                                i*ADDR_WIDTH
                                +: ADDR_WIDTH
                            ];

                        tag_mem[
                            (wr_ptr + accepted_count)
                            % DEPTH
                        ] <=
                            enq_tag[
                                i*TAG_WIDTH
                                +: TAG_WIDTH
                            ];

                        accepted_count =
                            accepted_count + 1;

                    end

                end

                // ------------------------------------------------
                // Read pointer.
                // ------------------------------------------------

                if (do_service) begin

                    if (
                        rd_ptr
                        == DEPTH - 1
                    ) begin

                        rd_ptr <= '0;

                    end
                    else begin

                        rd_ptr <=
                            rd_ptr + 1'b1;

                    end

                end

                // ------------------------------------------------
                // Write pointer.
                // ------------------------------------------------

                if (accepted_count != 0) begin

                    if (
                        (wr_ptr + accepted_count)
                        >= DEPTH
                    ) begin

                        wr_ptr <=
                            (wr_ptr + accepted_count)
                            - DEPTH;

                    end
                    else begin

                        wr_ptr <=
                            wr_ptr + accepted_count;

                    end

                end

                // ------------------------------------------------
                // FIFO count.
                // ------------------------------------------------

                case ({
                    do_service,
                    accepted_count != 0
                })

                    2'b00:
                        count <= count;

                    2'b01:
                        count <=
                            count + accepted_count;

                    2'b10:
                        count <=
                            count - 1'b1;

                    2'b11:
                        count <=
                            count
                            + accepted_count
                            - 1;

                    default:
                        count <= count;

                endcase

            end

        end

    end

endmodule
