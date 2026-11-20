// HUD Suite v3.3 - CPS counter.
// Counts arm swings that start a click (Attack = hits and air clicks) over the last second,
// and hands the number to the resource pack through a hidden title ("hscps:<n>").
import { world, system, EntitySwingSource } from "@minecraft/server";

// ---- settings ----
const WINDOW_MS = 1000;
// Add EntitySwingSource.Mine to also count swings while breaking blocks
// (holding the button on a block then counts as repeated clicks).
const COUNTED = new Set([EntitySwingSource.Attack, EntitySwingSource.None]);
const MARKER = "hscps:";
// ------------------

const swings = new Map();   // player id -> swing timestamps (ms)
const shown = new Map();    // player id -> last value sent

world.afterEvents.playerSwingStart.subscribe(({ player, swingSource }) => {
  if (!COUNTED.has(swingSource)) return;
  let list = swings.get(player.id);
  if (!list) swings.set(player.id, (list = []));
  list.push(Date.now());
});

system.runInterval(() => {
  const now = Date.now();
  for (const player of world.getAllPlayers()) {
    const list = swings.get(player.id);
    while (list && list.length && now - list[0] > WINDOW_MS) list.shift();
    const cps = list ? list.length : 0;
    if (shown.get(player.id) === cps) continue;   // only send changes: real titles stay untouched while idle
    shown.set(player.id, cps);
    try {
      player.onScreenDisplay.setTitle(MARKER + cps, { fadeInDuration: 0, stayDuration: 10, fadeOutDuration: 0 });
    } catch { /* player not ready yet */ }
  }
}, 2);

world.afterEvents.playerSpawn.subscribe(({ player }) => shown.delete(player.id));   // resend after join/respawn
world.afterEvents.playerLeave.subscribe(({ playerId }) => { swings.delete(playerId); shown.delete(playerId); });
