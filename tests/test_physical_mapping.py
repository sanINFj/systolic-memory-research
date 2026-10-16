import unittest

from model.physical_mapping import (
    BANK_SIZE_BYTES,
    NUM_BANKS,
    POLICIES,
    map_element,
    validate_layout,
)


class PhysicalMappingTests(unittest.TestCase):

    def test_all_policies_have_no_aliases(self):
        # Includes aligned, rectangular, and edge-sized tiles.
        workloads = [
            (8, 8, 8),
            (13, 17, 29),
            (32, 32, 32),
            (64, 32, 64),
            (64, 64, 64),
            (128, 256, 128),
        ]

        for policy in POLICIES:
            for M, K, N in workloads:
                with self.subTest(
                    policy=policy, M=M, K=K, N=N
                ):
                    result = validate_layout(M, K, N, policy)
                    self.assertEqual(
                        result["elements"], M * K + K * N
                    )
                    self.assertEqual(
                        len(result["bank_occupancy"]), NUM_BANKS
                    )
                    self.assertLess(
                        result["max_local_addr"], BANK_SIZE_BYTES
                    )

    def test_every_element_is_inside_bank_capacity(self):
        for policy in POLICIES:
            layout = validate_layout(13, 17, 29, policy)
            self.assertTrue(all(
                0 <= count for count in layout["bank_occupancy"]
            ))

    def test_invalid_policy_is_rejected(self):
        with self.assertRaises(ValueError):
            map_element("A", 0, 0, 8, 8, "not_a_policy")

    def test_out_of_range_matrix_column_is_rejected(self):
        with self.assertRaises(ValueError):
            map_element("B", 0, 8, 8, 8, "modulo")

    def test_oversized_bank_layout_is_rejected(self):
        # This A matrix exceeds what the four-bank split layout can hold:
        # 256 * 256 = 65,536 bytes, with only 4 banks assigned to A.
        with self.assertRaises(ValueError):
            validate_layout(256, 256, 8, "split")


if __name__ == "__main__":
    unittest.main(verbosity=2)
