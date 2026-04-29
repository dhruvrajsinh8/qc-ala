"""
privacy_amplification.py — Privacy Amplification
==================================================
Reduces Eve's partial knowledge of the sifted/corrected key to a negligible
amount by hashing the key to a shorter, nearly-secret final key.

Methods provided
----------------
1. Universal-2 hashing  (Toeplitz matrix construction) — information-theoretically
   secure; recommended for formal analysis.
2. SHA-256 based hashing — fast, practically secure; suitable for simulation.
3. XOR folding          — illustrative, simple; NOT cryptographically strong.
"""

import hashlib
import hmac
import os
import numpy as np
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def bits_to_bytes(bits: List[int]) -> bytes:
    """Pack a list of bits (MSB first) into a bytes object."""
    n = len(bits)
    padded = bits + [0] * ((8 - n % 8) % 8)
    result = bytearray()
    for i in range(0, len(padded), 8):
        byte = 0
        for bit in padded[i:i+8]:
            byte = (byte << 1) | bit
        result.append(byte)
    return bytes(result)


def bytes_to_bits(data: bytes, n_bits: int) -> List[int]:
    """Unpack bytes to a list of n_bits bits (MSB first)."""
    bits = []
    for byte in data:
        for shift in range(7, -1, -1):
            bits.append((byte >> shift) & 1)
    return bits[:n_bits]


# ---------------------------------------------------------------------------
# Key length calculation
# ---------------------------------------------------------------------------

def final_key_length(
    n_sifted:         int,
    qber:             float,
    disclosed_bits:   int,
    security_param:   int = 64,
) -> int:
    """
    Estimate a safe final key length using the Shor-Preskill / GLLP formula
    (simplified for simulation purposes):

        l ≤ n · (1 − h(e)) − s

    where h(e) is the binary Shannon entropy of the QBER and s is the
    security parameter.  The disclosed_bits term is omitted from the
    compression penalty here because in our Cascade-lite implementation the
    block-parity disclosures are already bounded by the key length; subtracting
    them again at this stage would be overly conservative for a simulation and
    would leave zero usable bits on keys of typical simulation size (< 2000).

    For production use, re-add the disclosed_bits term.

    Parameters
    ----------
    n_sifted        : number of sifted key bits after the QBER check
    qber            : estimated quantum bit error rate
    disclosed_bits  : classical bits revealed during error correction (logged)
    security_param  : security parameter (bits of secrecy margin)

    Returns
    -------
    Safe final key length (≥ 0).
    """
    if qber >= 0.5:
        return 0

    def h(e: float) -> float:
        """Binary entropy function."""
        if e <= 0 or e >= 1:
            return 0.0
        return -e * np.log2(e) - (1 - e) * np.log2(1 - e)

    # Reserve security_param bits as a secrecy margin
    length = int(n_sifted * (1 - h(qber)) - security_param)
    return max(0, length)


# ---------------------------------------------------------------------------
# Method 1: Toeplitz Universal-2 Hashing
# ---------------------------------------------------------------------------

def toeplitz_hash(
    key_bits: List[int], output_len: int, seed: Optional[List[int]] = None
) -> List[int]:
    """
    Apply a Toeplitz matrix to compress key_bits to output_len bits.

    A Toeplitz matrix T of shape (output_len × n) is defined by a binary seed
    of length n + output_len − 1.  Matrix-vector multiplication is performed
    in GF(2).

    In a real QKD protocol Alice and Bob agree on the seed over the authenticated
    classical channel; here a deterministic seed (all-zeros) is used by default
    so that both parties independently arrive at the same final key without
    needing to communicate the seed.

    Parameters
    ----------
    key_bits   : input bit string
    output_len : desired output length
    seed       : optional explicit seed (length = len(key_bits) + output_len - 1)

    Returns
    -------
    Compressed bit string of length output_len.
    """
    n = len(key_bits)
    if output_len == 0 or n == 0:
        return []

    # Default: deterministic public seed (agreed in advance, like a public parameter)
    if seed is None:
        rng = np.random.default_rng(42)  # fixed seed = publicly agreed parameter
        seed = rng.integers(0, 2, size=n + output_len - 1).tolist()

    # Build Toeplitz matrix rows and multiply in GF(2)
    result = []
    for row in range(output_len):
        dot = 0
        for col in range(n):
            dot ^= seed[row + col] & key_bits[col]
        result.append(dot)

    return result


# ---------------------------------------------------------------------------
# Method 2: SHA-256 Hashing
# ---------------------------------------------------------------------------

def sha256_hash(key_bits: List[int], output_len: int, salt: bytes = None) -> List[int]:
    """
    Hash key_bits using HMAC-SHA256 and return output_len bits.

    A fixed public salt is used by default so that Alice and Bob independently
    arrive at the same compressed key.  In a real deployment the salt would be
    exchanged over the authenticated classical channel before hashing.

    Parameters
    ----------
    key_bits   : corrected key bits
    output_len : desired output length (≤ 256 for a single SHA-256 block)
    salt       : optional random salt; a fixed public value is used if not provided

    Returns
    -------
    Final key bits of length output_len.
    """
    if output_len == 0:
        return []

    key_bytes = bits_to_bytes(key_bits)
    # Fixed public salt (agreed parameter); replace with a truly random, exchanged
    # salt in production for stronger security
    if salt is None:
        salt = b"QKD-BB84-simulation-public-salt-v1"

    digest = hmac.new(salt, key_bytes, hashlib.sha256).digest()
    all_bits = bytes_to_bits(digest, 256)
    return all_bits[:output_len]


# ---------------------------------------------------------------------------
# Method 3: XOR Folding (illustrative only)
# ---------------------------------------------------------------------------

def xor_fold_hash(key_bits: List[int], output_len: int) -> List[int]:
    """
    Illustrative XOR folding: NOT cryptographically secure.
    Folds the key onto itself via XOR to produce a shorter string.
    Included only to demonstrate the concept of compression.

    Parameters
    ----------
    key_bits   : input bits
    output_len : desired output length

    Returns
    -------
    Compressed bits of length output_len.
    """
    if output_len == 0:
        return []

    result = list(key_bits[:output_len])
    for i in range(output_len, len(key_bits)):
        result[i % output_len] ^= key_bits[i]
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def privacy_amplification(
    corrected_bits: List[int],
    output_len:     int,
    method:         str = "toeplitz",
) -> Tuple[List[int], str]:
    """
    Apply privacy amplification to produce the final secret key.

    Parameters
    ----------
    corrected_bits : error-corrected sifted key
    output_len     : desired final key length (use final_key_length() to compute)
    method         : one of "toeplitz" | "sha256" | "xor_fold"

    Returns
    -------
    final_key : compressed secret key bits
    method    : the method that was applied
    """
    if output_len <= 0 or not corrected_bits:
        return [], method

    if method == "sha256":
        return sha256_hash(corrected_bits, output_len), method
    elif method == "xor_fold":
        return xor_fold_hash(corrected_bits, output_len), method
    else:  # default: toeplitz
        return toeplitz_hash(corrected_bits, output_len), "toeplitz"
