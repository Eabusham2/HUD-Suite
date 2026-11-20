# HUD Suite

A Minecraft Bedrock resource pack that lets you resize chat and captions, shows an FPS and CPS counter, and adds a **HUD Editor** button to the pause menu. It works alongside UI Utils and Déesse UI.

**Download:** [latest release](https://github.com/Eabusham2/HUD-Suite/releases/latest)

| File | What it is |
|---|---|
| `HUDSuite_v3_3.mcpack` | Everything in **one resource pack**: chat/captions resize, HUD Editor, FPS + CPS. |
| `HUDSuite_v3_3.mcaddon` | The same pack plus an optional behavior pack that adds a second, script-counted CPS line. |

---

## Features

Each feature below is written the way it was asked for, followed by how the pack does it.

### "A GUI that lets me resize chat diagonally, vertically or horizontally, from the top right, top or right"
Pause → **HUD Editor** shows a fullscreen preview of your chat box. Drag the bar under the box to change its width and the bar beside it to change its height. Change both and the box grows diagonally from its corner.

Bedrock pins the chat at its top-left corner. To resize it without moving it, the right edge sets the width, the bottom edge sets the height, and the bottom-right corner moves when you change both.

### "Make chat not move, only resize"
Chat stays where the game puts it. The pack only changes its maximum width and height (`$g_chat_max`); its position is never touched.

### "Corner resize of the chat box and right side width resize and height, EXACTLY like resizing an image or text box in Google Slides, but only from the right side for width"
The chat preview grows from its top-left corner, like dragging a corner handle in Google Slides. Width is changed from the right side only, and height from the bottom.

### "If there's no drag way, have a slider that's parallel with the edge and the select point lines up"
Bedrock's UI can't report where a drag ended, so each edge has a bar that runs along it. The bar's handle sits on the box's edge, so dragging the handle drags the edge.

### "Captions resize like chat. Captions are bottom right; captions only change width"
The gold box in the editor is the captions preview, anchored bottom-right like in game. Its bar changes **width only**, and the handle lines up with the box's left edge (`$g_cap_size`).

### "Make the resize generate a preview, make the preview box fullscreen, outline the chat and captions, and show all the counters, not just FPS"
The editor fills the whole screen. Chat (blue) and captions (gold) are drawn at their real screen positions with outlines, and they update live as you drag. The counter preview shows both lines, `FPS 60` and `CPS 8`.

### "Add an FPS counter and a CPS counter"
- **FPS**: worked out from the game's frame time, smoothed and updated 4 times a second.
- **CPS**: arm swings started in the last second, counting hits and air clicks, up to 20.

Both are drawn by the HUD paper doll, so they work with the resource pack alone and need no behavior pack. The `.mcaddon` adds an optional second CPS line that the game's script engine counts.

### "Drag around the counters with a snap to areas (detect the mouse position and move the counter until you release the click)"
The editor has a 3×3 grid of snap spots (top-left … bottom-right). A preview of `FPS 60 / CPS 8` jumps to the spot you pick. You can fine-tune it with the **Move left/right** and **Move down/up** sliders in the gear menu.

Bedrock never tells a pack where the mouse let go, so a free drag can't move the real counter or be saved. That's why it uses snap spots (see [Known limits](#known-limits)).

### "A default button"
**Default** in the editor shows the default layout and the default value of every setting.

### "Scale text size as an option, with a button to toggle scaling the chat text"
- **Chat text:** the editor's text slider previews the size (`$g_chat_text`). The on/off switch is `$g_chat_text_custom` in the config file. `true` makes chat use that size, and `false` (the default) keeps the game's own Chat Settings → Font Size.
- **FPS/CPS text:** the **Text size** slider in the gear menu (50–200 %).

### "Put the HUD button on the pause menu, as its own menu like Déesse UI, with the coordinate values shown"
Press **Esc** and the **HUD Editor** button is at the top left. It opens a separate full-screen editor. The panel at the top right shows the exact value of every setting so you can copy it.

### "Save the values in the pack config button when loading in"
The FPS/CPS settings live in the pack's own settings menu. Open **Settings → Global Resources → HUD Suite → gear icon**. The game saves these for you:

- Show FPS / CPS readout
- Show FPS
- Show CPS
- Text size %
- Move left / right
- Move down / up

### "Persistence via a JSON file, or dump it into a log and read the log"
Chat size, captions size and the counter's screen corner are saved in `ui/_global_variables.json` inside the pack (see [Saving](#saving)). The game only lets the player model read the gear menu settings, and the menus and HUD layout can't read them, so these sizes have to go in the file. Packs can't write files or logs, so you copy the editor's values into it once.

### "Add a v# to the name"
The pack shows as **HUD Suite v3.3** in Global Resources. New versions keep the same pack ID, so they replace the old one instead of piling up copies.

### "Compatible with UI Utils and Déesse UI, latest GDK version, one resource pack"
- Every UI change is a small merge rather than a whole-file replacement: chat max size, captions size, an opt-in chat text size, and the paper doll's spot and size. That lets it stack with UI Utils and Déesse UI.
- Built for the current Bedrock (min engine 1.21.130; the behavior pack uses `@minecraft/server` 2.5.0). The config path under [Saving](#saving) is the one used by the current Windows (GDK) version.
- Everything except the optional script CPS line is in a single `.mcpack`.

---

## Install

1. Open the `.mcpack` (or `.mcaddon`) to import it.
2. Go to **Settings → Global Resources**, activate **HUD Suite v3.3**, and put it **above** UI Utils / Déesse UI.
3. Make sure **Settings → Video → Hide Paperdoll** is **off**, because the FPS/CPS counter is drawn by the paper doll.
4. *(.mcaddon only, optional)* Go to **World → Edit → Behavior Packs** and add **HUD Suite v3.3 - CPS** for the script-counted CPS line.

## Using it

| What | Where |
|---|---|
| Resize chat / captions, pick the counter spot, preview text size, Default | **Esc → HUD Editor** |
| FPS/CPS on/off, text size, move left/right/up/down (saved automatically) | **Settings → Global Resources → HUD Suite → gear** |
| Keep chat/captions sizes and the counter's corner | Config file (below) |

## Saving

Copy the values shown in the editor into:

```
%appdata%\Minecraft Bedrock\users\shared\games\com.mojang\resource_packs\<HUD Suite folder>\ui\_global_variables.json
```

| Key | Meaning | Default |
|---|---|---|
| `$g_chat_max` | chat width, max height | `["100%", "50%"]` |
| `$g_chat_text_custom` | `true` = use `$g_chat_text` instead of the game's font size | `false` |
| `$g_chat_text` | chat text size | `1.0` |
| `$g_cap_size` | captions width | `["30%", "100%"]` |
| `$g_fc_show` | FPS/CPS area on/off | `true` |
| `$g_fc_anchor` | FPS/CPS screen spot | `"top_left"` |
| `$g_fc_offset` | FPS/CPS offset | `[15, 15]` |
| `$g_fc_size` | paper doll frame size | `[15, 15]` |
| `$g_cnt_anchor` / `$g_cnt_offset` / `$g_cnt_scale` | spot and size of the optional script CPS line | `"top_right"` / `[-6, 6]` / `0.9` |

Restart the game (or re-enter the world) to apply. To reset, put the defaults back.

## Known limits

- **No free drag that saves.** Bedrock's UI never reports where something was dragged, so counter spots snap to a grid and edges use bars.
- **Packs can't write files.** Nothing in-game can save to the config file, so editor values are copied by hand. The gear menu settings are the one thing the game saves for you.
- **CPS ceiling.** CPS is counted from arm swings, the same signal other CPS/keystroke packs use. If your game ignores a click while the previous swing is still in its first half, very fast clicking reads about 6 CPS.
- **Paper doll.** In the HUD, the paper doll is replaced by the counter. Your player looks normal everywhere else. A pack that also replaces `player.entity.json` will conflict, and whichever pack is higher in the list wins.
- **Script CPS line** only runs in worlds where you can add behavior packs, not on servers you don't run.

## Build from source

`packs/` holds the generated pack source; `build.py` generates it and the release files.

```
pip install -r requirements.txt   # Pillow (pinned)
python build.py          # -> packs/HUDSuite_RP, packs/HUDSuite_BP, dist/*.mcpack, dist/*.mcaddon
```

`build.py` patches the vanilla `player.entity.json`. It downloads that file once from [Mojang/bedrock-samples](https://github.com/Mojang/bedrock-samples) (pinned to v1.26.60.5) into `vanilla/`.

| File | Purpose |
|---|---|
| `build.py` | manifests and pack settings, HUD overrides, pause-menu HUD Editor, config defaults, CPS script, checks, packaging |
| `readout_entity.py` | FPS/CPS readout: pixel font, 13 pre-shifted geometries, render controller, Molang |
| `tests/` | Molang interpreter + readout tests, CPS script test |
| `.github/workflows/release.yml` | builds from source, tests, and publishes a release (see [Releasing](#releasing)) |

## Tests

```
python tests/test_readout_settings.py   # gear menu settings: on/off, FPS/CPS toggles, size, move
python tests/test_readout_fps_cps.py    # FPS 30-240, CPS 1-20, drop to 0, digit rendering
node   tests/cps_script/test.mjs        # behavior pack CPS script against a mock @minecraft/server
python tests/check_packs_in_sync.py     # after build.py: committed packs/ matches the source
```

## Releasing

Releases are built from source by GitHub Actions:

1. Set the new version in `build.py` (`VER = [major, minor, patch]`), then run `python build.py` and commit `packs/`.
2. Go to **Actions → Release → Run workflow**.

The workflow builds the `.mcpack` and `.mcaddon` from source, runs the tests, and publishes a release tagged `v<version>` with both files attached. It has three options:

- **notes**: extra text added to the release notes.
- **overwrite**: if that version is already released, replace its files.
- **dry_run**: build and test only. The files go to the run's artifacts instead of a release.

## License

[MIT](LICENSE).

## Credits

- Title "preserved text" pattern from [LeGend077/json-ui-examples](https://github.com/LeGend077/json-ui-examples) (MIT).
- The paper-doll FPS/CPS technique was studied in Modules+ and OpenQuasar. The implementation, font and models here are original.
