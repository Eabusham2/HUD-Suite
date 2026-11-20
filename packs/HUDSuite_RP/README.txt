HUD SUITE v3.3
==============
INSTALL
 - HUDSuite_v3_3.mcpack   = everything, as ONE resource pack (FPS + CPS included).
 - HUDSuite_v3_3.mcaddon  = the same pack + an optional script CPS line (behavior pack).
 1. Open the file to import it. Older v3.x is replaced automatically; remove v0.x - v2.x.
 2. Settings > Global Resources: activate "HUD Suite v3.3", put it ABOVE UI Utils / Deese.
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
 Open %appdata%\Minecraft Bedrock\users\shared\games\com.mojang\resource_packs\<HUD Suite folder>\ui\_global_variables.json
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
 World > Edit > Behavior Packs: add "HUD Suite v3.3 - CPS". It adds a second "CPS n" line counted
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
