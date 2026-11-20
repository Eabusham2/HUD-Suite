"""HUD Suite: FPS + CPS readout drawn through the HUD paper doll (no behavior pack needed).

Technique (as used by Modules-Plus / OpenQuasar, re-implemented from scratch here):
  * the HUD paper doll renders the local player with variable.is_paperdoll && !query.is_in_ui
  * in that context only, the player body is hidden and our own readout geometry is drawn
  * FPS from query.delta_time, clicks from rising edges of variable.attack_time
All geometry, font pixels, Molang and render controllers below are original.
"""
import json, os, re
from PIL import Image

DOLL = "variable.hs_doll"      # this render is the HUD paper doll
SHOW = "variable.hs_show"      # ...and the readout is switched on in the pack settings

# ---------------------------------------------------------------- pack settings (gear on the pack; saved per player)
X_MIN, X_MAX, X_STEP = -60, 60, 10          # left/right: baked into pre-shifted geometries (no animation X mirroring)
SETTINGS = [
    {"type": "label", "text": "FPS / CPS readout (drawn by the HUD paper doll). Saved automatically."},
    {"type": "toggle", "text": "Show FPS / CPS readout", "name": "hs:readout", "default": True},
    {"type": "toggle", "text": "Show FPS", "name": "hs:show_fps", "default": True},
    {"type": "toggle", "text": "Show CPS", "name": "hs:show_cps", "default": True},
    {"type": "slider", "text": "Text size (%)", "name": "hs:size", "min": 50, "max": 200, "step": 10, "default": 100},
    {"type": "slider", "text": "Move left / right", "name": "hs:move_x", "min": X_MIN, "max": X_MAX, "step": X_STEP, "default": 0},
    {"type": "slider", "text": "Move down / up", "name": "hs:move_y", "min": -40, "max": 40, "step": 2, "default": 0},
    {"type": "label", "text": "Chat, captions and the readout's screen corner: Pause > HUD Editor."},
]
N_GEO = (X_MAX - X_MIN) // X_STEP + 1

# ---------------------------------------------------------------- 5x7 pixel font (original)
GLYPHS = {
 "0": [".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."],
 "1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
 "2": [".###.", "#...#", "....#", "..##.", ".#...", "#....", "#####"],
 "3": [".###.", "#...#", "....#", "..##.", "....#", "#...#", ".###."],
 "4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
 "5": ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
 "6": ["..##.", ".#...", "#....", "####.", "#...#", "#...#", ".###."],
 "7": ["#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."],
 "8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
 "9": [".###.", "#...#", "#...#", ".####", "....#", "...#.", ".##.."],
 "F": ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
 "P": ["####.", "#...#", "#...#", "####.", "#....", "#....", "#...."],
 "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
 "C": [".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."],
}
ORDER = list("0123456789FPSC")
CELL_W, CELL_H, GW, GH = 6, 8, 5, 7
TEX_W, TEX_H = 128, 16
DIGIT_RGB, LABEL_RGB, SHADOW_RGB = (255, 255, 255), (150, 230, 255), (62, 62, 62)


def font_png(path):
    im = Image.new("RGBA", (TEX_W, TEX_H), (0, 0, 0, 0))
    px = im.load()
    for col, ch in enumerate(ORDER):
        rgb = LABEL_RGB if ch.isalpha() else DIGIT_RGB
        for y, row in enumerate(GLYPHS[ch]):
            for x, c in enumerate(row):
                if c == "#":
                    px[col * CELL_W + x, y] = (*rgb, 255)               # row 0: glyph
                    px[col * CELL_W + x, CELL_H + y] = (*SHADOW_RGB, 255)  # row 1: shadow
    im.save(path)


# ---------------------------------------------------------------- geometry (1 model unit = 1 font pixel)
ADV = 6                       # glyph advance
LINE_TOP = {"fps": 24, "cps": 14}   # top edge of each line, model units above the feet
X0 = -20.5                    # left edge of a 7-glyph line centred on the doll


def glyph_bone(name, ch, slot, line, dx=0):
    col = ORDER.index(ch)
    x = X0 + slot * ADV + dx
    y = LINE_TOP[line] - GH
    return {"name": name, "parent": "hs_readout", "pivot": [0, 0, 0], "cubes": [
        # shadow 1px right / 1px down, slightly behind (camera looks at the north face from -z)
        {"origin": [x + 1, y - 1, 0.1], "size": [GW, GH, 0], "uv": {"north": {"uv": [col * CELL_W, CELL_H], "uv_size": [GW, GH]}}},
        {"origin": [x, y, 0], "size": [GW, GH, 0], "uv": {"north": {"uv": [col * CELL_W, 0], "uv_size": [GW, GH]}}}]}


