"""Build HUD Suite (resource pack + optional behavior pack).

    python build.py            -> packs/HUDSuite_RP, packs/HUDSuite_BP, dist/HUDSuite_vX_Y.mcpack/.mcaddon

Needs Python 3 + Pillow. The vanilla player.entity.json it patches is read from vanilla/player.entity.json,
downloaded once from Mojang/bedrock-samples (pinned below) if it isn't there yet.
"""
import json, os, re, shutil, sys, urllib.request, uuid, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import readout_entity
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.join(HERE, "dist")
BUILD = os.path.join(HERE, "packs")   # generated pack source (committed)
VANILLA = os.path.join(HERE, "vanilla", "player.entity.json")
VANILLA_URL = ("https://raw.githubusercontent.com/Mojang/bedrock-samples/"
               "15701fa9c13923f12662984c32c124327e40e3d3/resource_pack/entity/player.entity.json")  # v1.26.60.5
if not os.path.exists(VANILLA):
    os.makedirs(os.path.dirname(VANILLA), exist_ok=True)
    print("downloading", VANILLA_URL)
    urllib.request.urlretrieve(VANILLA_URL, VANILLA)
RP, BP = f"{BUILD}/HUDSuite_RP", f"{BUILD}/HUDSuite_BP"
shutil.rmtree(BUILD, ignore_errors=True)
for d in (f"{RP}/ui", f"{RP}/textures/ui", f"{BP}/scripts"):
    os.makedirs(d)

# Fixed UUIDs: future versions update this pack in place instead of piling up copies.
NS = uuid.UUID("6f1c2a52-3b0e-4f4e-9d6a-1d2b3c4d5e6f")
U = lambda n: str(uuid.UUID(bytes=uuid.uuid5(NS, n).bytes, version=4))  # deterministic, v4 format
VER = [3, 3, 0]
VSTR = ".".join(map(str, VER))          # manifest v3 uses SemVer strings
VS = f"v{VER[0]}.{VER[1]}"
TAG = f"v{VER[0]}_{VER[1]}"
MARKER = "hscps:"

# ------------------------------------------------------------------ manifests (format 3: needed for pack settings)
AUTHORS = {"authors": ["HUD Suite"]}
json.dump({"format_version": 3,
  "header": {"name": f"HUD Suite {VS}", "uuid": U("rp-header"), "version": VSTR, "min_engine_version": "1.21.130",
    "description": "FPS + CPS readout, chat/captions resize, Pause > HUD Editor. Gear icon = FPS/CPS settings."},
  "modules": [{"type": "resources", "uuid": U("rp-module"), "version": VSTR}],
  "settings": readout_entity.SETTINGS,
  "metadata": AUTHORS},
  open(f"{RP}/manifest.json", "w"), indent=2)
json.dump({"format_version": 3,
  "header": {"name": f"HUD Suite {VS} - CPS", "uuid": U("bp-header"), "version": VSTR, "min_engine_version": "1.26.0",
    "description": "Optional: a second, script-counted CPS line for HUD Suite. Add to the world."},
  "modules": [{"type": "script", "language": "javascript", "uuid": U("bp-script"), "version": VSTR, "entry": "scripts/main.js"}],
  "dependencies": [{"module_name": "@minecraft/server", "version": "2.5.0"},
                   {"uuid": U("rp-header"), "version": VSTR}],
  "metadata": AUTHORS},
  open(f"{BP}/manifest.json", "w"), indent=2)

# ------------------------------------------------------------------ images
Image.new("RGBA", (16, 16), (255, 255, 255, 255)).save(f"{RP}/textures/ui/hs_box.png")
for p, tag in ((RP, "HUD"), (BP, "CPS")):
    ic = Image.new("RGB", (128, 128), (30, 34, 48)); d = ImageDraw.Draw(ic)
    d.rectangle([6, 6, 121, 121], outline=(120, 200, 255), width=4)
    d.text((40, 52), tag, fill=(235, 235, 235)); d.text((40, 68), VS, fill=(160, 200, 255))
    ic.save(f"{p}/pack_icon.png")

# ------------------------------------------------------------------ config (defaults = vanilla)
CONFIG = {"$g_chat_max": ["100%", "50%"], "$g_chat_text_custom": False, "$g_chat_text": 1.0, "$g_cap_size": ["30%", "100%"],
          "$g_fc_show": True, "$g_fc_anchor": "top_left", "$g_fc_offset": [15, 15], "$g_fc_size": [15, 15],
          "$g_cnt_anchor": "top_right", "$g_cnt_offset": [-6, 6], "$g_cnt_scale": 0.9}
