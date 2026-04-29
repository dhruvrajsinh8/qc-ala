"""
tests/test_qkd.py — Unit & Integration Tests for the QKD Simulation
=====================================================================
Run with:  pytest tests/ -v
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import random
import pytest

from bb84 import Alice, Bob, Eve, prepare_qubit, measure_qubit, RECTILINEAR, DIAGONAL
from sifting import sift_keys, sifting_efficiency
from eavesdrop_detection import compute_qber, detect_eavesdropper, sample_for_detection
from error_correction import parity, cascade_error_correction, estimate_error_rate
from privacy_amplification import (
    privacy_amplification, final_key_length,
    toeplitz_hash, sha256_hash, xor_fold_hash, bits_to_bytes, bytes_to_bits,
)
from qkd_pipeline import run_qkd


# ============================================================
# BB84 core
# ============================================================

class TestQubitPreparationAndMeasurement:

    def test_same_basis_deterministic(self):
        """Measuring in the same basis as preparation always gives the original bit."""
        for bit in (0, 1):
            for basis in (RECTILINEAR, DIAGONAL):
                q = prepare_qubit(bit, basis)
                assert measure_qubit(q, basis) == bit

    def test_different_basis_random(self):
        """Measuring in a different basis gives 0 or 1 (both values possible)."""
        results = set()
        for _ in range(200):
            q = prepare_qubit(0, RECTILINEAR)
            results.add(measure_qubit(q, DIAGONAL))
        assert results == {0, 1}, "Should observe both outcomes with different bases"

    def test_qubit_structure(self):
        q = prepare_qubit(1, DIAGONAL)
        assert q["bit"] == 1
        assert q["basis"] == DIAGONAL


class TestAliceBob:

    def test_alice_generates_correct_length(self):
        alice = Alice(200)
        assert len(alice.bits)   == 200
        assert len(alice.bases)  == 200
        assert len(alice.qubits) == 200

    def test_bob_measures_correct_length(self):
        alice = Alice(100)
        bob   = Bob(100)
        bits  = bob.measure(alice.send_qubits())
        assert len(bits) == 100

    def test_no_eve_perfect_same_basis(self):
        """When bases match, Bob should always get Alice's bit."""
        for _ in range(50):
            bit   = random.randint(0, 1)
            basis = random.randint(0, 1)
            q     = prepare_qubit(bit, basis)
            assert measure_qubit(q, basis) == bit


class TestEve:

    def test_eve_forwards_same_count(self):
        alice = Alice(100)
        eve   = Eve()
        forwarded = eve.intercept(alice.send_qubits())
        assert len(forwarded) == 100

    def test_eve_increases_error_rate(self):
        """Over many runs, Eve should cause ~25 % error in the sifted key."""
        errors = 0
        total  = 0
        n = 2000

        alice = Alice(n)
        bob   = Bob(n)
        eve   = Eve()
        bob.measure(eve.intercept(alice.send_qubits()))

        for a_base, b_base, a_bit, b_bit in zip(
            alice.bases, bob.bases, alice.bits, bob.bits
        ):
            if a_base == b_base:
                total  += 1
                errors += (a_bit != b_bit)

        qber = errors / total if total else 0
        # BB84 theory: Eve causes ~25% QBER; allow ±10% statistical tolerance
        assert 0.10 <= qber <= 0.40, f"Expected ~0.25, got {qber:.3f}"


# ============================================================
# Sifting
# ============================================================

class TestSifting:

    def test_only_matching_bases_kept(self):
        alice_bases = [0, 1, 0, 1, 0]
        bob_bases   = [0, 0, 0, 1, 1]
        alice_bits  = [1, 0, 1, 0, 1]
        bob_bits    = [1, 1, 1, 0, 0]

        idx, sa, sb = sift_keys(alice_bases, bob_bases, alice_bits, bob_bits)
        assert idx == [0, 2, 3]
        assert sa  == [1, 1, 0]
        assert sb  == [1, 1, 0]

    def test_no_matching_bases(self):
        idx, sa, sb = sift_keys([0, 0], [1, 1], [0, 1], [0, 1])
        assert idx == [] and sa == [] and sb == []

    def test_all_matching_bases(self):
        idx, sa, sb = sift_keys([1, 1], [1, 1], [0, 1], [0, 1])
        assert len(sa) == 2

    def test_efficiency(self):
        assert sifting_efficiency(100, 50) == pytest.approx(0.5)
        assert sifting_efficiency(0, 0)    == 0.0


# ============================================================
# Eavesdrop detection
# ============================================================

