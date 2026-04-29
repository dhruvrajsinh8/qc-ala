#!/usr/bin/env python3
"""
examples/compare_scenarios.py
Compare QKD performance across multiple configurations.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from qkd_pipeline import run_qkd

configs = [
    {"label": "No Eve  — 1 000 bits",  "n_bits": 1000, "eve_present": False},
    {"label": "No Eve  — 2 000 bits",  "n_bits": 2000, "eve_present": False},
    {"label": "With Eve — 1 000 bits", "n_bits": 1000, "eve_present": True},
    {"label": "With Eve — 2 000 bits", "n_bits": 2000, "eve_present": True},
]

print(f"\n{'Label':<35} {'QBER':>7} {'Sifted':>8} {'Final':>8} {'Aborted':>9} {'Match':>7}")
print("-" * 80)
for cfg in configs:
    r = run_qkd(n_bits=cfg["n_bits"], eve_present=cfg["eve_present"], verbose=False)
    print(f"{cfg['label']:<35} {r.qber:>7.4f} {r.n_sifted:>8} {r.n_final:>8} "
          f"{'YES' if r.aborted else 'NO':>9} {'YES' if r.keys_match else 'NO':>7}")
print()
