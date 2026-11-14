"""Trace the safety state (mu, projected OT, wins, warnings) through one practice week.
    .venv/bin/python -m lab.trace_mu "FINAL" c15-25
"""
import sys
from .bench import parse_variant
from .runner import run_week

name, cls, params = parse_variant(sys.argv[1])
seed = sys.argv[2]
last = [-1]


class Traced(cls):
    def tick(self):
        super().tick()
        slot = self.now // 120
        if slot != last[0]:
            last[0] = slot
            d, h = divmod(self.now, 1440)
            late = sum(1 for o in self.orders.values() if None not in o["deliveredAt"] and max(o["deliveredAt"]) > o["deadline"])
            print(f"day {d} {h//60:02d}:00 orders {len(self.orders):3d} late {late:2d} urgent {len(self.urgent):2d} "
                  f"mu {self.mu:.2f} proj {getattr(self, 'proj_ot', float('nan')):.3f}", flush=True)


Traced.NAME = cls.NAME
r = run_week(Traced, params, 8, seed)
print("RESULT", r.get("margin"), r.get("on_time"), r.get("error"))