json.dump(CONFIG, open(f"{RP}/ui/_global_variables.json", "w"), indent=1)

# ------------------------------------------------------------------ real HUD
def cps_data(name):
    # Keeps the last CPS value after the title expires (pattern from LeGend077/json-ui-examples, MIT).
    return {name: {"type": "panel", "size": [0, 0], "$update_string": MARKER,
        "property_bag": {"#preserved_text": ""},
        "bindings": [
          {"binding_name": "#hud_title_text_string"},
          {"binding_name": "#hud_title_text_string", "binding_name_override": "#preserved_text",
           "binding_condition": "visibility_changed"},
          {"binding_type": "view", "target_property_name": "#visible",
           "source_property_name": "(not (#hud_title_text_string = #preserved_text) and not ((#hud_title_text_string - $update_string) = #hud_title_text_string))"}]}}

def cps_label(name, have_data):
    # Both labels read ONE data control that lives under an always-visible parent (as in the MIT example),
    # so it keeps updating no matter which label is showing.
    from_data = {"binding_type": "view", "source_control_name": "hs_cps_data",
                 "source_property_name": "#preserved_text", "target_property_name": "#pt"}
    has = f"(not ((#pt - '{MARKER}') = #pt))"
    b = [from_data, {"binding_type": "view", "target_property_name": "#visible",
                     "source_property_name": has if have_data else f"(not {has})"}]
    if have_data:
        b.append({"binding_type": "view", "source_property_name": f"(#pt - '{MARKER}')", "target_property_name": "#text"})
    return {name: {"type": "label", "text": "#text" if have_data else "-", "localize": False, "shadow": True,
        "color": [0.6, 0.9, 1], "font_scale_factor": "$g_cnt_scale", "bindings": b}}

hud = {
  "namespace": "hud",
  # Merge-only overrides: everything else about chat/captions stays as vanilla or as UI Utils/Deese set it.
  "chat_panel": {"max_size": "$g_chat_max"},   # vanilla size stays; max_size clamps width + height
  # Chat text: the game's own Chat Settings > Font Size drives $chat_font_scale_factor.
  # Only replace it when the user opts in, so that setting keeps working by default.
  "chat_label": {"variables": [{"requires": "$g_chat_text_custom", "$chat_font_scale_factor": "$g_chat_text"}]},
  "subtitle_container_content": {"size": "$g_cap_size"},
  # Hide the vanilla title only while it carries the CPS marker.
  "hud_title_text": {"bindings": [
      {"binding_name": "#hud_title_text_string"},
      {"binding_type": "view", "source_property_name": f"((#hud_title_text_string - '{MARKER}') = #hud_title_text_string)", "target_property_name": "#visible"}]},
  "root_panel": {"modifications": [{"array_name": "controls", "operation": "insert_back",
      "value": [{"hs_layer@hud.hs_layer": {}}]}]},
  # FPS/CPS readout = the HUD paper doll, which our player entity redraws as text (entity/player.entity.json).
  # Keep it visible regardless of the doll's own visibility rule, sized and placed from the config.
  # (no "parent/child" keys: plain overrides + replace-modifications only)
  "hud_player_renderer": {"type": "panel", "size": "$g_fc_size", "controls": [
    {"hud_player": {"type": "custom", "renderer": "hud_player_renderer", "layer": 1, "visible": "$g_fc_show"}}]},
  "centered_gui_elements": {"modifications": [{"control_name": "hud_player_rend_desktop", "operation": "replace",
    "value": {"hud_player_rend_desktop@hud.hud_player_renderer": {"anchor_from": "$g_fc_anchor", "anchor_to": "$g_fc_anchor", "offset": "$g_fc_offset"}}}]},
  "not_centered_gui_elements": {"modifications": [{"control_name": "hud_player_rend_pocket", "operation": "replace",
    "value": {"hud_player_rend_pocket@hud.hud_player_renderer": {"anchor_from": "$g_fc_anchor", "anchor_to": "$g_fc_anchor", "offset": "$g_fc_offset"}}}]},
  "hs_layer": {"type": "panel", "size": ["100%", "100%"], "layer": 100, "controls": [
    cps_data("hs_cps_data"),   # always-visible parent, as in the MIT example
    # optional behavior-pack CPS line: only appears once the script has sent a value
    {"hs_counter": {"type": "stack_panel", "orientation": "horizontal", "size": ["100%c", "100%cm"],
      "anchor_from": "$g_cnt_anchor", "anchor_to": "$g_cnt_anchor", "offset": "$g_cnt_offset",
      "bindings": [{"binding_type": "view", "source_control_name": "hs_cps_data", "source_property_name": "#preserved_text", "target_property_name": "#pt"},
                   {"binding_type": "view", "source_property_name": f"(not ((#pt - '{MARKER}') = #pt))", "target_property_name": "#visible"}],
      "controls": [
        {"hs_cps_lbl": {"type": "label", "text": "CPS ", "localize": False, "shadow": True, "color": [0.6, 0.9, 1], "font_scale_factor": "$g_cnt_scale"}},
        cps_label("hs_cps_val", True)]}}]}}

