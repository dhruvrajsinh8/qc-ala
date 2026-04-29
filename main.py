#!/usr/bin/env python3
"""
main.py — QKD Simulation Entry Point
=====================================
Run the full BB84 QKD simulation from the command line.

Usage examples
--------------
  python main.py                          # default run, no Eve
  python main.py --bits 2000 --eve       # with Eve present
  python main.py --bits 1500 --method sha256 --verbose
  python main.py --demo                  # runs all three scenarios
"""

import argparse
import sys
import os

# Ensure src/ is on the path when run from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from qkd_pipeline import run_qkd


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="BB84 Quantum Key Distribution Simulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--bits",    type=int,   default=1000,
                        help="Number of qubits to transmit (default: 1000)")
    parser.add_argument("--eve",     action="store_true",
                        help="Enable Eve (eavesdropper) on the quantum channel")
    parser.add_argument("--method",  choices=["toeplitz","sha256","xor_fold"],
                        default="toeplitz",
                        help="Privacy amplification method (default: toeplitz)")
    parser.add_argument("--sample",  type=float, default=0.10,
                        help="Fraction of sifted bits used for QBER check (default: 0.10)")
    parser.add_argument("--passes",  type=int,   default=4,
                        help="Number of Cascade error-correction passes (default: 4)")
    parser.add_argument("--security",type=int,   default=64,
                        help="Security parameter in bits (default: 64)")
    parser.add_argument("--demo",    action="store_true",
                        help="Run three demo scenarios and compare results")
    parser.add_argument("--verbose", action="store_true", default=True,
                        help="Verbose step-by-step output (default: True)")
    parser.add_argument("--quiet",   action="store_true",
                        help="Suppress verbose output")
    return parser.parse_args()


def run_demo():
    """Run three canonical scenarios for demonstration."""
    scenarios = [
        {"label": "Scenario A — No Eve",              "n_bits": 1500, "eve_present": False, "pa_method": "toeplitz"},
        {"label": "Scenario B — Eve Intercepts All",  "n_bits": 1500, "eve_present": True,  "pa_method": "toeplitz"},
        {"label": "Scenario C — SHA-256 Amplification","n_bits": 2000, "eve_present": False, "pa_method": "sha256"},
    ]

    for s in scenarios:
        print(f"\n{'#'*60}")
        print(f"  {s['label']}")
        print(f"{'#'*60}")
        result = run_qkd(
            n_bits=s["n_bits"],
            eve_present=s["eve_present"],
            pa_method=s["pa_method"],
            verbose=True,
        )
        if result.aborted:
            print("  → Key exchange ABORTED.\n")
        else:
            status = "✓ MATCH" if result.keys_match else "✗ MISMATCH"
            print(f"  → Final key ({result.n_final} bits): {status}\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    args = parse_args()
    verbose = not args.quiet

    if args.demo:
        run_demo()
        sys.exit(0)

    result = run_qkd(
        n_bits=args.bits,
        eve_present=args.eve,
        pa_method=args.method,
        sample_fraction=args.sample,
        ec_passes=args.passes,
        security_param=args.security,
        verbose=verbose,
    )

    sys.exit(0 if (not result.aborted and result.keys_match) else 1)
