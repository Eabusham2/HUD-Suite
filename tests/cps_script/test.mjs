// Runs packs/HUDSuite_BP/scripts/main.js against a mock of @minecraft/server.   node tests/cps_script/test.mjs
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
const here = fileURLToPath(new URL('.', import.meta.url));
const src = readFileSync(here + '../../packs/HUDSuite_BP/scripts/main.js', 'utf8').replace('"@minecraft/server"', '"./mock_server.mjs"');
writeFileSync(here + 'main.under_test.mjs', src);
const mc = await import('./mock_server.mjs');
let now = 1_000_000; Date.now = () => now;
await import('./main.under_test.mjs');
const tick = () => mc.interval.fn();
const last = () => mc.titles.at(-1)?.t;
const click = (src = 'Attack') => mc.fire('swing', { player: mc.players[0], swingSource: src });
let ok = true; const expect = (c, m) => { console.log((c ? 'PASS ' : 'FAIL ') + m); ok &&= c; };

expect(mc.interval.ticks === 2, 'updates every 2 ticks');
tick(); expect(last() === 'hscps:0', 'sends 0 on first update');
const n0 = mc.titles.length; tick(); tick(); expect(mc.titles.length === n0, 'idle: no repeated titles');
for (let i = 0; i < 12; i++) { click(); now += 70; }            // 12 clicks in 840 ms
tick(); expect(last() === 'hscps:12', `12 clicks in <1s -> ${last()}`);
click('Build'); click('Interact'); click('Mine'); click('DropItem');
tick(); expect(last() === 'hscps:12', 'right-click/place/mine/drop swings ignored');
click('None'); tick(); expect(last() === 'hscps:13', 'source None (air) counted');
now += 1100; tick(); expect(last() === 'hscps:0', 'drops to 0 after 1s without clicks');
const o = mc.titles.at(-1).o; expect(o.fadeInDuration === 0 && o.fadeOutDuration === 0 && o.stayDuration === 10, 'title options');
mc.fire('spawn', { player: mc.players[0], initialSpawn: false }); tick(); expect(last() === 'hscps:0' && mc.titles.at(-2)?.t === 'hscps:0', 'resends after respawn');
mc.fire('leave', { playerId: 'p1' }); expect(true, 'leave handler ran');
// sliding window: 1 click every 100ms for 3s -> steady ~10
for (let i = 0; i < 30; i++) { click(); now += 100; tick(); }
const v = +last().slice(6); expect(v >= 9 && v <= 11, `steady 10 cps -> ${v}`);
process.exit(ok ? 0 : 1);