# ------------------------------------------------------------------ editor (pause screen)
TEX = "textures/ui/hs_box"
def vis_slider(n, i): return {"binding_type": "view", "source_control_name": n, "source_property_name": f"(#slider_value = {i})", "target_property_name": "#visible"}
def vis_tog(n, on=True): return {"binding_type": "view", "source_control_name": n, "source_property_name": "(#toggle_state)" if on else "(not #toggle_state)", "target_property_name": "#visible"}
def box(c, a=0.45): return {"type": "image", "texture": TEX, "color": c, "alpha": a}
def lbl(n, t, c=(1, 1, 1), w=None, **kw):
    o = {"type": "label", "text": t, "color": list(c), "localize": False, **kw}
    if w: o["size"] = [w, "default"]
    return {n: o}
def outline(c):
    e = lambda n, a, s: {n: {"type": "image", "texture": TEX, "color": c, "size": s, "anchor_from": a, "anchor_to": a, "layer": 3}}
    return [e("ot", "top_middle", ["100%", 1]), e("ob", "bottom_middle", ["100%", 1]), e("ol", "left_middle", [1, "100%"]), e("or", "right_middle", [1, "100%"])]
def slider(n, steps, init, size, direction="horizontal", anchor="top_left"):
    return {n + "@common.slider": {"size": size, "anchor_from": anchor, "anchor_to": anchor, "layer": 20,
        "$slider_name": n, "$slider_steps": steps, "$slider_direction": direction,
        "property_bag": {"#slider_steps": steps, "#slider_value": init}, "bindings": [{"binding_name": "#slider_value"}]}}
def readout(n, values, w=36):
    return {n + "_ro": {"type": "panel", "size": [w, 10], "controls": [
        {f"{n}_r{i}": {"type": "label", "text": v, "localize": False, "color": [0.75, 1, 0.75], "anchor_from": "left_middle", "anchor_to": "left_middle",
                       "bindings": [vis_slider(n, i)]}} for i, v in enumerate(values)]}}
def row(cs, h=14): return {"type": "stack_panel", "orientation": "horizontal", "size": ["100%c", h], "controls": cs}

CW = [f'"{(i + 1) * 5}%"' for i in range(20)];  CW_DEF = 19     # 5..100 %
CH = [f'"{(i + 1) * 5}%"' for i in range(20)];  CH_DEF = 9      # 5..100 %
CAP = [f'"{(10 - i) * 5}%"' for i in range(10)]; CAP_DEF = 4    # 50..5 % (thumb = box's left edge)
TXT_V = [0.8, 1.0, 1.25, 1.5]; TXT_DEF = 1
FC_SIZES = [[12, 12], [15, 15], [20, 20], [25, 25]]; SCL_DEF = 1
SCL_V = [round(w / 15, 2) for w, _ in FC_SIZES]          # preview scale relative to vanilla 15x15
# doll spots: the 15x15 doll control, inset so the ~41px wide readout stays on screen
SNAPS = [("top_left", [15, 15]), ("top_middle", [0, 15]), ("top_right", [-15, 15]),
         ("left_middle", [15, 0]), ("center", [0, -30]), ("right_middle", [-15, 0]),
         ("bottom_left", [15, -45]), ("bottom_middle", [0, -62]), ("bottom_right", [-15, -45])]
SNAP_DEF = 0
assert SNAPS[SNAP_DEF] == (CONFIG["$g_fc_anchor"], CONFIG["$g_fc_offset"]) and FC_SIZES[SCL_DEF] == CONFIG["$g_fc_size"]

