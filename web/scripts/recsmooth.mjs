import fs from "node:fs";

const [,, URL, MS, DIR, PORT, ONLY] = process.argv;
const FPS = 60;
const duration = Number(MS);
const N = ONLY ? 1 : Math.round((duration / 1000) * FPS);
const step = 1000 / FPS;
fs.rmSync(DIR, { recursive: true, force: true });
fs.mkdirSync(DIR, { recursive: true });

const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
const page = list.find((t) => t.type === "page");
if (!page) throw new Error("no page target");
const ws = new WebSocket(page.webSocketDebuggerUrl.replace("localhost", "127.0.0.1"));
let id = 0;
const pend = new Map();
const send = (method, params = {}) =>
  new Promise((resolve) => {
    const i = ++id;
    pend.set(i, resolve);
    ws.send(JSON.stringify({ id: i, method, params }));
  });
await new Promise((resolve) => (ws.onopen = resolve));
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  if (message.id && pend.has(message.id)) {
    pend.get(message.id)(message.result);
    pend.delete(message.id);
  }
};
const ev = (expression, awaitPromise = false) =>
  send("Runtime.evaluate", { expression, awaitPromise });
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

await send("Page.enable");
await send("Runtime.enable");
await send("Emulation.setDeviceMetricsOverride", {
  width: 1600,
  height: 900,
  deviceScaleFactor: 1,
  mobile: false,
});
await send("Page.addScriptToEvaluateOnNewDocument", {
  source: "window.__REC__=true; window.__vt=0;",
});
await send("Page.navigate", { url: URL });
await sleep(1800);
await ev("document.fonts && document.fonts.ready", true).catch(() => {});

for (let i = 0; i < N; i++) {
  const t = ONLY ? Number(ONLY) : Math.round(i * step);
  await ev(`window.__vt=${t}; window.dispatchEvent(new Event('vt'));`);
  await ev("new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))", true);
  const shot = await send("Page.captureScreenshot", { format: "png" });
  const name = ONLY ? "preview.png" : `f${String(i).padStart(4, "0")}.png`;
  fs.writeFileSync(`${DIR}/${name}`, Buffer.from(shot.data, "base64"));
  if (i % 120 === 0) console.log("frame", i, "t", t);
}
ws.close();
console.log("wrote", N, "to", DIR);
