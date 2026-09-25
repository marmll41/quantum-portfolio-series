"""Write the benchmark model to model.bin so other languages use the exact
same portfolio. Layout (little-endian float64): d, truth_cvar, mu[d],
w[d], chol[d*d] row-major."""

import numpy as np

from mc_baseline import build_model, exact_reference

m = build_model()
if m.nu is not None:
    raise SystemExit("the Julia port covers the normal case only; "
                     "run with MC_DIST=normal")
truth = exact_reference(m)["cvar"]
np.concatenate([[m.d, truth], m.mu, m.w, m.chol.ravel()]).astype(
    "<f8").tofile("model.bin")
print(f"wrote model.bin  d={m.d}  truth_cvar={truth:.8f}")