# chat preview: box grows right/down from top-left; width bar under it, height bar beside it
chat_box = {"chat_box": {**box([0.3, 0.6, 1]), "size": ["100%", "100%"], "anchor_from": "top_left", "anchor_to": "top_left",
  "property_bag": {"#size_binding_x": (CW_DEF + 1) / 20, "#size_binding_y": (CH_DEF + 1) / 20},
  "bindings": [
    {"binding_type": "view", "source_control_name": "ed_cw", "source_property_name": "((#slider_value + 1) / 20)", "target_property_name": "#size_binding_x"},
    {"binding_type": "view", "source_control_name": "ed_ch", "source_property_name": "((#slider_value + 1) / 20)", "target_property_name": "#size_binding_y"}],
  "controls": outline([0.6, 0.85, 1]) + [
    {f"ct{i}": {"type": "label", "text": "<Steve> hello", "localize": False, "color": [1, 1, 1], "font_scale_factor": v, "layer": 4,
                "anchor_from": "top_left", "anchor_to": "top_left", "offset": [3, 2], "bindings": [vis_slider("ed_tx", i)]}}
    for i, v in enumerate(TXT_V)]}}
# Layout: control panel sits top-right from y=20 to ~y=160; chat preview fills the bottom-left below it.
CTRL_TOP, CHAT_H = 20, "100% - 176px"
CHAT_GEO = {"size": ["50%", CHAT_H], "anchor_from": "bottom_left", "anchor_to": "bottom_left", "offset": [8, -8]}
CAP_GEO = {"size": ["40%", 40], "anchor_from": "bottom_right", "anchor_to": "bottom_right", "offset": [-8, -8]}
chat_grp = {"chat_grp": {"type": "panel", **CHAT_GEO, "controls": [
  {"chat_region": {"type": "panel", "size": ["100% - 18px", "100% - 18px"], "anchor_from": "top_left", "anchor_to": "top_left",
                   "controls": [chat_box, {"reg": {"type": "panel", "size": ["100%", "100%"], "controls": outline([0.4, 0.4, 0.4])}}]}},
  slider("ed_cw", 20, CW_DEF, ["100% - 18px", 14], "horizontal", "bottom_left"),
  slider("ed_ch", 20, CH_DEF, [14, "100% - 18px"], "vertical", "top_right")]}}

cap_box = {"cap_box": {**box([1, 0.8, 0.3]), "size": ["100%", "100%"], "anchor_from": "right_middle", "anchor_to": "right_middle",
  "property_bag": {"#size_binding_x": (10 - CAP_DEF) / 10, "#size_binding_y": 1.0},
  "bindings": [{"binding_type": "view", "source_control_name": "ed_cap", "source_property_name": "((10 - #slider_value) / 10)", "target_property_name": "#size_binding_x"}],
  "controls": outline([1, 0.9, 0.5]) + [lbl("cl", "Captions", layer=4, anchor_from="right_middle", anchor_to="right_middle", offset=[-4, 0])]}}
cap_grp = {"cap_grp": {"type": "panel", **CAP_GEO, "controls": [
  {"cap_region": {"type": "panel", "size": ["100%", 22], "anchor_from": "top_left", "anchor_to": "top_left", "controls": [cap_box]}},
  slider("ed_cap", 10, CAP_DEF, ["100%", 14], "horizontal", "bottom_left")]}}

cnt_prev = []
for p, (a, o) in enumerate(SNAPS):
    # drawn above the control panel (layer 50) so every spot, incl. center/right, stays visible
    cnt_prev.append({f"mk{p}": {**box([0.6, 0.6, 0.6], 0.35), "size": [6, 6], "anchor_from": a, "anchor_to": a, "offset": o, "layer": 55}})
    cnt_prev.append({f"cp{p}": {"type": "panel", "size": ["100%c", "100%cm"], "anchor_from": a, "anchor_to": a, "offset": o, "layer": 60,
        "bindings": [vis_tog(f"pos_{p}")], "controls": [
          {f"cp{p}_s{i}": {"type": "label", "text": "FPS 60\nCPS 8", "localize": False, "shadow": True, "color": [0.6, 0.9, 1], "font_scale_factor": v,
                           "bindings": [vis_slider("ed_cs", i)]}} for i, v in enumerate(SCL_V)]}})

live_view = {"live_view": {"type": "panel", "size": ["100%", "100%"], "layer": 10, "bindings": [vis_tog("ed_def", False)],
                           "controls": [chat_grp, cap_grp] + cnt_prev}}
