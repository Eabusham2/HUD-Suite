"""v3.3: run the SHIPPED entity scripts / render controller / geometries through molang_sim, with pack settings."""
import json, sys, os, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from molang_sim import Env, P, tokenize, parse_only

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "packs", "HUDSuite_RP")
man = json.load(open(f"{ROOT}/manifest.json"))
ent = json.load(open(f"{ROOT}/entity/player.entity.json"))["minecraft:client_entity"]["description"]
rc = json.load(open(f"{ROOT}/render_controllers/hs_readout.render_controllers.json"))["render_controllers"]["controller.render.hs_readout"]
anim = json.load(open(f"{ROOT}/animations/hs_readout.animation.json"))["animations"]
GEO = {}
for f in glob.glob(f"{ROOT}/models/entity/hs_readout_*.geo.json"):
    g = json.load(open(f))["minecraft:geometry"][0]; GEO[g["description"]["identifier"]] = g
DEFAULTS = {x["name"]: x["default"] for x in man["settings"] if "name" in x}

ok = True
def check(c, msg):
    global ok
    print(("PASS " if c else "FAIL ") + msg); ok &= bool(c)

mine_init = [s for s in ent["scripts"]["initialize"] if "hs_" in s]
mine_pre = [s for s in ent["scripts"]["pre_animation"] if "hs_" in s]
conds = [list(r.items())[0] for r in ent["render_controllers"]]
for s in mine_init + mine_pre: parse_only(s.split("=", 1)[1].strip().rstrip(";"))
for r in rc["part_visibility"]:
    (b, c), = r.items()
    if isinstance(c, str): parse_only(c)
for _, c in conds: parse_only(c)
for a in anim.values():
    for bone in a["bones"].values():
        for v in bone.values():
            for x in (v if isinstance(v, list) else [v]):
                if isinstance(x, str): parse_only(x)
check(True, f"{len(mine_init)+len(mine_pre)} script lines, {len(rc['part_visibility'])} visibility rules, {len(conds)} render conditions, animations all parse")

# settings referenced by the entity == settings defined in the manifest
used = set()
for s in mine_pre:
    for t in tokenize(s):
        if t[0] == "str": used.add(t[1])
check(used == set(DEFAULTS), f"entity reads exactly the manifest's settings: {sorted(used)}")

# geometry array: index i -> geometry shifted by move_x = -60 + 10 i
arr = rc["arrays"]["geometries"]["Array.hs_geo"]
check(len(arr) == len(GEO) == 13 and all(ent["geometry"][a.split(".", 1)[1].lower()] in GEO for a in arr),
      "13 geometries: all listed in the render controller and registered on the entity")

def make_env(paper=1, ui=0, settings=None):
    st = dict(DEFAULTS, **(settings or {}))
    q = {"query.life_time": 0.0, "query.delta_time": 1/60, "query.is_in_ui": ui, "query.is_spectator": 0,
         "query.get_pack_setting": lambda n: float(st.get(n, 0)) if not isinstance(st.get(n), bool) else 0.0,
         "query.is_pack_setting_enabled": lambda n: float(bool(st.get(n, False))),
         "query.is_pack_setting_selected": lambda n, o: float(st.get(n) == o)}
    e = Env(q)
    e.vars.update({"variable.is_paperdoll": paper, "variable.is_first_person": 0, "variable.map_face_icon": 0, "variable.attack_time": 0})
    for s in mine_init: e.run(s)
    for s in mine_pre: e.run(s)
    return e
def shown_rcs(e): return [k for k, c in conds if e.ev(P(tokenize(c)).expr())]

for name, kw in {"world": dict(paper=0, ui=0), "hud doll": dict(paper=1, ui=0), "inventory": dict(paper=0, ui=1), "pause doll": dict(paper=1, ui=1)}.items():
    sh = shown_rcs(make_env(**kw)); readout = "controller.render.hs_readout" in sh; body = any("player" in k for k in sh)
    check(readout == (name == "hud doll") and body == (name != "hud doll"), f"defaults, {name:10s}: readout={readout} body={body}")
sh = shown_rcs(make_env(settings={"hs:readout": False}))
check("controller.render.hs_readout" not in sh and any("player" in k for k in sh), "gear 'Show readout' OFF -> doll shows your normal player again")

def text(e, fps=144, cps=12):
    e.vars["variable.hs_fps"], e.vars["variable.hs_cps"] = fps, cps
    geo = GEO[ent["geometry"][arr[int(e.vars["variable.hs_xi"])].split(".", 1)[1].lower()]]
    vis = {b["name"]: True for b in geo["bones"]}
    for r in rc["part_visibility"]:
        (b, c), = r.items()
        for t in (list(vis) if b == "*" else [b]): vis[t] = c if isinstance(c, bool) else bool(e.ev(P(tokenize(c)).expr()))
    lines = {}
    for b in geo["bones"]:
        if b["name"] == "hs_readout" or not vis[b["name"]]: continue
        c = b["cubes"][1]; line = b["name"].split("_")[1]
        lines.setdefault(line, []).append((c["origin"][0], "0123456789FPSC"[c["uv"]["north"]["uv"][0] // 6]))
    out = {k: "".join(ch for _, ch in sorted(v)) for k, v in lines.items()}
    left = min(x for v in lines.values() for x, _ in v) if lines else None
    return out, left
t, _ = text(make_env()); check(t == {"fps": "FPS144", "cps": "CPS12"}, f"defaults render {t}")
t, _ = text(make_env(settings={"hs:show_fps": False})); check(t == {"cps": "CPS12"}, f"'Show FPS' off -> {t}")
t, _ = text(make_env(settings={"hs:show_cps": False})); check(t == {"fps": "FPS144"}, f"'Show CPS' off -> {t}")
_, x0 = text(make_env(settings={"hs:move_x": 0})); _, xr = text(make_env(settings={"hs:move_x": 60})); _, xl = text(make_env(settings={"hs:move_x": -60}))
check(xr - x0 == 60 and x0 - xl == 60, f"'Move left/right' +60 -> text {xr - x0:+.0f} units (screen-right = +x), -60 -> {xl - x0:+.0f}")
for v, want in ((-60, 0), (-30, 3), (0, 6), (30, 9), (60, 12), (999, 12), (-999, 0)):
    xi = make_env(settings={"hs:move_x": v}).vars["variable.hs_xi"]
    check(xi == want, f"move_x {v:5} -> geometry #{xi:.0f}")
for v, want in ((100, 1.0), (50, 0.5), (200, 2.0), (0, 1.0)):
    sz = make_env(settings={"hs:size": v}).vars["variable.hs_size"]
    check(abs(sz - want) < 1e-9, f"'Text size' {v}% -> scale {sz}")
e = make_env(settings={"hs:move_y": 20}); check(e.vars["variable.hs_y"] == 20, "'Move down/up' +20 -> bone moves +20 (up)")
tf = anim["animation.hs.readout_transform"]["bones"]["hs_readout"]
check(tf["position"] == [0, "variable.hs_y", 0] and tf["scale"] == "variable.hs_size", "transform animation uses only Y + scale (no mirrored X)")
piv = [g["bones"][0]["pivot"] for g in GEO.values()]
check(all(p[1] == 16 for p in piv), "size grows around the text's middle (pivot y=16, between the two lines)")
sys.exit(0 if ok else 1)
