"""FPS / CPS behaviour: runs the shipped entity Molang through molang_sim (FPS smoothing, CPS counting, digits)."""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from molang_sim import Env, P, tokenize, parse_only

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "packs", "HUDSuite_RP")
ent = json.load(open(f"{ROOT}/entity/player.entity.json"))["minecraft:client_entity"]["description"]
rc = json.load(open(f"{ROOT}/render_controllers/hs_readout.render_controllers.json"))["render_controllers"]["controller.render.hs_readout"]
geo = json.load(open(f"{ROOT}/models/entity/hs_readout_6.geo.json"))["minecraft:geometry"][0]
man = json.load(open(f"{ROOT}/manifest.json"))
ST = {x["name"]: x["default"] for x in man["settings"] if "name" in x}

ok = True
def check(c, msg):
    global ok
    print(("PASS " if c else "FAIL ") + msg); ok &= bool(c)

# 1. every Molang string in our additions parses (subset grammar = stricter than the game's)
mine_init = [s for s in ent["scripts"]["initialize"] if "hs_" in s]
mine_pre = [s for s in ent["scripts"]["pre_animation"] if "hs_" in s]
for s in mine_init + mine_pre:
    rhs = s.split("=", 1)[1].strip().rstrip(";")
    parse_only(rhs)
for rule in rc["part_visibility"]:
    (bone, cond), = rule.items()
    if isinstance(cond, str): parse_only(cond)
conds = [list(r.items())[0] for r in ent["render_controllers"]]
for _, c in conds: parse_only(c)
check(True, f"all {len(mine_init)+len(mine_pre)} script lines, {len(rc['part_visibility'])} visibility rules and {len(conds)} render conditions parse")

# 2. bone names in visibility rules exist in the geometry
bones = {b["name"] for b in geo["bones"]}
check(all(list(r)[0] in bones or list(r)[0] == "*" for r in rc["part_visibility"]), "every visibility rule targets an existing bone")

# 3. context gating
ctx = {"world": dict(paper=0, ui=0), "hud doll": dict(paper=1, ui=0), "inventory": dict(paper=0, ui=1), "pause doll": dict(paper=1, ui=1)}
def make_env(paper, ui):
    q = {"query.life_time": 0.0, "query.delta_time": 1/60, "query.is_in_ui": ui, "query.is_spectator": 0,
         "query.get_pack_setting": lambda n: 0.0 if isinstance(ST[n], bool) else float(ST[n]),
         "query.is_pack_setting_enabled": lambda n: float(bool(ST[n]))}
    e = Env(q); e.vars["variable.is_paperdoll"] = paper; e.vars["variable.is_first_person"] = 0; e.vars["variable.map_face_icon"] = 0
    for s in mine_init: e.run(s)
    return e
for name, c in ctx.items():
    e = make_env(**c)
    for s in mine_pre: e.run(s)
    shown = [k for k, cond in conds if e.ev(P(tokenize(cond)).expr())]
    readout = "controller.render.hs_readout" in shown; body = any("player" in k for k in shown)
    want_readout = name == "hud doll"
    check(readout == want_readout and body == (not want_readout), f"{name:10s}: readout={readout} body={body}")

# 4. FPS
def run_frames(e, n, dt, at_fn=None):
    for i in range(n):
        e.q["query.delta_time"] = dt; e.q["query.life_time"] += dt
        e.vars["variable.attack_time"] = at_fn(e.q["query.life_time"]) if at_fn else 0.0
        for s in mine_pre: e.run(s)
for target in (60, 144, 240, 30):
    e = make_env(1, 0); run_frames(e, int(target * 2), 1 / target)
    check(abs(e.vars["variable.hs_fps"] - target) <= 1, f"steady {target} fps -> shows {e.vars['variable.hs_fps']:.0f}")
e = make_env(1, 0); updates = []; last = None
for i in range(240):
    run_frames(e, 1, 1/120)
    if e.vars["variable.hs_fps"] != last: updates.append(e.q["query.life_time"]); last = e.vars["variable.hs_fps"]
check(len(updates) <= 10, f"display changes at most ~4x/s (changed {len(updates)}x in 2s)")
e = make_env(1, 0); run_frames(e, 50, 0.0)
check(0 <= e.vars["variable.hs_fps"] <= 999, f"zero frame time is clamped (shows {e.vars['variable.hs_fps']:.0f})")