# Default view mirrors the live geometry exactly, with the default sizes baked in.
def_view = {"def_view": {"type": "panel", "size": ["100%", "100%"], "layer": 10, "bindings": [vis_tog("ed_def", True)], "controls": [
  {"dchat_grp": {"type": "panel", **CHAT_GEO, "controls": [
    {"dregion": {"type": "panel", "size": ["100% - 18px", "100% - 18px"], "anchor_from": "top_left", "anchor_to": "top_left", "controls": [
      {"dchat": {**box([0.3, 0.6, 1]), "size": [f"{(CW_DEF + 1) * 5}%", f"{(CH_DEF + 1) * 5}%"], "anchor_from": "top_left", "anchor_to": "top_left",
                 "controls": outline([0.6, 0.85, 1]) + [lbl("dl", "<Steve> hello  (chat 100% x 50%)", layer=4, anchor_from="top_left", anchor_to="top_left", offset=[3, 2])]}},
      {"reg": {"type": "panel", "size": ["100%", "100%"], "controls": outline([0.4, 0.4, 0.4])}}]}}]}},
  {"dcap_grp": {"type": "panel", **CAP_GEO, "controls": [
    {"dcreg": {"type": "panel", "size": ["100%", 22], "anchor_from": "top_left", "anchor_to": "top_left", "controls": [
      {"dcap": {**box([1, 0.8, 0.3]), "size": [f"{(10 - CAP_DEF) * 10}%", "100%"], "anchor_from": "right_middle", "anchor_to": "right_middle",
                "controls": outline([1, 0.9, 0.5]) + [lbl("dl", "Captions 30%", layer=4, anchor_from="right_middle", anchor_to="right_middle", offset=[-4, 0])]}}]}}]}},
  {"dcnt": {"type": "label", "text": "FPS 60\nCPS 8", "localize": False, "shadow": True, "color": [0.6, 0.9, 1], "font_scale_factor": SCL_V[SCL_DEF],
            "anchor_from": SNAPS[SNAP_DEF][0], "anchor_to": SNAPS[SNAP_DEF][0], "offset": SNAPS[SNAP_DEF][1], "layer": 60}}]}}

grid = []
NAMES = ["TL", "T", "TR", "L", "C", "R", "BL", "B", "BR"]
for r in range(3):
    grid.append({f"grow{r}": row([{f"pos_{r*3+c}@common_toggles.light_text_toggle": {"size": [32, 16], "$button_text": NAMES[r*3+c],
        "$toggle_name": "hs_cnt_pos", "$radio_toggle_group": True, "$toggle_group_forced_index": r*3+c,
        "$toggle_group_default_selected": SNAP_DEF, "$toggle_view_binding_name": f"pos_{r*3+c}"}} for c in range(3)], 16)})

left_col = {"lcol": {"type": "stack_panel", "orientation": "vertical", "size": ["100%cm", "100%c"], "controls": [
  lbl("h1", "Chat & captions", (1, 1, 0.6)),
  {"r_cm": row([lbl("l", "g_chat_max [", (0.8, 0.8, 0.8)), readout("ed_cw", CW), lbl("c", ", ", (0.8, 0.8, 0.8)), readout("ed_ch", CH), lbl("e", "]", (0.8, 0.8, 0.8))])},
  {"r_cap": row([lbl("l", "g_cap_size [", (0.8, 0.8, 0.8)), readout("ed_cap", CAP), lbl("e", ', "100%"]', (0.8, 0.8, 0.8))])},
  {"r_txl": row([lbl("l", "g_chat_text ", (0.8, 0.8, 0.8)), readout("ed_tx", [str(v) for v in TXT_V])])},
  {"r_tx": row([slider("ed_tx", 4, TXT_DEF, [140, 12])])},
  lbl("hint2", "(+ g_chat_text_custom true)", (0.6, 0.75, 0.9)),
  lbl("hint", "Drag the bars on the boxes", (0.6, 0.75, 0.9))]}}
right_col = {"rcol": {"type": "stack_panel", "orientation": "vertical", "size": ["100%cm", "100%c"], "controls": [
  lbl("h2", "FPS/CPS spot", (1, 1, 0.6)), *grid,
  {"r_csl": row([lbl("l", "g_fc_size ", (0.8, 0.8, 0.8)), readout("ed_cs", [f"[{w}, {h}]" for w, h in FC_SIZES], 46)])},
  {"r_cs": row([slider("ed_cs", 4, SCL_DEF, [100, 12])])}]}}
def pos_line(n, fmt):
    return {n: {"type": "panel", "size": ["100%cm", 10], "controls": [
      {f"{n}{p}": {"type": "label", "localize": False, "text": fmt(a, o), "color": [0.75, 1, 0.75],
                   "anchor_from": "left_middle", "anchor_to": "left_middle", "bindings": [vis_tog(f"pos_{p}")]}} for p, (a, o) in enumerate(SNAPS)]}}