def readout_geometry(dx=0, ident="geometry.hs_readout"):
    # pivot between the two lines, so "Text size" grows the text around its middle
    bones = [{"name": "hs_readout", "pivot": [dx, 16, 0]}]
    show = {"fps": "variable.hs_sf", "cps": "variable.hs_sc"}
    vis = []
    for line, label in (("fps", "FPS"), ("cps", "CPS")):
        for i, ch in enumerate(label):
            bones.append(glyph_bone(f"hs_{line}_l{i}", ch, i, line, dx))
            vis.append({f"hs_{line}_l{i}": show[line]})
    # numbers start right after the label (slot 4): one bone set per digit count, so no gaps
    for line, var, maxlen in (("fps", "variable.hs_fps", 3), ("cps", "variable.hs_cps", 2)):
        for n in range(1, maxlen + 1):
            lo, hi = (10 ** (n - 1) if n > 1 else 0), 10 ** n
            size_ok = f"{var} >= {lo} && {var} < {hi}" if n < maxlen else f"{var} >= {lo}"
            for k in range(n):
                place = 10 ** (n - 1 - k)
                for dgt in range(10):
                    name = f"hs_{line}_n{n}_p{place}_{dgt}"
                    bones.append(glyph_bone(name, str(dgt), 4 + k, line, dx))
                    digit = f"math.mod(math.floor({var} / {place}), 10) == {dgt}" if place > 1 else f"math.mod(math.floor({var}), 10) == {dgt}"
                    vis.append({name: f"{show[line]} && {size_ok} && {digit}"})
    geo = {"format_version": "1.12.0", "minecraft:geometry": [{
        "description": {"identifier": ident, "texture_width": TEX_W, "texture_height": TEX_H,
                        "visible_bounds_width": 8, "visible_bounds_height": 8, "visible_bounds_offset": [0, 1, 0]},
        "bones": bones}]}
    return geo, vis


# ---------------------------------------------------------------- Molang
N_CLICKS = 20     # ring of click timestamps -> counts up to 20 CPS


def molang():
    init = ["variable.hs_fps = 0.0;", "variable.hs_fps_s = 60.0;", "variable.hs_fps_t = 0.0;",
            "variable.hs_prev_at = 0.0;", "variable.hs_cps = 0.0;", "variable.hs_doll = 0.0;", "variable.hs_show = 0.0;",
            "variable.hs_sf = 1.0;", "variable.hs_sc = 1.0;", "variable.hs_size = 1.0;", "variable.hs_xi = 0.0;", "variable.hs_y = 0.0;"]
    init += [f"variable.hs_c{i} = -10.0;" for i in range(N_CLICKS)]
    pre = [
        # which render is this? HUD paper doll only (not inventory, pause screen or the world)
        f"{DOLL} = variable.is_paperdoll && !query.is_in_ui;",
        # pack settings (read-only, saved per player by the game)
        f"{SHOW} = {DOLL} && query.is_pack_setting_enabled('hs:readout');",
        "variable.hs_sf = query.is_pack_setting_enabled('hs:show_fps');",
        "variable.hs_sc = query.is_pack_setting_enabled('hs:show_cps');",
        "variable.hs_size = query.get_pack_setting('hs:size');",
        "variable.hs_size = variable.hs_size > 0 ? variable.hs_size / 100.0 : 1.0;",
        f"variable.hs_xi = math.clamp(math.round((query.get_pack_setting('hs:move_x') - ({X_MIN})) / {X_STEP}), 0, {N_GEO - 1});",
        "variable.hs_y = query.get_pack_setting('hs:move_y');",
        # FPS: smoothed 1/frame-time, shown 4x per second
        "variable.hs_dt = math.clamp(query.delta_time, 0.001, 1.0);",
        "variable.hs_fps_s = variable.hs_fps_s + (1.0 / variable.hs_dt - variable.hs_fps_s) * math.min(variable.hs_dt * 4.0, 1.0);",
        "variable.hs_upd = (query.life_time - variable.hs_fps_t) >= 0.25 || query.life_time < variable.hs_fps_t;",
        "variable.hs_fps = variable.hs_upd ? math.clamp(math.round(variable.hs_fps_s), 0, 999) : variable.hs_fps;",
        "variable.hs_fps_t = variable.hs_upd ? query.life_time : variable.hs_fps_t;",
        # CPS: a click = the arm swing starting or restarting (air clicks swing too)
        "variable.hs_click = variable.attack_time > 0 && (variable.hs_prev_at <= 0 || variable.attack_time < variable.hs_prev_at);",
        "variable.hs_prev_at = variable.attack_time;",
    ]
    pre += [f"variable.hs_c{i} = variable.hs_click ? variable.hs_c{i-1} : variable.hs_c{i};" for i in range(N_CLICKS - 1, 0, -1)]
    pre += ["variable.hs_c0 = variable.hs_click ? query.life_time : variable.hs_c0;",
            "variable.hs_cps = " + " + ".join(f"(query.life_time - variable.hs_c{i} < 1.0)" for i in range(N_CLICKS)) + ";"]
    return init, pre


