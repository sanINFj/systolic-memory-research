`timescale 1ns/1ps

// ============================================================
// BANKED SRAM
// ============================================================
//
// 64 KB total
// 8 banks
// 8 KB per bank
//
// Each bank:
//
//     request queue
//     one read per cycle
//     FIFO ordering
//
// Maximum incoming requests:
//
//     16 / cycle
//
// ============================================================

module banked_sram #(
    parameter NUM_BANKS  = 8,
    parameter BANK_SIZE  = 8192,
    parameter ADDR_WIDTH = 13,
    parameter TAG_WIDTH  = 8,
    parameter ENQ_WIDTH  = 16,
    parameter FIFO_DEPTH = 32
) (
    input logic clk,
    input logic rst,

    input logic [ENQ_WIDTH-1:0]
        req_valid,

    input logic [2:0]
        req_bank [ENQ_WIDTH],

    input logic [
        ENQ_WIDTH*ADDR_WIDTH-1:0
    ]
        req_addr,

    input logic [
        ENQ_WIDTH*TAG_WIDTH-1:0
    ]
        req_tag,

    output logic [NUM_BANKS-1:0]
        rsp_valid,

    output logic [
        NUM_BANKS*8-1:0
    ]
        rsp_data,

    output logic [
        NUM_BANKS*TAG_WIDTH-1:0
    ]
        rsp_tag,

    output logic overflow
);

    // --------------------------------------------------------
    // SRAM
    // --------------------------------------------------------

    logic [7:0]
        mem [NUM_BANKS][BANK_SIZE];

    // --------------------------------------------------------
    // FIFO inputs
    //
    // Every bank receives a complete 16-lane interface.
    // --------------------------------------------------------

    logic [
        ENQ_WIDTH-1:0
    ]
        fifo_enq_valid [NUM_BANKS];

    logic [
        ENQ_WIDTH*ADDR_WIDTH-1:0
    ]
        fifo_enq_addr [NUM_BANKS];

    logic [
        ENQ_WIDTH*TAG_WIDTH-1:0
    ]
        fifo_enq_tag [NUM_BANKS];

    // --------------------------------------------------------
    // FIFO outputs
    // --------------------------------------------------------

    logic
        fifo_service_valid [NUM_BANKS];

    logic [
        ADDR_WIDTH-1:0
    ]
        fifo_service_addr [NUM_BANKS];

    logic [
        TAG_WIDTH-1:0
    ]
        fifo_service_tag [NUM_BANKS];

    logic
        fifo_overflow [NUM_BANKS];

    integer bank;
    integer lane;

    // --------------------------------------------------------
    // REQUEST ROUTING
    // --------------------------------------------------------

    always_comb begin

        // Clear all FIFO inputs.

        for (
            bank = 0;
            bank < NUM_BANKS;
            bank = bank + 1
        ) begin

            fifo_enq_valid[bank] = '0;

            fifo_enq_addr[bank] = '0;

            fifo_enq_tag[bank] = '0;

        end

        // Route each request directly to its selected bank.
        //
        // Important:
        //
        // We preserve the original request lane.
        // This avoids the previous compaction problem.

        for (
            lane = 0;
            lane < ENQ_WIDTH;
            lane = lane + 1
        ) begin

            if (req_valid[lane]) begin

                fifo_enq_valid[
                    req_bank[lane]
                ][lane] = 1'b1;

                fifo_enq_addr[
                    req_bank[lane]
                ][
                    lane*ADDR_WIDTH
                    +:
                    ADDR_WIDTH
                ]
                =
                req_addr[
                    lane*ADDR_WIDTH
                    +:
                    ADDR_WIDTH
                ];

                fifo_enq_tag[
                    req_bank[lane]
                ][
                    lane*TAG_WIDTH
                    +:
                    TAG_WIDTH
                ]
                =
                req_tag[
                    lane*TAG_WIDTH
                    +:
                    TAG_WIDTH
                ];

            end

        end

    end

    // --------------------------------------------------------
    // FIFOs
    // --------------------------------------------------------

    genvar b;

    generate

        for (
            b = 0;
            b < NUM_BANKS;
            b = b + 1
        ) begin : BANK_FIFO

            bank_fifo #(
                .ADDR_WIDTH(ADDR_WIDTH),
                .TAG_WIDTH(TAG_WIDTH),
                .DEPTH(FIFO_DEPTH),
                .ENQ_WIDTH(ENQ_WIDTH)
            ) fifo_inst (

                .clk(clk),

                .rst(rst),

                .enq_valid(
                    fifo_enq_valid[b]
                ),

                .enq_addr(
                    fifo_enq_addr[b]
                ),

                .enq_tag(
                    fifo_enq_tag[b]
                ),

                .service_enable(1'b1),

                .service_valid(
                    fifo_service_valid[b]
                ),

                .service_addr(
                    fifo_service_addr[b]
                ),

                .service_tag(
                    fifo_service_tag[b]
                ),

                .count(),

                .overflow(
                    fifo_overflow[b]
                )

            );

        end

    endgenerate

    // --------------------------------------------------------
    // SRAM READ
    // --------------------------------------------------------

    always_ff @(posedge clk) begin

        if (rst) begin

            rsp_valid <= '0;

            rsp_data <= '0;

            rsp_tag <= '0;

        end
        else begin

            for (
                bank = 0;
                bank < NUM_BANKS;
                bank = bank + 1
            ) begin

                if (
                    fifo_service_valid[bank]
                ) begin

                    rsp_valid[bank] <= 1'b1;

                    rsp_data[
                        bank*8
                        +:
                        8
                    ] <=
                        mem[bank][
                            fifo_service_addr[bank]
                        ];

                    rsp_tag[
                        bank*TAG_WIDTH
                        +:
                        TAG_WIDTH
                    ] <=
                        fifo_service_tag[bank];

                end
                else begin

                    rsp_valid[bank] <= 1'b0;

                    rsp_data[
                        bank*8
                        +:
                        8
                    ] <= '0;

                    rsp_tag[
                        bank*TAG_WIDTH
                        +:
                        TAG_WIDTH
                    ] <= '0;

                end

            end

        end

    end

    // --------------------------------------------------------
    // OVERFLOW
    // --------------------------------------------------------

    always_comb begin

        overflow = 1'b0;

        for (
            bank = 0;
            bank < NUM_BANKS;
            bank = bank + 1
        ) begin

            if (fifo_overflow[bank])
                overflow = 1'b1;

        end

    end

endmodule
