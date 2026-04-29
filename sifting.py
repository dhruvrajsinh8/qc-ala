"""
sifting.py — Basis Sifting
===========================
Alice and Bob compare their bases over the classical (public) channel and keep
only the bits where they used the same basis.  No bit values are revealed.
"""

from typing import List, Tuple


def sift_keys(
    alice_bases: List[int],
    bob_bases:   List[int],
    alice_bits:  List[int],
    bob_bits:    List[int],
) -> Tuple[List[int], List[int], List[int]]:
    """
    Perform basis sifting.

    Parameters
    ----------
    alice_bases : list of bases Alice used
    bob_bases   : list of bases Bob used
    alice_bits  : list of bits Alice sent
    bob_bits    : list of bits Bob measured

    Returns
    -------
    matching_indices : positions where bases agreed
    sifted_alice     : Alice's sifted key
    sifted_bob       : Bob's sifted key
    """
    matching_indices = [
        i for i, (a, b) in enumerate(zip(alice_bases, bob_bases)) if a == b
    ]
    sifted_alice = [alice_bits[i] for i in matching_indices]
    sifted_bob   = [bob_bits[i]   for i in matching_indices]

    return matching_indices, sifted_alice, sifted_bob


def sifting_efficiency(n_original: int, n_sifted: int) -> float:
    """Return the fraction of bits retained after sifting."""
    return n_sifted / n_original if n_original else 0.0
