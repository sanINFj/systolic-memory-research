`timescale 1ns/1ps

module bank_mapper_physical_tb;

    reg        is_A;
    reg [7:0]  row;
    reg [7:0]  index;
    reg [15:0] K;
    reg [15:0] N;

    wire [2:0] bank0, bank1, bank2, bank3;
    wire [12:0] addr0, addr1, addr2, addr3;

    integer errors;
    reg seen [0:3][0:7][0:8191];

    bank_mapper #(.BANK_POLICY(0)) m0
        (is_A, row, index, K, N, bank0, addr0);
    bank_mapper #(.BANK_POLICY(1)) m1
        (is_A, row, index, K, N, bank1, addr1);
    bank_mapper #(.BANK_POLICY(2)) m2
        (is_A, row, index, K, N, bank2, addr2);
    bank_mapper #(.BANK_POLICY(3)) m3
        (is_A, row, index, K, N, bank3, addr3);

    task automatic check_element;
        integer eb [0:3];
        integer ea [0:3];
        integer ab [0:3];
        integer aa [0:3];
        integer raw [0:3];
        integer global_byte;
        integer groups;
        integer p;

        begin
            #1;

            ab[0] = bank0; ab[1] = bank1;
            ab[2] = bank2; ab[3] = bank3;

            aa[0] = addr0; aa[1] = addr1;
            aa[2] = addr2; aa[3] = addr3;

            raw[0] = m0.local_full;
            raw[1] = m1.local_full;
            raw[2] = m2.local_full;
            raw[3] = m3.local_full;

            // Independently calculate expected addresses.
            // Policy 0: global byte address, interleaved over 8 banks.
            if (is_A)
                global_byte = row * K + index;
            else
                global_byte = 32768 + row * N + index;

            eb[0] = global_byte % 8;
            ea[0] = global_byte / 8;

            // Policy 1: A uses banks 0-3; B uses banks 4-7.
            if (is_A) begin
                eb[1] = row % 4;
                ea[1] = (row / 4) * K + index;
            end
            else begin
                eb[1] = 4 + (index % 4);
                groups = (N + 3) / 4;
                ea[1] = row * groups + (index / 4);
            end

            // Policy 2: A is row-banked; B is column-banked.
            if (is_A) begin
                eb[2] = row % 8;
                ea[2] = (row / 8) * K + index;
            end
            else begin
                eb[2] = (index + 4) % 8;
                groups = (N + 7) / 8;
                ea[2] = 4096 + row * groups + (index / 8);
            end

            // Policy 3: XOR bank selection with compact local indexing.
            if (is_A) begin
                eb[3] = (row % 8) ^ (index % 8);
                groups = (K + 7) / 8;
                ea[3] = (row / 8) * groups * 8
                      + (index / 8) * 8
                      + (row % 8);
            end
            else begin
                eb[3] = (row % 8) ^ (index % 8);
                groups = (N + 7) / 8;
                ea[3] = 4096
                      + (row / 8) * groups * 8
                      + (index / 8) * 8
                      + (row % 8);
            end

            for (p = 0; p < 4; p = p + 1) begin

                if (ab[p] != eb[p] || raw[p] != ea[p]) begin
                    $display(
                        "FAIL FORMULA policy=%0d operand=%0d row=%0d index=%0d expected_bank=%0d actual_bank=%0d expected_addr=%0d actual_full_addr=%0d",
                        p, is_A, row, index,
                        eb[p], ab[p], ea[p], raw[p]
                    );
                    errors = errors + 1;
                end

                if (raw[p] < 0 || raw[p] >= 8192) begin
                    $display(
                        "FAIL CAPACITY policy=%0d local_addr=%0d",
                        p, raw[p]
                    );
                    errors = errors + 1;
                end
                else if (seen[p][ab[p]][raw[p]]) begin
                    $display(
                        "FAIL ALIAS policy=%0d bank=%0d addr=%0d operand=%0d row=%0d index=%0d",
                        p, ab[p], raw[p], is_A, row, index
                    );
                    errors = errors + 1;
                end
                else begin
                    seen[p][ab[p]][raw[p]] = 1'b1;
                end

                if (aa[p] != raw[p]) begin
                    $display(
                        "FAIL OUTPUT TRUNCATION policy=%0d output=%0d full=%0d",
                        p, aa[p], raw[p]
                    );
                    errors = errors + 1;
                end
            end
        end
    endtask

    task automatic run_workload;
        input integer M;
        input integer Kdim;
        input integer Ndim;
        integer r;
        integer c;
        integer b;
        integer a;
        integer s;

        begin
            // Reset occupancy before each workload.
            for (b = 0; b < 4; b = b + 1)
                for (a = 0; a < 8; a = a + 1)
                    for (s = 0; s < 8192; s = s + 1)
                        seen[b][a][s] = 1'b0;

            K = Kdim;
            N = Ndim;

            $display(
                "Checking M=%0d K=%0d N=%0d",
                M, Kdim, Ndim
            );

            // Check all A elements.
            is_A = 1'b1;
            for (r = 0; r < M; r = r + 1) begin
                for (c = 0; c < Kdim; c = c + 1) begin
                    row = r;
                    index = c;
                    check_element();
                end
            end

            // Check all B elements.
            is_A = 1'b0;
            for (r = 0; r < Kdim; r = r + 1) begin
                for (c = 0; c < Ndim; c = c + 1) begin
                    row = r;
                    index = c;
                    check_element();
                end
            end
        end
    endtask

    initial begin
        is_A = 1'b1;
        row = 0;
        index = 0;
        K = 1;
        N = 1;
        errors = 0;

        run_workload(8, 8, 8);
        run_workload(13, 17, 29);
        run_workload(128, 256, 128);

        if (errors == 0) begin
            $display("PASS: all policies match expected formulas; no aliases or capacity violations");
            $finish;
        end
        else begin
            $display("FAIL: total errors = %0d", errors);
            $fatal(1);
        end
    end

endmodule
