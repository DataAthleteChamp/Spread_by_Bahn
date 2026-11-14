"""Policy registry. Add a policy: create a module here with a Desk subclass that has NAME, then import it below."""
from .starter import Starter
from .markup import Markup
from .smart import Smart
from .econ import Econ

POLICIES = {cls.NAME: cls for cls in (Starter, Markup, Smart, Econ)}

# Named strategies = presets of `smart` (switch ideas on one at a time -> ablation)
PRESETS = {
    "S1_gate":        "smart:track=0,cap=0,hire=0,offers=0,safety=0,scarce=0",
    "S2_gate_scarce": "smart:track=0,cap=0,hire=0,offers=0,safety=0",
    "S3_hire":        "smart:track=0,cap=0,offers=0,safety=0",
    "S4_offers":      "smart:track=0,cap=0,offers=1,safety=0",
    "S5_track":       "smart:track=1,cap=0,offers=1,safety=0",
    "S6_cap":         "smart:track=0,cap=1,offers=1,safety=0",
    "S7_safety":      "smart:track=0,cap=0,offers=1,safety=1",
    "S9_skew":        "smart:track=0,cap=0,offers=1,safety=0,skew=1",
    "S10_track_war":  "smart:track=1,cap=0,offers=1,safety=0,warguard=1",
    "S8_full":        "smart:track=1,cap=1,offers=1,safety=1",
    # current best (validate2: EUR13.85k/wk, 94.1% on time, min 91.0%, 14/14 ranked on fresh seeds)
    "CANDIDATE1": "econ:defer=1,notes2=1,charge_fix=1,fee_hat=1.0,winmodel=1,trust=1,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,safety2=1,s2_target=0.96,s2_k=25,peak=1,peak_k=0.6,peak_budget=1.0,risk_file=risk_v3.json,hard_thr=0.05,hard_k=4,risk_max=0.10,late_cost=1.5",
    "CANDIDATE2": "econ:defer=1,notes2=1,charge_fix=1,fee_hat=1.0,winmodel=1,trust=1,fee_late=1.1,urgent_open=1.2,urgent_max=1.4,safety2=1,s2_target=0.96,s2_k=25,peak=1,peak_k=0.6,peak_budget=1.0,risk_file=risk_v3.json,hard_thr=0.05,hard_k=4,risk_max=0.13,late_cost=1.5,eta_d=0.03",
    "CANDIDATE3": "CANDIDATE2:tradein_decl=1,min_slack=240,urgent_open=1.3,urgent_max=1.6,late_h=6",
    "CANDIDATE4": "CANDIDATE3:late_h=10,step1_min=90,step1_f=1.0",
    "CANDIDATE5": "CANDIDATE4:notes3=1",
    "CANDIDATE6": "CANDIDATE5:peak=0",
    "CANDIDATE7": "CANDIDATE6:hard_thr=0.08",
    "SAFE": "CANDIDATE7:flu=1,flu_mu=0.5,s2_target=0.97,s2_k=40,risk_max=0.11",
    "SAFER": "CANDIDATE7:flu=1,flu_mu=0.6,s2_target=0.975,s2_k=60,risk_max=0.10",
    "CANDIDATE8": "SAFE",
    "CANDIDATE": "CANDIDATE8",   # alias used by the live runner / test finals
}


def get(name: str):
    if name not in POLICIES:
        raise SystemExit(f"Unknown policy {name!r}. Known: {', '.join(POLICIES)}; presets: {', '.join(PRESETS)}")
    return POLICIES[name]
