"""
eavesdrop_detection.py — Eavesdropping Detection
=================================================
Alice and Bob sacrifice a random subset of their sifted key bits to compute
the Quantum Bit Error Rate (QBER).  A QBER above the threshold (~11 %)
indicates the presence of an eavesdropper and the key is aborted.
"""

import random
from typing import List, Tuple


# QBER threshold: theoretical limit for BB84 is ~11 % with individual attacks
QBER_THRESHOLD = 0.11


def sample_for_detection(
    alice_bits: List[int],
    bob_bits:   List[int],
    sample_fraction: float = 0.1,
) -> Tuple[List[int], List[int], List[int], List[int]]:
    """
    Randomly partition the sifted key into a public *check* subset (sacrificed
    for QBER estimation) and a private *key* subset used for the final key.

    Parameters
    ----------
    alice_bits      : Alice's sifted bits
    bob_bits        : Bob's sifted bits
    sample_fraction : fraction of bits to sacrifice (default 10 %)

    Returns
    -------
    check_alice  : Alice's check bits (public)
    check_bob    : Bob's check bits (public)
    key_alice    : remaining Alice bits (private)
    key_bob      : remaining Bob bits (private)
    """
    n = len(alice_bits)
    n_check = max(1, int(n * sample_fraction))

    check_indices = random.sample(range(n), n_check)
    check_set     = set(check_indices)
    key_indices   = [i for i in range(n) if i not in check_set]

    check_alice = [alice_bits[i] for i in check_indices]
    check_bob   = [bob_bits[i]   for i in check_indices]
    key_alice   = [alice_bits[i] for i in key_indices]
    key_bob     = [bob_bits[i]   for i in key_indices]

    return check_alice, check_bob, key_alice, key_bob


def compute_qber(check_alice: List[int], check_bob: List[int]) -> float:
    """
    Compute QBER from the public check bits.

    Returns
    -------
    QBER in [0, 1].
    """
    if not check_alice:
        return 0.0
    errors = sum(a != b for a, b in zip(check_alice, check_bob))
    return errors / len(check_alice)


def detect_eavesdropper(
    alice_bits: List[int],
    bob_bits:   List[int],
    sample_fraction: float = 0.1,
    threshold:       float = QBER_THRESHOLD,
) -> Tuple[bool, float, List[int], List[int]]:
    """
    Full eavesdrop-detection step.

    Parameters
    ----------
    alice_bits      : Alice's sifted bits
    bob_bits        : Bob's sifted bits
    sample_fraction : fraction sacrificed for QBER check
    threshold       : QBER above this value → abort

    Returns
    -------
    eve_detected  : True if QBER > threshold (abort the key)
    qber          : measured QBER
    key_alice     : remaining key bits for Alice (empty if aborted)
    key_bob       : remaining key bits for Bob (empty if aborted)
    """
    check_alice, check_bob, key_alice, key_bob = sample_for_detection(
        alice_bits, bob_bits, sample_fraction
    )
    qber = compute_qber(check_alice, check_bob)

    if qber > threshold:
        return True, qber, [], []

    return False, qber, key_alice, key_bob