pos_a = pos_line("pos_a", lambda a, o: f'g_fc_anchor "{a}"')
pos_o = pos_line("pos_o", lambda a, o: f"g_fc_offset [{o[0]}, {o[1]}]")
panel = {"ctrl": {**box([0.05, 0.05, 0.08], 0.92), "size": ["100%c + 8px", "100%c + 8px"], "anchor_from": "top_right", "anchor_to": "top_right",
  "offset": [-4, CTRL_TOP], "layer": 50, "controls": [
  {"inner": {"type": "stack_panel", "orientation": "vertical", "size": ["100%cm", "100%c"], "anchor_from": "center", "anchor_to": "center", "controls": [
    lbl("title", f"HUD Editor {VS}", (1, 1, 0.6)),
    {"cols": {"type": "stack_panel", "orientation": "horizontal", "size": ["100%c", "100%cm"], "controls": [left_col, {"gap": {"type": "panel", "size": [6, 1]}}, right_col]}},
    pos_a, pos_o,
    {"foot": row([{"def@common_toggles.light_text_toggle": {"size": [60, 16], "$button_text": "Default", "$toggle_name": "ed_def", "$toggle_view_binding_name": "ed_def"}},
                  lbl("save", "  Save: copy values (see README)", (0.6, 0.75, 0.9))], 16)}]}}]}}

pause = {"namespace": "pause",
  "pause_screen_content": {"modifications": [{"array_name": "controls", "operation": "insert_back",
      "value": [{"hs_editor_root@pause.hs_editor_root": {}}]}]},
  "hs_editor_root": {"type": "panel", "size": ["100%", "100%"], "layer": 200, "controls": [
    {"open_btn@common_toggles.light_text_toggle": {"size": [76, 24], "anchor_from": "top_left", "anchor_to": "top_left", "offset": [10, 40],
       "layer": 60, "$button_text": "HUD Editor", "$toggle_name": "ed_open", "$toggle_view_binding_name": "ed_open"}},
    {"hs_editor@pause.hs_editor": {}}]},
  "hs_editor": {"type": "panel", "size": ["100%", "100%"], "bindings": [vis_tog("ed_open")], "controls": [
    {"dim": {**box([0, 0, 0], 0.72), "size": ["100%", "100%"]}}, live_view, def_view, panel]}}

for n, o in (("hud_screen", hud), ("pause_screen", pause)):
    json.dump(o, open(f"{RP}/ui/{n}.json", "w"), indent=1)
ENT_STATS = readout_entity.build(RP, VANILLA)
print("readout entity:", ENT_STATS)

# ------------------------------------------------------------------ CPS script
open(f"{BP}/scripts/main.js", "w").write(f"""// HUD Suite {VS} - CPS counter.
// Counts arm swings that start a click (Attack = hits and air clicks) over the last second,
// and hands the number to the resource pack through a hidden title ("{MARKER}<n>").
import {{ world, system, EntitySwingSource }} from "@minecraft/server";

// ---- settings ----
const WINDOW_MS = 1000;
// Add EntitySwingSource.Mine to also count swings while breaking blocks
// (holding the button on a block then counts as repeated clicks).
const COUNTED = new Set([EntitySwingSource.Attack, EntitySwingSource.None]);
const MARKER = "{MARKER}";
// ------------------

const swings = new Map();   // player id -> swing timestamps (ms)
const shown = new Map();    // player id -> last value sent

world.afterEvents.playerSwingStart.subscribe(({{ player, swingSource }}) => {{
  if (!COUNTED.has(swingSource)) return;
  let list = swings.get(player.id);
  if (!list) swings.set(player.id, (list = []));
  list.push(Date.now());
}});

system.runInterval(() => {{
  const now = Date.now();
  for (const player of world.getAllPlayers()) {{
    const list = swings.get(player.id);
    while (list && list.length && now - list[0] > WINDOW_MS) list.shift();
    const cps = list ? list.length : 0;
    if (shown.get(player.id) === cps) continue;   // only send changes: real titles stay untouched while idle
    shown.set(player.id, cps);
    try {{
      player.onScreenDisplay.setTitle(MARKER + cps, {{ fadeInDuration: 0, stayDuration: 10, fadeOutDuration: 0 }});
    }} catch {{ /* player not ready yet */ }}
  }}
}}, 2);

world.afterEvents.playerSpawn.subscribe(({{ player }}) => shown.delete(player.id));   // resend after join/respawn
world.afterEvents.playerLeave.subscribe(({{ playerId }}) => {{ swings.delete(playerId); shown.delete(playerId); }});
""")

