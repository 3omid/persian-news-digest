// موقت: کدوم سرویس ترجمه از سرورهای Cloudflare جواب می‌ده؟ (بعد از تست حذف می‌شه)
const T = ["Tesla profits drop 43% in Q3", "Rice strikes to earn Arsenal draw at Bayern"];
const UA = { "User-Agent": "Mozilla/5.0 (compatible; NewsDigest/1.0)" };
async function tryIt(name, fn) {
  try {
    const r = await fn();
    const text = await r.text();
    return { name, status: r.status, body: text.slice(0, 300) };
  } catch (e) {
    return { name, error: String(e?.message || e) };
  }
}
export async function onRequestGet() {
  const q = encodeURIComponent(T.join("\n"));
  const results = await Promise.all([
    tryIt("gtx-post", () => fetch("https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=fa&dt=t", { method: "POST", body: new URLSearchParams({ q: T.join("\n") }), headers: { ...UA, "Content-Type": "application/x-www-form-urlencoded" } })),
    tryIt("gtx-get", () => fetch(`https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=fa&dt=t&q=${q}`, { headers: UA })),
    tryIt("clients5", () => fetch(`https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl=auto&tl=fa&q=${encodeURIComponent(T[0])}&q=${encodeURIComponent(T[1])}`, { headers: UA })),
    tryIt("gtx-t", () => fetch(`https://translate.googleapis.com/translate_a/t?client=gtx&sl=auto&tl=fa&q=${encodeURIComponent(T[0])}&q=${encodeURIComponent(T[1])}`, { headers: UA })),
    tryIt("mymemory", () => fetch(`https://api.mymemory.translated.net/get?q=${encodeURIComponent(T[0])}&langpair=en|fa`, { headers: UA })),
  ]);
  return new Response(JSON.stringify(results, null, 1), { headers: { "Content-Type": "application/json; charset=utf-8" } });
}
