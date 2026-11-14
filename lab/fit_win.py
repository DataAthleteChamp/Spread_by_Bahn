"""Fit P(win | quote) offline from saved reveals:
  logit P(win) = beta*(-log(q/list)) + world FE + pickup-town + delivery-town + option + weekday + hour-bucket
Prints beta and the town effects (the world-invariant lane part of the competitor price, in log-price units),
and writes lab/models/win.json (used as a prior by econ)."""
import json, glob, math, collections
import numpy as np
from pathlib import Path
from sklearn.linear_model import LogisticRegression
ROOT = Path(__file__).resolve().parent.parent
X, y, meta = [], [], []
cols = {}
def col(name):
    if name not in cols: cols[name] = len(cols)
    return cols[name]
col("neg_log_ratio")
for d in [x for x in glob.glob(str(ROOT / "data/runs/*")) if Path(x, "reveal.json").exists()]:
    w = Path(d).name
    rv = json.load(open(Path(d, "reveal.json")))
    for rr in rv["requests"]:
        r, q = rr["request"], rr.get("quote") or {}
        if rr["outcome"] not in ("won", "lost") or not q: continue
        lists = {o["kind"]: o["listPriceCents"] for o in r["options"]}
        ratios = {k: v / lists[k] for k, v in q.items() if k in lists}
        k, ratio = min(ratios.items(), key=lambda kv: kv[1])
        if ratio > 3: continue
        a, b = r["legs"][0]["pickup"]["placeId"], r["legs"][0]["delivery"]["placeId"]
        f = {col("neg_log_ratio"): -math.log(ratio), col("w:" + w): 1, col("a:" + a): 1, col("b:" + b): 1,
             col("o:" + k): 1, col("d:%d" % (r["arrivedAt"] // 1440)): 1, col("h:%d" % ((r["arrivedAt"] % 1440) // 180)): 1,
             col("n_opts:%d" % len(q)): 1}
        X.append(f); y.append(rr["outcome"] == "won"); meta.append((w, a, b, k, ratio))
M = np.zeros((len(X), len(cols)))
for i, f in enumerate(X):
    for j, v in f.items(): M[i, j] = v
y = np.array(y)
m = LogisticRegression(C=5.0, max_iter=5000).fit(M, y)
coef = dict(zip(cols, m.coef_[0]))
beta = coef["neg_log_ratio"]
print(f"n={len(y)} win rate {y.mean():.3f}  beta={beta:.2f} per log-price unit  (ratio range {min(t[4] for t in meta):.2f}-{max(t[4] for t in meta):.2f})")
def eff(prefix):
    return sorted(((round(v / beta, 3), k[2:]) for k, v in coef.items() if k.startswith(prefix)), reverse=True)
print("pickup-town effect (log-price, + = we can charge more):", eff("a:"))
print("delivery-town effect:", eff("b:"))
print("option:", eff("o:"), " weekday:", eff("d:"), " hour bucket:", eff("h:"), " n options quoted:", eff("n_opts:"))
w = eff("w:"); print("world level spread (log):", w[0], w[-1])
out = {"beta": beta, "intercept": float(m.intercept_[0]) / beta, "a": {k: v for v, k in eff("a:")}, "b": {k: v for v, k in eff("b:")},
       "o": {k: v for v, k in eff("o:")}, "d": {k: v for v, k in eff("d:")}, "h": {k: v for v, k in eff("h:")},
       "world_mean": float(np.mean([v for v, _ in w]))}
(ROOT / "lab/models/win.json").write_text(json.dumps(out)); print("wrote lab/models/win.json")