# ---------------------------------------------------------------- strip // comments (vanilla sample files carry some)
def load_jsonc(path):
    t = open(path, encoding="utf-8-sig").read()
    out, i, s = [], 0, False
    while i < len(t):
        c = t[i]
        if s:
            out.append(c)
            if c == "\\":
                out.append(t[i + 1]); i += 2; continue
            if c == '"':
                s = False
        else:
            if c == '"':
                s = True; out.append(c)
            elif t.startswith("//", i):
                while i < len(t) and t[i] != "\n":
                    i += 1
                continue
            else:
                out.append(c)
        i += 1
    return json.loads(re.sub(r",(\s*[}\]])", r"\1", "".join(out)))


def build(rp, vanilla_entity):
    os.makedirs(f"{rp}/entity", exist_ok=True); os.makedirs(f"{rp}/models/entity", exist_ok=True)
    os.makedirs(f"{rp}/render_controllers", exist_ok=True); os.makedirs(f"{rp}/animations", exist_ok=True)
    os.makedirs(f"{rp}/textures/entity", exist_ok=True)
    font_png(f"{rp}/textures/entity/hs_font.png")
    geos = []
    for i in range(N_GEO):
        g, vis = readout_geometry(X_MIN + i * X_STEP, f"geometry.hs_readout_{i}")
        json.dump(g, open(f"{rp}/models/entity/hs_readout_{i}.geo.json", "w"), separators=(",", ":"))
        geos.append(g)

    json.dump({"format_version": "1.8.0", "render_controllers": {"controller.render.hs_readout": {
        "arrays": {"geometries": {"Array.hs_geo": [f"Geometry.hs_readout_{i}" for i in range(N_GEO)]}},
        "geometry": "Array.hs_geo[variable.hs_xi]", "materials": [{"*": "Material.hs_text"}], "textures": ["Texture.hs_font"],
        "ignore_lighting": True, "filter_lighting": True,
        "part_visibility": [{"*": True}] + vis}}}, open(f"{rp}/render_controllers/hs_readout.render_controllers.json", "w"), indent=1)

    # body, armor, held item and cape all hang off "root"/"body": shrink them, only inside the HUD doll
    json.dump({"format_version": "1.8.0", "animations": {
        "animation.hs.hide_body": {"loop": True, "bones": {
            "root": {"scale": 0.0001}, "body": {"scale": 0.0001}, "cape": {"scale": 0.0001}}},
        # size + up/down from the pack settings (Y and scale are not mirrored, unlike animation X)
        "animation.hs.readout_transform": {"loop": True, "bones": {
            "hs_readout": {"position": [0, "variable.hs_y", 0], "scale": "variable.hs_size"}}}}},
        open(f"{rp}/animations/hs_readout.animation.json", "w"), indent=1)

    ent = load_jsonc(vanilla_entity)
    d = ent["minecraft:client_entity"]["description"]
    d["materials"]["hs_text"] = "entity_alphatest"
    d["textures"]["hs_font"] = "textures/entity/hs_font"
    for i in range(N_GEO):
        d["geometry"][f"hs_readout_{i}"] = f"geometry.hs_readout_{i}"
    d["animations"]["hs_hide_body"] = "animation.hs.hide_body"
    d["animations"]["hs_readout_tf"] = "animation.hs.readout_transform"
    init, pre = molang()
    d["scripts"]["initialize"] = d["scripts"].get("initialize", []) + init
    d["scripts"]["pre_animation"] = d["scripts"].get("pre_animation", []) + pre
    d["scripts"]["animate"] = d["scripts"].get("animate", []) + [{"hs_hide_body": SHOW}, {"hs_readout_tf": SHOW}]
    rcs = []
    for rc in d["render_controllers"]:
        (k, cond), = rc.items()
        rcs.append({k: f"({cond}) && !{SHOW}"})
    rcs.append({"controller.render.hs_readout": SHOW})
    d["render_controllers"] = rcs
    json.dump(ent, open(f"{rp}/entity/player.entity.json", "w"), indent=1)
    return {"geometries": N_GEO, "bones_each": len(geos[0]["minecraft:geometry"][0]["bones"]), "vis_rules": len(vis), "init": len(init), "pre": len(pre)}