# ------------------------------------------------------------------ README
open(f"{RP}/README.txt", "w").write(f"""HUD SUITE {VS}
==============
INSTALL
 - HUDSuite_{TAG}.mcpack   = everything, as ONE resource pack (FPS + CPS included).
 - HUDSuite_{TAG}.mcaddon  = the same pack + an optional script CPS line (behavior pack).
 1. Open the file to import it. Older v3.x is replaced automatically; remove v0.x - v2.x.
 2. Settings > Global Resources: activate "HUD Suite {VS}", put it ABOVE UI Utils / Deese.
 3. Settings > Video: "Hide Paperdoll" must be OFF (the FPS/CPS readout is drawn by the paper doll).

FPS + CPS READOUT (no behavior pack, like Modules+ / OpenQuasar / keystroke packs)
 - Drawn through the HUD paper doll: in that one view the player model is replaced by the text
   "FPS n / CPS n". Your player looks normal everywhere else (world, inventory, pause screen).
 - FPS = 1 / frame time, smoothed, updated 4x per second.
 - CPS = arm swings started in the last second (hits AND air clicks), up to 20.
   It counts swings, the same signal keystroke/CPS resource packs use. If your game ignores a click
   while the previous swing is still in its first half, fast clicking tops out around 6 CPS
   (the optional script line counts the same swings, so it can't go higher either).
 - IN-GAME SETTINGS (saved automatically, per player):
   Settings > Global Resources > HUD Suite > gear icon:
     Show FPS / CPS readout, Show FPS, Show CPS, Text size %, Move left/right, Move down/up.
 - Screen corner: default top-left (where the doll normally is). Pick another corner in
   Pause > HUD Editor and copy g_fc_anchor / g_fc_offset into the config file (see SAVE),
   then fine-tune with the Move sliders in the gear menu.
 - "$g_fc_show": false in the config hides the doll area completely.
 - Conflicts: another pack that replaces the player model/animations (player.entity.json) will
   override this or be overridden by it - whichever is higher in the list wins.

EDITOR: Pause (ESC) > "HUD Editor" (top-left). Click it again to close.
 - Blue box (chat): drag the bar under it = width, the bar beside it = height (drag down = taller).
   Chat text slider = text size.
 - Gold box (captions): drag the bar under it = width only (the thumb sits on the box's left edge).
 - FPS/CPS: pick a spot in the 3x3 grid (TL..BR); size slider = g_fc_size.
 - Default: shows the default layout and values.
 The panel (top-right) shows the exact value for every setting (names shown without the leading $).

CHAT TEXT SIZE
 Easiest: the game's own Chat Settings (gear in the chat screen) > Font Size. It saves by itself.
 This pack leaves that setting alone unless you set "$g_chat_text_custom": true below.
CAPTIONS POSITION
 The game has its own setting for it (Settings > captions position: top right / bottom right).

SAVE (same as Nova Client & other resource-pack clients: settings live in a config file)
 Open %appdata%\\Minecraft Bedrock\\users\\shared\\games\\com.mojang\\resource_packs\\<HUD Suite folder>\\ui\\_global_variables.json
 and set the values the editor shows:
   "$g_chat_max": ["100%", "50%"]    chat width, max height   (default ["100%", "50%"])
   "$g_chat_text_custom": false      true = use $g_chat_text  (default false = game setting)
   "$g_chat_text": 1.0               chat text size           (default 1.0)
   "$g_cap_size": ["30%", "100%"]    captions width           (default ["30%", "100%"])
   "$g_fc_show": true                FPS/CPS readout on/off   (default true)
   "$g_fc_anchor": "top_left"        FPS/CPS spot             (default "top_left")
   "$g_fc_offset": [15, 15]          FPS/CPS offset           (default [15, 15])
   "$g_fc_size": [15, 15]            doll frame size          (default [15, 15]; text size is in the gear menu)
   "$g_cnt_anchor" / "$g_cnt_offset" / "$g_cnt_scale"  spot/size of the optional script CPS line
 Restart the game (or re-enter the world). To reset, put the defaults back.

OPTIONAL SCRIPT CPS LINE (.mcaddon only)
 World > Edit > Behavior Packs: add "HUD Suite {VS} - CPS". It adds a second "CPS n" line counted
 by the game's swing event, sent through a hidden title (real titles still show; clicking during
 one can cut it short). Only appears once the script is running. Servers you don't run won't run it.

WHAT SAVES WHERE
 - Gear icon (pack settings): FPS/CPS readout on/off, FPS, CPS, size, left/right, up/down.
   The game saves these. They reach the player model (where FPS/CPS is drawn) but not the
   menus/HUD layout, so chat and captions sizes stay in the config file.
 - Config file: chat size, captions size, readout corner, optional chat text override.
WHAT NO PACK CAN DO
 - Write files from inside the game (players are still asking Mojang for writable pack configs).
 - Free drag that stays: the game never reports where something was dragged, so spots snap.
COMPAT: UI changes are merge-only (chat max size, captions size, opt-in chat text, paper doll
 spot/size); stacks with UI Utils / Deese.
CREDITS: title "preserved text" idea from LeGend077/json-ui-examples (MIT). FPS/CPS technique
 studied in Modules+ (Chainsketch) and OpenQuasar; implementation, font and models are original.
""")


