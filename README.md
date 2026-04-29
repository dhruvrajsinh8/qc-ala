# BB84 Quantum Key Distribution — Full End-to-End Simulation

> **ALA Individual Assignment** — End-to-End QKD Simulation  
> Extends the basic BB84 lab implementation with basis sifting, error correction, and privacy amplification.

---

## Overview

This project simulates the complete **BB84 Quantum Key Distribution (QKD)** protocol in pure Python.  
Starting from raw qubit transmission, it walks through every stage a real QKD system must perform before Alice and Bob can share a secret key.

```
Alice ──[qubits]──▶ (Eve?) ──▶ Bob
         │                       │
         └──── Classical Channel (public) ────┘
                  Sifting → QBER check → Error Correction → Privacy Amplification
                                                               │
                                                          Final Secret Key
```

---

## Protocol Stages

| # | Stage | File | Description |
|---|-------|------|-------------|
| 1 | **Raw Key Generation** | `src/bb84.py` | Alice generates random bits & bases, prepares qubits; Bob measures in random bases; Eve optionally intercepts (intercept-and-resend attack) |
| 2 | **Basis Sifting** | `src/sifting.py` | Alice & Bob compare bases over the public channel; only matching-basis bits are kept (~50 % retained) |
| 3 | **Eavesdrop Detection** | `src/eavesdrop_detection.py` | A random sample of sifted bits is sacrificed to compute the **QBER**; if QBER > 11 % the session is aborted |
| 4 | **Error Correction** | `src/error_correction.py` | A simplified **Cascade** protocol corrects residual bit errors using binary bisection on parity-mismatched blocks |
| 5 | **Privacy Amplification** | `src/privacy_amplification.py` | The corrected key is compressed using a **Toeplitz-matrix universal hash** (or SHA-256 / XOR-fold) to eliminate Eve's partial knowledge |

---

## Project Structure

```
qkd-simulation/
├── main.py                        # CLI entry point
├── requirements.txt
├── README.md
├── src/
│   ├── bb84.py                    # Alice, Bob, Eve + qubit helpers
│   ├── sifting.py                 # Basis sifting
│   ├── eavesdrop_detection.py     # QBER estimation & abort logic
│   ├── error_correction.py        # Cascade-lite error correction
│   ├── privacy_amplification.py   # Toeplitz / SHA-256 / XOR-fold hashing
│   └── qkd_pipeline.py            # Full orchestration pipeline
├── tests/
│   └── test_qkd.py                # 37 unit + integration tests (pytest)
└── examples/
    └── compare_scenarios.py       # Side-by-side scenario comparison
```

---

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/<your-username>/qkd-simulation.git
cd qkd-simulation
pip install -r requirements.txt
```

### 2. Run the Demo

```bash
python main.py --demo
```

This runs three scenarios: no Eve, Eve present, and SHA-256 amplification.

### 3. Custom Run

```bash
# Basic run — 1000 qubits, no Eve
python main.py --bits 1000

# With Eve intercepting
python main.py --bits 2000 --eve

# Change privacy amplification method
python main.py --bits 1500 --method sha256
```

### 4. Run Tests

```bash
pytest tests/ -v
```

All 37 tests should pass.

---

## Key Parameters

| Flag | Default | Description |
|------|---------|-------------|
| `--bits` | 1000 | Number of qubits Alice transmits |
| `--eve` | False | Enable Eve (intercept-and-resend eavesdropper) |
| `--method` | `toeplitz` | Privacy amplification: `toeplitz`, `sha256`, `xor_fold` |
| `--sample` | 0.10 | Fraction of sifted bits used for QBER estimation |
| `--passes` | 4 | Number of Cascade error-correction passes |
| `--security` | 64 | Security parameter (bits) for key-length formula |

---

## Sample Output

### No Eve

```
============================================================
BB84 QKD Simulation
============================================================

[Stage 1] Raw key generation — 1000 qubits
[Stage 2] Basis sifting
  Matching bases : 512/1000 (51.2%)
[Stage 3] Eavesdrop detection (sample=10%)
  QBER : 0.0000 (0.00%)
  ✓ No eavesdropper detected — proceeding
[Stage 4] Error correction (Cascade, 4 passes)
  Residual error rate : 0.0000%
[Stage 5] Privacy amplification (toeplitz)
  Target final key length : 448 bits
============================================================
SUMMARY
  Eve present      : False
  QBER             : 0.0000
  Raw bits         : 1000
  Sifted bits      : 512
  Final key length : 448
  Keys match       : True
============================================================
```

### With Eve

```
[Stage 1] Raw key generation — 1000 qubits
  ⚠  Eve is intercepting the quantum channel!
[Stage 3] Eavesdrop detection (sample=10%)
  QBER : 0.2549 (25.49%)
  ✗ Eve DETECTED — aborting key exchange!
```

---

## Theory Notes

### QBER Threshold
The theoretical maximum QBER for secure key generation under **individual attacks** is ~11 % (BB84 with one-way error correction).  
This simulation uses 11 % as the abort threshold.  For coherent attacks, the threshold drops to ~7.1 %.

### Key Length Formula
The safe final key length follows the Shor-Preskill / GLLP formula:

```
l ≤ n · (1 − h(e)) − security_param
```

where `h(e) = −e log₂ e − (1−e) log₂(1−e)` is the binary entropy of the QBER.

### Privacy Amplification Methods
| Method | Security | Speed | Notes |
|--------|----------|-------|-------|
| `toeplitz` | Information-theoretic | Medium | Recommended; uses fixed public seed |
| `sha256` | Computational | Fast | HMAC-SHA256 with fixed public salt |
| `xor_fold` | Illustrative only | Fast | **Not** cryptographically secure |

---

## References

1. Bennett, C. H. & Brassard, G. (1984). *Quantum cryptography: Public key distribution and coin tossing.*
2. Shor, P. W. & Preskill, J. (2000). *Simple proof of security of the BB84 quantum key distribution protocol.*
3. Brassard, G. & Salvail, L. (1994). *Secret-key reconciliation by public discussion.* (Cascade protocol)
4. Carter, J. L. & Wegman, M. N. (1979). *Universal classes of hash functions.* (Toeplitz hashing)

---

## License

MIT License — free to use for academic and educational purposes.
