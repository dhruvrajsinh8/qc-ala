"""
error_correction.py — Error Correction (Cascade-lite)
=======================================================
Implements a simplified Cascade-style binary error-correction protocol:

  Pass 1  – Divide the key into blocks; compare parities publicly; bisect
             blocks with wrong parity to locate and correct single errors.
  Pass 2+ – Repeat with shuffled blocks to catch errors missed in earlier
             passes and to correct errors that propagated during bisection.

Only *parities* (XOR of all bits in a block) are disclosed, not the bits
themselves, preserving most of the secrecy.
"""

import math
import random
from copy import deepcopy
from typing import List, Tuple


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parity(bits: List[int]) -> int:
    """Return XOR parity of a list of bits."""
    result = 0
    for b in bits:
        result ^= b
    return result


def block_parity_compare(
    alice_bits: List[int],
    bob_bits:   List[int],
    start: int,
    end:   int,
) -> bool:
    """Return True if parities of the slice [start, end) differ."""
    return parity(alice_bits[start:end]) != parity(bob_bits[start:end])


# ---------------------------------------------------------------------------
# Binary search correction
# ---------------------------------------------------------------------------

def _bisect_correct(
    alice_bits: List[int],
    bob_bits:   List[int],
    start: int,
    end:   int,
    disclosed_count: List[int],
) -> None:
    """
    Recursively bisect a block to locate and flip a single error in bob_bits.
    Each parity comparison costs one classical bit of information (counted in
    disclosed_count[0]).
    """
    if end - start == 1:
        # Found the erroneous bit — flip it
        bob_bits[start] ^= 1
        return

    mid = (start + end) // 2
    disclosed_count[0] += 1

    if block_parity_compare(alice_bits, bob_bits, start, mid):
        _bisect_correct(alice_bits, bob_bits, start, mid, disclosed_count)
    else:
        _bisect_correct(alice_bits, bob_bits, mid,   end, disclosed_count)


# ---------------------------------------------------------------------------
# Single Cascade pass
# ---------------------------------------------------------------------------

def _cascade_pass(
    alice_bits:      List[int],
    bob_bits:        List[int],
    block_size:      int,
    indices:         List[int],
    disclosed_count: List[int],
) -> int:
    """
    One pass of the Cascade protocol over a (possibly shuffled) index mapping.

    Parameters
    ----------
    alice_bits      : Alice's reference bits (in original positions)
    bob_bits        : Bob's bits to be corrected (modified in-place)
    block_size      : number of bits per block
    indices         : permutation mapping pass-positions → original positions
    disclosed_count : mutable counter of classical bits disclosed

    Returns
    -------
    Number of errors corrected in this pass.
    """
    n = len(alice_bits)
    errors_fixed = 0

    # Build re-ordered views
    alice_perm = [alice_bits[i] for i in indices]
    bob_perm   = [bob_bits[i]   for i in indices]

    pos = 0
    while pos < n:
        blk_end = min(pos + block_size, n)
        disclosed_count[0] += 1  # parity comparison

        if parity(alice_perm[pos:blk_end]) != parity(bob_perm[pos:blk_end]):
            # Error detected in this block — bisect
            _bisect_correct(alice_perm, bob_perm, pos, blk_end, disclosed_count)
            errors_fixed += 1

            # Write corrections back to original positions
            for rel, orig in enumerate(indices[pos:blk_end]):
                bob_bits[orig] = bob_perm[pos + rel]

        pos += block_size

    return errors_fixed


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def cascade_error_correction(
    alice_bits: List[int],
    bob_bits:   List[int],
    passes:     int = 4,
) -> Tuple[List[int], int, float]:
    """
    Run the Cascade error-correction protocol.

    Parameters
    ----------
    alice_bits : Alice's sifted key (reference, not modified)
    bob_bits   : Bob's sifted key (corrected in-place)
    passes     : number of Cascade passes (default 4)

    Returns
    -------
    corrected_bob   : Bob's corrected key
    disclosed_bits  : total classical bits revealed during correction
    residual_error  : fraction of bits still wrong after correction
    """
    n = len(alice_bits)
    if n == 0:
        return [], 0, 0.0

    corrected = deepcopy(bob_bits)
    disclosed = [0]  # mutable counter

    for p in range(passes):
        # Block size doubles each pass (standard Cascade schedule)
        block_size = max(1, 2 ** p)

        # Shuffle indices for passes > 0 to catch previously missed errors
        indices = list(range(n))
        if p > 0:
            random.shuffle(indices)

        _cascade_pass(alice_bits, corrected, block_size, indices, disclosed)

    # Compute residual error rate
    remaining_errors = sum(a != b for a, b in zip(alice_bits, corrected))
    residual_error   = remaining_errors / n if n else 0.0

    return corrected, disclosed[0], residual_error


def estimate_error_rate(
    alice_sample: List[int],
    bob_sample:   List[int],
) -> float:
    """
    Estimate QBER from a public sample of matching-basis bits.

    Parameters
    ----------
    alice_sample : Alice's bits (subset sacrificed for QBER estimation)
    bob_sample   : Bob's corresponding bits

    Returns
    -------
    Estimated Quantum Bit Error Rate (QBER) in [0, 1].
    """
    if not alice_sample:
        return 0.0
    errors = sum(a != b for a, b in zip(alice_sample, bob_sample))
    return errors / len(alice_sample)