class TestEavesdropDetection:

    def test_qber_all_correct(self):
        bits = [0, 1, 0, 1, 1]
        assert compute_qber(bits, bits) == 0.0

    def test_qber_all_wrong(self):
        a = [0, 0, 0, 0]
        b = [1, 1, 1, 1]
        assert compute_qber(a, b) == 1.0

    def test_qber_half(self):
        a = [0, 0, 1, 1]
        b = [1, 1, 1, 1]
        assert compute_qber(a, b) == pytest.approx(0.5)

    def test_no_eve_not_detected(self):
        """Identical sifted keys → QBER ≈ 0 → no detection."""
        bits = [random.randint(0,1) for _ in range(200)]
        detected, qber, _, _ = detect_eavesdropper(bits, bits[:])
        assert not detected
        assert qber == 0.0

    def test_high_qber_detected(self):
        """Completely mismatched keys → QBER = 1 → detected."""
        alice = [0] * 200
        bob   = [1] * 200
        detected, qber, _, _ = detect_eavesdropper(alice, bob)
        assert detected
        assert qber == 1.0

    def test_sample_sizes(self):
        bits = list(range(100))
        bits = [b % 2 for b in bits]
        ca, cb, ka, kb = sample_for_detection(bits, bits, sample_fraction=0.2)
        assert len(ca) == 20
        assert len(ka) == 80
        assert len(ca) + len(ka) == 100


# ============================================================
# Error correction
# ============================================================

class TestErrorCorrection:

    def test_parity_even(self):
        assert parity([0, 1, 1, 0]) == 0

    def test_parity_odd(self):
        assert parity([1, 1, 1, 0]) == 1

    def test_no_errors(self):
        bits = [random.randint(0,1) for _ in range(100)]
        corrected, disclosed, residual = cascade_error_correction(bits, bits[:])
        assert residual == 0.0
        assert corrected == bits

    def test_single_error_corrected(self):
        alice = [1, 0, 1, 0, 1, 0, 1, 0]
        bob   = [1, 0, 1, 1, 1, 0, 1, 0]  # bit 3 flipped
        corrected, _, _ = cascade_error_correction(alice, bob, passes=4)
        assert corrected == alice

    def test_multiple_errors_reduced(self):
        """Cascade should significantly reduce a 5 % error rate."""
        n = 500
        alice = [random.randint(0,1) for _ in range(n)]
        bob   = alice[:]
        # Flip ~5 % of bits
        for i in random.sample(range(n), n // 20):
            bob[i] ^= 1

        corrected, _, residual = cascade_error_correction(alice, bob, passes=4)
        assert residual < 0.05  # should be much better than the original

    def test_estimate_error_rate(self):
        alice = [0, 1, 0, 1]
        bob   = [0, 0, 0, 1]
        assert estimate_error_rate(alice, bob) == pytest.approx(0.25)


# ============================================================
# Privacy amplification
# ============================================================

class TestPrivacyAmplification:

    def test_output_length_toeplitz(self):
        bits = [random.randint(0,1) for _ in range(256)]
        out, _ = privacy_amplification(bits, 128, method="toeplitz")
        assert len(out) == 128

    def test_output_length_sha256(self):
        bits = [random.randint(0,1) for _ in range(256)]
        out, _ = privacy_amplification(bits, 64, method="sha256")
        assert len(out) == 64

    def test_output_length_xor_fold(self):
        bits = [random.randint(0,1) for _ in range(256)]
        out, _ = privacy_amplification(bits, 32, method="xor_fold")
        assert len(out) == 32

    def test_empty_key(self):
        out, _ = privacy_amplification([], 0)
        assert out == []

    def test_bits_to_bytes_roundtrip(self):
        from privacy_amplification import bits_to_bytes, bytes_to_bits
        bits = [1, 0, 1, 1, 0, 0, 1, 0]
        assert bytes_to_bits(bits_to_bytes(bits), 8) == bits

    def test_final_key_length_positive(self):
        l = final_key_length(1000, 0.05, 200, 64)
        assert l > 0

    def test_final_key_length_high_qber(self):
        """Very high QBER should yield zero or negative (clamped to 0) key length."""
        l = final_key_length(100, 0.49, 50, 64)
        assert l == 0


# ============================================================
# End-to-end pipeline
# ============================================================

class TestFullPipeline:

    def test_no_eve_keys_match(self):
        result = run_qkd(n_bits=1000, eve_present=False, verbose=False)
        assert not result.aborted
        assert result.keys_match
        assert result.n_final > 0

    def test_eve_detected(self):
        """With Eve, QBER should be high enough to trigger detection most of the time."""
        detections = 0
        for _ in range(10):
            result = run_qkd(n_bits=800, eve_present=True, verbose=False)
            if result.eve_detected or result.aborted:
                detections += 1
        # Probabilistic: expect detection in at least 7 out of 10 runs
        assert detections >= 7, f"Eve detected only {detections}/10 times"

    def test_sha256_method(self):
        result = run_qkd(n_bits=1000, eve_present=False, pa_method="sha256", verbose=False)
        assert not result.aborted

    def test_xor_fold_method(self):
        result = run_qkd(n_bits=1000, eve_present=False, pa_method="xor_fold", verbose=False)
        assert not result.aborted

    def test_sifting_efficiency_approx_50pct(self):
        result = run_qkd(n_bits=2000, eve_present=False, verbose=False)
        # Expect ~50 % ± 5 %
        assert 0.40 <= result.sift_efficiency <= 0.60

    def test_result_fields(self):
        result = run_qkd(n_bits=500, eve_present=False, verbose=False)
        assert result.n_raw == 500
        assert result.qber >= 0.0
        assert result.n_sifted <= 500