# 5. CPS from attack_time (swing 0->1 over 0.3 s, restarted by every click)
def swing_fn(click_times, restart=True, dur=0.3):
    def at(t):
        past = [c for c in click_times if c <= t]
        if not past: return 0.0
        start = past[-1] if restart else None
        if not restart:  # a click only starts a swing if no swing running
            start = None
            for c in past:
                if start is None or c - start >= dur: start = c
        p = (t - start) / dur
        return p if p < 1 else 0.0
    return at
for cps in (1, 5, 8, 12, 16, 20):
    clicks = [1.0 + k / cps for k in range(cps * 3)]
    e = make_env(1, 0); seen = []
    def at_fn(t, f=swing_fn(clicks)): return f(t)
    for i in range(int(3.9 * 144)):
        run_frames(e, 1, 1/144, at_fn)
        if 2.5 < e.q["query.life_time"] < 3.9: seen.append(e.vars["variable.hs_cps"])
    avg = sum(seen) / len(seen)
    check(abs(avg - cps) <= 1.0, f"{cps:2d} cps clicking (swing restarts each click) -> reads {avg:.1f}")
e = make_env(1, 0)
run_frames(e, int(3 * 144), 1/144, swing_fn([1.0 + k / 10 for k in range(5)]))   # last click 1.4s, check at 3.0s
check(e.vars["variable.hs_cps"] == 0, f"drops to 0 after clicking stops (reads {e.vars['variable.hs_cps']:.0f})")
clicks = [1.0 + k / 12 for k in range(36)]; e = make_env(1, 0); seen = []
for i in range(int(3.9 * 144)):
    run_frames(e, 1, 1/144, swing_fn(clicks, restart=False))
    if 2.5 < e.q["query.life_time"] < 3.9: seen.append(e.vars["variable.hs_cps"])
print(f"INFO 12 cps if the game never restarts a running swing -> reads {sum(seen)/len(seen):.1f}")
def half_restart(click_times, dur=0.3):
    def at(t):
        start = None
        for c in click_times:
            if c > t: break
            if start is None or c - start >= dur / 2: start = c
        if start is None: return 0.0
        p = (t - start) / dur
        return p if p < 1 else 0.0
    return at
for cps in (6, 8, 12, 16):
    clicks = [1.0 + k / cps for k in range(cps * 3)]; e = make_env(1, 0); seen = []
    for i in range(int(3.9 * 144)):
        run_frames(e, 1, 1/144, half_restart(clicks))
        if 2.5 < e.q["query.life_time"] < 3.9: seen.append(e.vars["variable.hs_cps"])
    print(f"INFO {cps:2d} cps if the game only restarts a swing past halfway (Java rule) -> reads {sum(seen)/len(seen):.1f}")

# 6. digit rendering: exactly one glyph per shown slot, no leading zeros
def visible_bones(fps, cps):
    e = make_env(1, 0); e.vars["variable.hs_fps"] = fps; e.vars["variable.hs_cps"] = cps
    vis = {b: True for b in bones}
    for rule in rc["part_visibility"]:
        (b, c), = rule.items()
        targets = bones if b == "*" else [b]
        for t in targets: vis[t] = c if isinstance(c, bool) else bool(e.ev(P(tokenize(c)).expr()))
    return {b for b, v in vis.items() if v}
def text_of(vb, line):
    out = []
    for slot in range(7):
        ch = [b for b in vb if b.startswith(f"hs_{line}_") and b != "hs_readout" and slot_of[b] == slot]
        out.append(chr_of[ch[0]] if len(ch) == 1 else (" " if not ch else "?"))
    return "".join(out).rstrip()
slot_of, chr_of = {}, {}
ORDER = list("0123456789FPSC")
for b in geo["bones"]:
    if b["name"] == "hs_readout": continue
    cube = b["cubes"][1]
    slot_of[b["name"]] = round((cube["origin"][0] + 20.5) / 6)
    chr_of[b["name"]] = ORDER[cube["uv"]["north"]["uv"][0] // 6]
for fps, cps in ((0, 0), (7, 3), (60, 8), (144, 12), (999, 20), (100, 10)):
    vb = visible_bones(fps, cps)
    t1, t2 = text_of(vb, "fps"), text_of(vb, "cps")
    want1, want2 = f"FPS {fps}", f"CPS {cps}"
    check(t1 == want1.rstrip() and t2 == want2.rstrip(), f"fps={fps} cps={cps} renders {t1!r} / {t2!r}")

sys.exit(0 if ok else 1)
