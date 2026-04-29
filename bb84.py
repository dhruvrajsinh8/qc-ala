"""
bb84.py — Core BB84 Quantum Key Distribution Protocol
======================================================
Simulates the full BB84 protocol between Alice (sender) and Bob (receiver),
including optional Eve (eavesdropper) interception.
"""

import random
import numpy as np
from typing import Optional


# ---------------------------------------------------------------------------
# Quantum bit helpers
# ---------------------------------------------------------------------------

RECTILINEAR = 0   # basis: |0⟩ / |1⟩
DIAGONAL    = 1   # basis: |+⟩ / |−⟩


def prepare_qubit(bit: int, basis: int) -> dict:
    """
    Alice prepares a qubit.

    Parameters
    ----------
    bit   : classical bit value (0 or 1)
    basis : RECTILINEAR or DIAGONAL

    Returns
    -------
    dict representing a simulated qubit with its hidden state.
    """
    return {"bit": bit, "basis": basis}


def measure_qubit(qubit: dict, basis: int) -> int:
    """
    Bob (or Eve) measures a qubit in a chosen basis.

    If the measurement basis matches the preparation basis the result is
    deterministic; otherwise the outcome is uniformly random.

    Parameters
    ----------
    qubit : dict returned by prepare_qubit
    basis : the basis used for measurement

    Returns
    -------
    Measured bit (0 or 1).
    """
    if basis == qubit["basis"]:
        return qubit["bit"]
    return random.randint(0, 1)


# ---------------------------------------------------------------------------
# Alice
# ---------------------------------------------------------------------------

class Alice:
    """Generates random bits & bases, prepares qubits."""

    def __init__(self, n_bits: int):
        self.n_bits = n_bits
        self.bits   = [random.randint(0, 1) for _ in range(n_bits)]
        self.bases  = [random.randint(0, 1) for _ in range(n_bits)]
        self.qubits = [prepare_qubit(b, ba)
                       for b, ba in zip(self.bits, self.bases)]

    def send_qubits(self) -> list:
        """Returns the list of prepared qubits (the quantum channel payload)."""
        return self.qubits


# ---------------------------------------------------------------------------
# Eve  (optional eavesdropper)
# ---------------------------------------------------------------------------

class Eve:
    """
    Intercept-and-resend eavesdropper.
    Eve measures each qubit in a randomly chosen basis, then re-prepares and
    forwards a new qubit — inevitably introducing errors when her basis differs
    from Alice's.
    """

    def __init__(self):
        self.intercepted_bits  = []
        self.intercepted_bases = []

    def intercept(self, qubits: list) -> list:
        """
        Intercept all qubits, measure them, and forward new qubits.

        Parameters
        ----------
        qubits : list of qubit dicts from Alice

        Returns
        -------
        List of new qubit dicts forwarded toward Bob.
        """
        forwarded = []
        self.intercepted_bits  = []
        self.intercepted_bases = []

        for q in qubits:
            eve_basis = random.randint(0, 1)
            eve_bit   = measure_qubit(q, eve_basis)
            self.intercepted_bits.append(eve_bit)
            self.intercepted_bases.append(eve_basis)
            # Re-prepare and forward
            forwarded.append(prepare_qubit(eve_bit, eve_basis))

        return forwarded


# ---------------------------------------------------------------------------
# Bob
# ---------------------------------------------------------------------------

class Bob:
    """Measures received qubits in randomly chosen bases."""

    def __init__(self, n_bits: int):
        self.n_bits = n_bits
        self.bases  = [random.randint(0, 1) for _ in range(n_bits)]
        self.bits   = []

    def measure(self, qubits: list) -> list:
        """
        Measure each qubit in Bob's randomly chosen basis.

        Parameters
        ----------
        qubits : list of qubit dicts received over the (possibly tampered)
                 quantum channel

        Returns
        -------
        List of measured bit values.
        """
        self.bits = [measure_qubit(q, b)
                     for q, b in zip(qubits, self.bases)]
        return self.bits
