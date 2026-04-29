"""
qkd_pipeline.py — Full End-to-End QKD Simulation Pipeline
===========================================================
Orchestrates all stages of the BB84 QKD protocol:

  Stage 1  Raw key generation (Alice, optional Eve, Bob)
  Stage 2  Basis sifting
  Stage 3  Eavesdropping detection (QBER check)
  Stage 4  Error correction (Cascade-lite)
  Stage 5  Privacy amplification → final secret key
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List, Optional

from bb84 import Alice, Bob, Eve
from sifting import sift_keys, sifting_efficiency
from eavesdrop_detection import detect_eavesdropper
from error_correction import cascade_error_correction
from privacy_amplification import privacy_amplification, final_key_length


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class QKDResult:
    """Holds statistics and the final keys from one QKD run."""

    # Configuration
    n_bits:           int  = 0
    eve_present:      bool = False
    pa_method:        str  = "toeplitz"

    # Stage 1 – Raw generation
    n_raw:            int  = 0

    # Stage 2 – Sifting
    n_sifted:         int  = 0
    sift_efficiency:  float = 0.0

    # Stage 3 – Eavesdrop detection
    qber:             float = 0.0
    eve_detected:     bool  = False
    aborted:          bool  = False

    # Stage 4 – Error correction
    n_after_ec:       int   = 0
    disclosed_bits:   int   = 0
    residual_error:   float = 0.0

    # Stage 5 – Privacy amplification
    n_final:          int   = 0
    final_key_alice:  List[int] = field(default_factory=list)
    final_key_bob:    List[int] = field(default_factory=list)
    keys_match:       bool  = False


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run_qkd(
    n_bits:            int  = 1000,
    eve_present:       bool = False,
    pa_method:         str  = "toeplitz",
    sample_fraction:   float = 0.1,
    ec_passes:         int   = 4,
    security_param:    int   = 64,
    verbose:           bool  = True,
) -> QKDResult:
    """
    Execute the complete BB84 QKD protocol.

    Parameters
    ----------
    n_bits          : number of qubits Alice transmits
    eve_present     : if True, Eve intercepts every qubit
    pa_method       : privacy amplification method ("toeplitz"|"sha256"|"xor_fold")
    sample_fraction : fraction of sifted bits used for QBER estimation
    ec_passes       : number of Cascade error-correction passes
    security_param  : security parameter (bits) for key-length calculation
    verbose         : print step-by-step summary

    Returns
    -------
    QKDResult dataclass with all statistics and final keys.
    """
    res = QKDResult(n_bits=n_bits, eve_present=eve_present, pa_method=pa_method)

    # ------------------------------------------------------------------
    # Stage 1: Raw key generation
    # ------------------------------------------------------------------
    if verbose:
        print("=" * 60)
        print("BB84 QKD Simulation")
        print("=" * 60)
        print(f"\n[Stage 1] Raw key generation — {n_bits} qubits")

    alice = Alice(n_bits)
    bob   = Bob(n_bits)

    qubits = alice.send_qubits()

    if eve_present:
        eve    = Eve()
        qubits = eve.intercept(qubits)
        if verbose:
            print("  ⚠  Eve is intercepting the quantum channel!")

    bob.measure(qubits)
    res.n_raw = n_bits

    if verbose:
        print(f"  Alice's raw bits (first 10): {alice.bits[:10]}")
        print(f"  Bob's   raw bits (first 10): {bob.bits[:10]}")

    # ------------------------------------------------------------------
    # Stage 2: Basis sifting
    # ------------------------------------------------------------------
    if verbose:
        print(f"\n[Stage 2] Basis sifting")

    _, sifted_alice, sifted_bob = sift_keys(
        alice.bases, bob.bases, alice.bits, bob.bits
    )
    res.n_sifted       = len(sifted_alice)
    res.sift_efficiency = sifting_efficiency(n_bits, res.n_sifted)

    if verbose:
        print(f"  Matching bases : {res.n_sifted}/{n_bits} "
              f"({res.sift_efficiency:.1%})")
        print(f"  Sifted key (first 10): {sifted_alice[:10]}")

    # ------------------------------------------------------------------
    # Stage 3: Eavesdrop detection
    # ------------------------------------------------------------------
    if verbose:
        print(f"\n[Stage 3] Eavesdrop detection (sample={sample_fraction:.0%})")

    res.eve_detected, res.qber, key_alice, key_bob = detect_eavesdropper(
        sifted_alice, sifted_bob, sample_fraction=sample_fraction
    )

    if verbose:
        print(f"  QBER : {res.qber:.4f} ({res.qber:.2%})")

    if res.eve_detected:
        res.aborted = True
        if verbose:
            print("  ✗ Eve DETECTED — aborting key exchange!")
        return res

    if verbose:
        print("  ✓ No eavesdropper detected — proceeding")

    # ------------------------------------------------------------------
    # Stage 4: Error correction
    # ------------------------------------------------------------------
    if verbose:
        print(f"\n[Stage 4] Error correction (Cascade, {ec_passes} passes)")

    corrected_bob, res.disclosed_bits, res.residual_error = \
        cascade_error_correction(key_alice, key_bob, passes=ec_passes)

    res.n_after_ec = len(key_alice)

    if verbose:
        print(f"  Bits after detection check : {res.n_after_ec}")
        print(f"  Classical bits disclosed   : {res.disclosed_bits}")
        print(f"  Residual error rate        : {res.residual_error:.4%}")

    # ------------------------------------------------------------------
    # Stage 5: Privacy amplification
    # ------------------------------------------------------------------
    output_len = final_key_length(
        res.n_after_ec, res.qber, res.disclosed_bits, security_param
    )

    if verbose:
        print(f"\n[Stage 5] Privacy amplification ({pa_method})")
        print(f"  Target final key length : {output_len} bits")

    if output_len == 0:
        if verbose:
            print("  ✗ Insufficient bits for a secure key — aborting.")
        res.aborted = True
        return res

    res.final_key_alice, _ = privacy_amplification(key_alice,     output_len, pa_method)
    res.final_key_bob,   _ = privacy_amplification(corrected_bob, output_len, pa_method)
    res.n_final            = output_len

    res.keys_match = (res.final_key_alice == res.final_key_bob)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    if verbose:
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"  Eve present      : {eve_present}")
        print(f"  QBER             : {res.qber:.4f}")
        print(f"  Raw bits         : {res.n_raw}")
        print(f"  Sifted bits      : {res.n_sifted}")
        print(f"  After EC         : {res.n_after_ec}")
        print(f"  Final key length : {res.n_final}")
        print(f"  Keys match       : {res.keys_match}")
        if res.final_key_alice:
            print(f"  Final key (first 16 bits): {res.final_key_alice[:16]}")
        print("=" * 60)

    return res