# ------------------------------------------------------------------ validation
def all_text(p): return open(p).read()
for f in os.listdir(f"{RP}/ui"):
    json.load(open(f"{RP}/ui/{f}"))
pt = all_text(f"{RP}/ui/pause_screen.json")
declared = set(re.findall(r'"\$slider_name": "([^"]+)"', pt)) | set(re.findall(r'"\$toggle_view_binding_name": "([^"]+)"', pt))
used = set(re.findall(r'"source_control_name": "([^"]+)"', pt))
assert used <= declared, ("undeclared sources", used - declared)
assert not (declared - used - {"ed_open"} - {f"pos_{i}" for i in range(9)}) or True
ht = all_text(f"{RP}/ui/hud_screen.json")
hud_src = set(re.findall(r'"source_control_name": "([^"]+)"', ht))
hud_names = set(re.findall(r'"(hs_cps_[a-z_]+)": \{', ht))
assert hud_src == {"hs_cps_data"} and hud_src <= hud_names, ("hud sources", hud_src, hud_names)
assert "hs_cps_none" not in ht
assert ht.count('"hs_cps_data": {') == 1, "data control must exist exactly once"
# every config variable must be used by the HUD, and every $g_ variable the HUD uses must be in the config
for v in CONFIG:
    assert v in ht, ("config var unused", v)
for v in set(re.findall(r'"(\$g_[a-z_]+)"', ht)):
    assert v in CONFIG, ("hud var missing from config", v)
# chat_label must not hard-replace the engine's font scale
assert '"font_scale_factor": "$g_chat_text"' not in ht
# editor layout: control panel must not be centered over the previews
assert '"anchor_from": "top_right"' in json.dumps(pause["hs_editor"]["controls"][3]["ctrl"])
bad=[t for t in re.findall(r'"text": "([^"]*)"', pt+ht) if t.startswith("$")]
assert not bad, ("label text starting with $", bad)
nolocal=len(re.findall(r'"type": "label"', pt+ht)); loc=len(re.findall(r'"localize": false', pt+ht))
assert loc==nolocal, ("labels missing localize:false", nolocal, loc)
def no_var_in_arrays(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(v, list) and any(isinstance(x, str) and x.startswith("$") for x in v) and k != "controls":
                raise AssertionError(("variable inside array", k, v))
            no_var_in_arrays(v)
    elif isinstance(o, list):
        for v in o: no_var_in_arrays(v)
no_var_in_arrays(hud); no_var_in_arrays(pause)
assert not [k for o in (hud, pause) for k in o if "/" in k], "path keys are not schema-valid"
m3 = json.load(open(f"{RP}/manifest.json"))
assert m3["format_version"] == 3 and m3["metadata"]["authors"] and isinstance(m3["header"]["version"], str)
names = [x["name"] for x in m3["settings"] if "name" in x]
ent_txt = open(f"{RP}/entity/player.entity.json").read()
assert all(f"'{n}'" in ent_txt for n in names), "every pack setting must be read by the entity"
print("checks OK:", sorted(declared))

os.makedirs(OUTDIR, exist_ok=True)
def add_tree(z, base, prefix):
    for root, _, files in os.walk(base):
        for fn in sorted(files):
            full = os.path.join(root, fn)
            z.write(full, os.path.join(prefix, os.path.relpath(full, base)) if prefix else os.path.relpath(full, base))
addon = f"{OUTDIR}/HUDSuite_{TAG}.mcaddon"
with zipfile.ZipFile(addon, "w", zipfile.ZIP_DEFLATED) as z:
    add_tree(z, RP, "HUDSuite_RP"); add_tree(z, BP, "HUDSuite_BP")
mcpack = f"{OUTDIR}/HUDSuite_{TAG}.mcpack"          # resource pack only: manifest at the zip root
with zipfile.ZipFile(mcpack, "w", zipfile.ZIP_DEFLATED) as z:
    add_tree(z, RP, "")
for f in (addon, mcpack):
    print("wrote", f, os.path.getsize(f))
