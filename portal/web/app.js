/* سه‌سبد — single-page UI (no build step). Hash routes: #/ #/signup #/login #/risk #/result #/billing #/dashboard #/founder */
"use strict";

// ------------------------------------------------------------------ helpers
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fa = (n, d = 0) => (n == null || Number.isNaN(+n)) ? "—"
  : new Intl.NumberFormat("fa-IR", { maximumFractionDigits: d, minimumFractionDigits: d }).format(+n);
const tmn = (n) => n == null ? "—" : fa(Math.round(n)) + " تومان";
// big money figure: the unit is set smaller so long amounts stay on one line
const money = (n) => n == null ? "—" : `${fa(Math.round(n))} <small class="unit">تومان</small>`;
// signed figures are isolated left-to-right, otherwise the sign and the percent sign land on the wrong side in RTL
const signed = (n, d = 2) => n == null ? "—" : `<bdi dir="ltr">${n > 0 ? "+" : n < 0 ? "−" : ""}${fa(Math.abs(n), d)}</bdi>`;
const pct = (n, d = 2) => n == null ? "—" : `<bdi dir="ltr">${n > 0 ? "+" : n < 0 ? "−" : ""}${fa(Math.abs(n), d)}٪</bdi>`;
const tone = (n) => n > 0 ? "gain" : n < 0 ? "loss" : "";
const faDigits = (s) => String(s ?? "").replace(/(\d)\.(\d)/g, "$1٫$2").replace(/\d/g, (d) => "۰۱۲۳۴۵۶۷۸۹"[d]);
const parseNum = (s) => +String(s).replace(/[۰-۹]/g, (d) => "۰۱۲۳۴۵۶۷۸۹".indexOf(d)).replace(/[^\d.]/g, "") || 0;
const clock = (ts) => ts ? new Intl.DateTimeFormat("fa-IR", { hour: "2-digit", minute: "2-digit" }).format(ts * 1000) : "—";
const when = (ts) => ts ? new Intl.DateTimeFormat("fa-IR", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(ts * 1000) : "—";
const day = (ts) => ts ? new Intl.DateTimeFormat("fa-IR", { year: "numeric", month: "long", day: "numeric" }).format(ts * 1000) : "—";
const ago = (s) => s == null ? "—" : s < 90 ? "همین حالا" : s < 3600 ? `${fa(Math.round(s / 60))} دقیقه پیش` : s < 86400 ? `${fa(Math.round(s / 3600))} ساعت پیش` : `${fa(Math.round(s / 86400))} روز پیش`;
const RISK = [["low", "c-low", "t-low", "کم‌ریسک"], ["medium", "c-mid", "t-mid", "متوسط"], ["high", "c-high", "t-high", "پرریسک"]];

async function api(path, body, method) {
  const o = { method: method || (body ? "POST" : "GET"), headers: { "X-Requested-With": "tmn" }, credentials: "same-origin" };
  if (body) { o.headers["Content-Type"] = "application/json"; o.body = JSON.stringify(body); }
  const r = await fetch(path, o);
  let data = {};
  try { data = await r.json(); } catch (_) { /* empty body */ }
  if (!r.ok) { const e = new Error(data.error || "ارتباط با سرور برقرار نشد. دوباره امتحان کنید."); e.status = r.status; throw e; }
  return data;
}

function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(toast.h);
  toast.h = setTimeout(() => t.classList.remove("show"), 3200);
}

const S = { me: { user: null }, meta: null, timers: [] };
const every = (ms, fn) => { S.timers.push(setInterval(fn, ms)); };
const go = (h) => { if (location.hash === h) route(); else location.hash = h; };

function splitBar(alloc, tall) {
  return `<div class="split${tall ? " tall" : ""}" role="img" aria-label="کم‌ریسک ${fa(alloc.low)}٪، متوسط ${fa(alloc.medium)}٪، پرریسک ${fa(alloc.high)}٪">`
    + RISK.map(([k, c]) => `<span class="${c}" style="flex-grow:${Math.max(0, alloc[k])}"></span>`).join("") + "</div>";
}

function legend(alloc, amounts) {
  return `<div class="legend">` + RISK.map(([k, , t, name]) => `<div class="${t}"><div class="k">${name}</div>
    <div class="v num">${fa(alloc[k])}٪</div>${amounts ? `<div class="a num">${tmn(amounts[k])}</div>` : ""}</div>`).join("") + `</div>`;
}

function allocFor(score) {
  const A = S.meta.anchors;
  const s = Math.max(0, Math.min(100, score));
  for (let i = 0; i < A.length - 1; i++) {
    const [s0, a0] = A[i], [s1, a1] = A[i + 1];
    if (s >= s0 && s <= s1) {
      const t = (s - s0) / (s1 - s0);
      const high = Math.round(a0[2] + (a1[2] - a0[2]) * t), medium = Math.round(a0[1] + (a1[1] - a0[1]) * t);
      return { low: 100 - high - medium, medium, high };
    }
  }
  return { low: 100, medium: 0, high: 0 };
}
const profileFor = (s) => S.meta.profiles.find((p) => s < p.upto) || S.meta.profiles[S.meta.profiles.length - 1];

function expectedFor(alloc) {
  const st = Object.fromEntries(S.meta.strategies.map((x) => [x.key, x.backtest]));
  let mean = 0, worst = 0;
  for (const k of ["low", "medium", "high"]) { mean += alloc[k] / 100 * st[k].mean_pct; worst += alloc[k] / 100 * st[k].worst_pct; }
  return { mean, worst };
}

function regimeLine(m) {
  if (!m || !m.regime || m.regime.ch48_pct == null) return `<span class="dot"></span> قیمت‌های بازار هنوز دریافت نشده است`;
  const r = m.regime, src = m.source === "replay" ? " (داده‌ی بازپخش آفلاین)" : "";
  const dot = !m.fresh ? "err" : r.on ? "on" : "off";
  return `<span class="dot ${dot}"></span><span>تتر/تومان در ۴۸ ساعت <b class="num ltr">${pct(r.ch48_pct)}</b>؛ ${r.on
    ? "شرط ورود سبدها برقرار است" : `سبدها منتظرند تا رشد به ${fa(r.threshold_pct)}٪ برسد`}${src}</span>`;
}

// ------------------------------------------------------------------ chart
function lineChart(el, rows, opt = {}) {
  if (!rows || rows.length < 2) { el.innerHTML = `<div class="chart-empty">${opt.empty || "هنوز داده‌ای برای نمودار نیست؛ چند دقیقه صبر کنید."}</div>`; return; }
  const W = 800, H = 260, P = { l: 8, r: 70, t: 14, b: 26 };
  const xs = rows.map((r) => r[0]), ys = rows.map((r) => r[1]);
  let lo = Math.min(...ys, opt.base ?? Infinity), hi = Math.max(...ys, opt.base ?? -Infinity);
  if (hi - lo < hi * 0.002) { lo -= hi * 0.001 + 1; hi += hi * 0.001 + 1; }
  const pad = (hi - lo) * 0.08; lo -= pad; hi += pad;
  const x = (t) => P.l + (t - xs[0]) / (xs[xs.length - 1] - xs[0] || 1) * (W - P.l - P.r);
  const y = (v) => P.t + (1 - (v - lo) / (hi - lo)) * (H - P.t - P.b);
  const pts = rows.map((r) => `${x(r[0]).toFixed(1)},${y(r[1]).toFixed(1)}`);
  const color = opt.color || "var(--lapis)";
  const last = ys[ys.length - 1];
  const ticks = [hi - pad, (hi + lo) / 2, lo + pad];
  const fmt = opt.fmt || ((v) => fa(v / 1e6, 2) + "م");
  el.innerHTML = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" aria-label="${esc(opt.label || "نمودار ارزش")}">
    ${ticks.map((v) => `<line x1="${P.l}" x2="${W - P.r}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line)" stroke-width="1"/>
      <text x="${W - P.r + 8}" y="${y(v) + 4}" font-size="12" fill="var(--muted)">${fmt(v)}</text>`).join("")}
    ${opt.base != null ? `<line x1="${P.l}" x2="${W - P.r}" y1="${y(opt.base)}" y2="${y(opt.base)}" stroke="var(--muted)" stroke-dasharray="4 4" stroke-width="1"/>` : ""}
    <polygon points="${P.l},${H - P.b} ${pts.join(" ")} ${x(xs[xs.length - 1])},${H - P.b}" fill="${color}" opacity=".10"/>
    <polyline points="${pts.join(" ")}" fill="none" stroke="${color}" stroke-width="2.2" vector-effect="non-scaling-stroke" stroke-linejoin="round"/>
    <circle cx="${x(xs[xs.length - 1])}" cy="${y(last)}" r="4" fill="${color}"/>
    <text x="${P.l}" y="${H - 6}" font-size="12" fill="var(--muted)">${esc(when(xs[0]))}</text>
    <text x="${W - P.r}" y="${H - 6}" font-size="12" fill="var(--muted)" text-anchor="end">${esc(when(xs[xs.length - 1]))}</text>
    <line class="hair" x1="0" x2="0" y1="${P.t}" y2="${H - P.b}" stroke="var(--muted)" stroke-width="1" visibility="hidden"/>
  </svg><div class="tip" hidden></div>`;
  const svg = $("svg", el), tip = $(".tip", el), hair = $(".hair", el);
  const move = (ev) => {
    const b = svg.getBoundingClientRect();
    const vx = (ev.clientX - b.left) / b.width * W;
    let i = 0, best = Infinity;
    rows.forEach((r, j) => { const d = Math.abs(x(r[0]) - vx); if (d < best) { best = d; i = j; } });
    hair.setAttribute("x1", x(rows[i][0])); hair.setAttribute("x2", x(rows[i][0])); hair.setAttribute("visibility", "visible");
    tip.hidden = false;
    tip.style.left = `${x(rows[i][0]) / W * 100}%`;
    tip.textContent = `${when(rows[i][0])} — ${tmn(rows[i][1])}`;
  };
  svg.addEventListener("pointermove", move);
  svg.addEventListener("pointerleave", () => { tip.hidden = true; hair.setAttribute("visibility", "hidden"); });
}

function gauge(score) {
  const cx = 160, cy = 160, r = 130;
  const p = (v) => { const a = Math.PI * v / 100; return [cx + r * Math.cos(a), cy - r * Math.sin(a)]; };
  const arc = (v1, v2, c) => { const [x1, y1] = p(v1), [x2, y2] = p(v2); return `<path d="M${x1} ${y1} A${r} ${r} 0 0 0 ${x2} ${y2}" stroke="${c}" stroke-width="22" fill="none"/>`; };
  const [nx, ny] = p(score);
  return `<svg class="gauge" viewBox="0 0 320 190" role="img" aria-label="نمره‌ی ریسک ${fa(score)} از ۱۰۰">
    ${arc(0.6, 19.4, "var(--low)")}${arc(20.6, 39.4, "color-mix(in srgb, var(--low) 50%, var(--mid))")}${arc(40.6, 59.4, "var(--mid)")}
    ${arc(60.6, 79.4, "color-mix(in srgb, var(--mid) 50%, var(--high))")}${arc(80.6, 99.4, "var(--high)")}
    <line x1="${cx}" y1="${cy}" x2="${nx}" y2="${ny}" stroke="var(--ink)" stroke-width="4" stroke-linecap="round"/>
    <circle cx="${cx}" cy="${cy}" r="9" fill="var(--ink)"/>
    <text x="${cx}" y="${cy - 34}" text-anchor="middle" font-size="44" font-weight="900">${fa(score, 0)}</text>
    <text x="${cx + r}" y="${cy + 26}" text-anchor="middle" font-size="13" fill="var(--muted)">۰</text>
    <text x="${cx - r}" y="${cy + 26}" text-anchor="middle" font-size="13" fill="var(--muted)">۱۰۰</text>
  </svg>`;
}

// ------------------------------------------------------------------ nav + router
function nav(cur) {
  const u = S.me.user, link = (h, t) => `<a href="#/${h}"${cur === h ? ' aria-current="page"' : ""}>${t}</a>`;
  $("#nav").innerHTML = !u
    ? `${link("login", "ورود")}<a class="btn primary small" href="#/signup">ثبت‌نام</a>`
    : (u.role === "founder" ? link("founder", "اتاق کنترل") : link("dashboard", "داشبورد"))
      + link(S.me.profile ? "result" : "risk", "پروفایل ریسک") + (u.role === "founder" ? "" : link("billing", "اشتراک"))
      + `<span class="who">${esc(u.name)}</span><a href="#/logout">خروج</a>`;
}

const ROUTES = { "": landing, login, signup, risk: quiz, result, billing: billingPage, dashboard, founder, logout };
const PRIVATE = new Set(["risk", "result", "billing", "dashboard", "founder"]);

async function route() {
  S.timers.forEach(clearInterval); S.timers = [];
  const [path, qs] = location.hash.replace(/^#\/?/, "").split("?");
  const params = new URLSearchParams(qs || "");
  const view = ROUTES[path] ? path : "";
  if (PRIVATE.has(view) && !S.me.user) return go(`#/login?next=${view}`);
  nav(view);
  const main = $("#view");
  try {
    await ROUTES[view](main, params);
  } catch (e) {
    if (e.status === 401) { S.me = { user: null }; return go(`#/login?next=${view}`); }
    main.innerHTML = `<div class="wrap page"><div class="panel empty"><h2>این صفحه باز نشد</h2><p>${esc(e.message)}</p>
      <button class="btn" id="retry">دوباره امتحان کنید</button></div></div>`;
    $("#retry").onclick = route;
  }
  if (!params.has("keep")) window.scrollTo(0, 0);
}

async function refreshMe() { S.me = await api("/api/me"); }

// ------------------------------------------------------------------ landing
async function landing(main) {
  const m = S.meta;
  const st = m.strategies;
  main.innerHTML = `
  <section class="hero"><div class="wrap hero-grid">
    <div>
      <h1>ربات معامله‌گری که به اندازه‌ی ریسک‌پذیری شما معامله می‌کند</h1>
      <p class="lead">به ${fa(m.questions)} سؤال جواب بدهید. سرمایه‌ی شما بین سه استراتژی کم‌ریسک، متوسط و پرریسک تقسیم می‌شود و ربات به‌طور شبانه‌روزی روی بازارهای تومانی والکس معامله می‌کند.</p>
      <div class="cta-row">
        <a class="btn primary" href="${S.me.user ? "#/risk" : "#/signup?next=risk"}">شروع پرسشنامه</a>
        ${S.me.user ? `<a class="btn" href="#/${S.me.user.role === "founder" ? "founder" : "dashboard"}">داشبورد من</a>` : `<a class="btn" href="#/login">ورود</a>`}
      </div>
      <p class="regime-line">${regimeLine(m.market)}</p>
    </div>
    <div class="dial" aria-labelledby="dialh">
      <div class="dial-top"><h2 id="dialh">سرمایه‌تان چطور تقسیم می‌شود؟</h2><span class="pname" id="pname"></span></div>
      <label class="small muted" for="rs">ریسک‌پذیری را جابه‌جا کنید</label>
      <input class="range" id="rs" type="range" min="0" max="100" value="55" aria-describedby="pname">
      <div class="range-scale"><span>محافظه‌کار</span><span>جسور</span></div>
      <div class="cap"><label for="cap" class="small">سرمایه</label><input class="input num" id="cap" inputmode="numeric" value="50,000,000"><span class="small muted">تومان</span></div>
      <div id="dsplit"></div><div id="dleg"></div>
      <div class="dial-stats">
        <div><span class="small muted">میانگین بک‌تست (۲۷ ساعت)</span><b class="num" id="dmean"></b></div>
        <div><span class="small muted">بدترین نتیجه‌ی بک‌تست</span><b class="num" id="dworst"></b></div>
      </div>
    </div>
  </div></section>

  <section class="band" id="how"><div class="wrap">
    <h2>از ثبت‌نام تا اولین معامله</h2>
    <p class="intro">چهار قدم؛ ربات بعد از آن خودش کار می‌کند و شما هر لحظه سود و زیان و دلیل هر معامله را می‌بینید.</p>
    <ol class="steps">
      <li><h3>ثبت‌نام</h3><p>با ایمیل حساب بسازید.</p></li>
      <li><h3>پرسشنامه‌ی ریسک</h3><p>${fa(m.questions)} سؤال درباره‌ی توان مالی و تحمل شما در برابر ضرر.</p></li>
      <li><h3>تخصیص و اشتراک</h3><p>سهم هر استراتژی را می‌بینید، در صورت تمایل محافظه‌کارانه‌ترش می‌کنید و اشتراک می‌خرید.</p></li>
      <li><h3>شروع ربات</h3><p>ربات با همان قوانین ربات اصلی برای شما معامله می‌کند.</p></li>
    </ol>
  </div></section>

  <section class="band" id="strategies"><div class="wrap">
    <h2>سه استراتژی، سه سطح ریسک</h2>
    <p class="intro">هر سه از یک موتور معاملاتی می‌آیند که همین حالا روی حساب بنیان‌گذار در والکس کار می‌کند. عددها نتیجه‌ی بک‌تست بعد از کارمزد هستند.</p>
    <div class="ladder">${st.map((s, i) => `<article class="rung ${RISK[i][2]}">
      <h3>${esc(s.name)}</h3><div class="assets">${esc(faDigits(s.assets))}</div><p>${esc(faDigits(s.how))}</p>
      <div class="bt"><div><span>میانگین</span><b class="num">${pct(s.backtest.mean_pct)}</b></div>
      <div><span>احتمال ضرر</span><b class="num">${s.backtest.p_loss_pct == null ? "—" : fa(s.backtest.p_loss_pct) + "٪"}</b></div>
      <div><span>بدترین</span><b class="num">${pct(s.backtest.worst_pct)}</b></div></div></article>`).join("")}</div>
    <div class="honest"><p><b>صادقانه:</b> بک‌تست‌ها روی ۲۹ روز داده‌ی ساعتی والکس و پنجره‌های ۲۷ ساعته انجام شده‌اند. سود سبدهای متوسط و پرریسک به ادامه‌ی روند تضعیف ریال بستگی دارد؛ در بازار بدون روند، نتیجه نزدیک صفر یا منفی بوده است. ربات فقط وقتی وارد این سبدها می‌شود که تتر/تومان در ۴۸ ساعت حداقل ${fa((m.market.regime && m.market.regime.threshold_pct) || 1)}٪ رشد کرده باشد.</p></div>
  </div></section>

  <section class="band" id="plans"><div class="wrap">
    <h2>اشتراک</h2>
    <p class="intro">ربات فقط با اشتراک فعال برای شما معامله می‌کند. همه‌ی پلن‌ها امکانات یکسان دارند.</p>
    ${plansHtml(m.plans, false)}
    <ul class="features">${m.features.map((f) => `<li>${esc(f)}</li>`).join("")}</ul>
  </div></section>`;

  const rs = $("#rs"), cap = $("#cap");
  const draw = () => {
    const s = +rs.value, a = allocFor(s), c = parseNum(cap.value), e = expectedFor(a);
    $("#pname").textContent = profileFor(s).name;
    $("#dsplit").innerHTML = splitBar(a, true);
    $("#dleg").innerHTML = legend(a, { low: c * a.low / 100, medium: c * a.medium / 100, high: c * a.high / 100 });
    $("#dmean").innerHTML = `<span class="${tone(e.mean)}">${pct(e.mean)}</span>`;
    $("#dworst").innerHTML = `<span class="${tone(e.worst)}">${pct(e.worst)}</span>`;
  };
  rs.oninput = draw;
  cap.oninput = () => { const n = parseNum(cap.value); cap.value = n ? n.toLocaleString("en-US") : ""; draw(); };
  draw();
}

function plansHtml(plans, buy) {
  return `<div class="plans">${plans.map((p) => `<article class="plan${p.key === "quarterly" ? " best" : ""}">
    <h3>${esc(p.name)}${p.badge ? `<span class="badge">${esc(p.badge)}</span>` : ""}</h3>
    <div class="price num">${fa(p.price_tmn)}</div><div class="per">تومان برای ${fa(p.days)} روز</div>
    ${buy ? `<button class="btn ${p.key === "quarterly" ? "primary" : ""}" data-plan="${esc(p.key)}">خرید اشتراک ${esc(p.name)}</button>`
    : `<a class="btn ${p.key === "quarterly" ? "primary" : ""}" href="${S.me.user ? "#/billing" : "#/signup?next=billing"}">انتخاب ${esc(p.name)}</a>`}
  </article>`).join("")}</div>`;
}

// ------------------------------------------------------------------ auth
function authForm(main, kind, params) {
  const sign = kind === "signup";
  main.innerHTML = `<div class="auth">
    <h1>${sign ? "ساخت حساب" : "ورود به حساب"}</h1>
    <p class="muted">${sign ? "بعد از ثبت‌نام مستقیم به پرسشنامه‌ی ریسک می‌روید." : "با ایمیل و رمز عبورتان وارد شوید."}</p>
    <form class="panel" id="f" novalidate>
      ${sign ? `<div class="field"><label for="name">نام</label><input class="input" id="name" autocomplete="name" required></div>` : ""}
      <div class="field"><label for="email">ایمیل</label><input class="input ltr" id="email" type="email" autocomplete="email" required></div>
      <div class="field"><label for="pw">رمز عبور</label><input class="input ltr" id="pw" type="password" autocomplete="${sign ? "new-password" : "current-password"}" required>
        ${sign ? `<span class="small muted">حداقل ۸ کاراکتر، ترکیبی از حرف و عدد</span>` : ""}</div>
      <p class="err" id="err" role="alert"></p>
      <button class="btn primary" style="width:100%" type="submit">${sign ? "ساخت حساب" : "ورود"}</button>
    </form>
    <p class="small muted" style="margin-top:14px">${sign ? `حساب دارید؟ <a href="#/login${params.get("next") ? "?next=" + esc(params.get("next")) : ""}">وارد شوید</a>`
    : `حساب ندارید؟ <a href="#/signup${params.get("next") ? "?next=" + esc(params.get("next")) : ""}">ثبت‌نام کنید</a>`}</p>
  </div>`;
  $("#f").onsubmit = async (ev) => {
    ev.preventDefault();
    const btn = $("button[type=submit]", ev.target);
    btn.disabled = true; $("#err").textContent = "";
    try {
      const body = { email: $("#email").value, password: $("#pw").value };
      if (sign) body.name = $("#name").value;
      await api(sign ? "/api/auth/signup" : "/api/auth/login", body);
      await refreshMe();
      const next = params.get("next");
      const allowed = ["risk", "result", "billing", "dashboard", "founder"];
      go("#/" + (allowed.includes(next) ? next : sign ? "risk" : S.me.user.role === "founder" ? "founder" : "dashboard"));
    } catch (e) { $("#err").textContent = e.message; btn.disabled = false; }
  };
  $(sign ? "#name" : "#email").focus();
}
function signup(main, p) { return authForm(main, "signup", p); }
function login(main, p) { return authForm(main, "login", p); }
async function logout() { await api("/api/auth/logout", {}); S.me = { user: null }; go("#/"); }

// ------------------------------------------------------------------ questionnaire
async function quiz(main) {
  const { questions } = await api("/api/risk/questions");
  const answers = Object.assign({}, (S.me.profile && S.me.profile.answers) || {});
  let i = 0;
  const draw = () => {
    const q = questions[i], n = questions.length, last = i === n - 1;
    main.innerHTML = `<div class="quiz">
      <div class="qprog" aria-hidden="true">${questions.map((x, j) => `<span class="${j < i ? "done" : j === i ? "cur" : ""}"></span>`).join("")}</div>
      <div class="qdims"><span>ظرفیت ریسک: توان مالی شما</span><span>تمایل به ریسک: نگاه شما به ضرر</span></div>
      <div class="qcount">سؤال ${fa(i + 1)} از ${fa(n)}</div>
      <h2 id="qt">${esc(q.title)}</h2>
      <div class="opts" role="radiogroup" aria-labelledby="qt">${q.options.map((o, j) => `<button class="opt" role="radio" aria-checked="${answers[q.id] === j}" data-j="${j}"><kbd>${fa(j + 1)}</kbd><span>${esc(o)}</span></button>`).join("")}</div>
      <p class="err" id="err" role="alert"></p>
      <div class="quiz-nav">
        <button class="btn ghost" id="prev" ${i === 0 ? "disabled" : ""}>سؤال قبلی</button>
        <button class="btn primary" id="next" ${answers[q.id] == null ? "disabled" : ""}>${last ? "ثبت پاسخ‌ها و دیدن نتیجه" : "سؤال بعدی"}</button>
      </div></div>`;
    const pick = (j) => {
      answers[q.id] = j;
      $$(".opt").forEach((b) => b.setAttribute("aria-checked", String(+b.dataset.j === j)));
      $("#next").disabled = false;
      if (!last) setTimeout(() => { if (questions[i] === q) { i++; draw(); } }, 260);
    };
    $$(".opt").forEach((b) => { b.onclick = () => pick(+b.dataset.j); });
    $("#prev").onclick = () => { i--; draw(); };
    $("#next").onclick = async () => {
      if (!last) { i++; return draw(); }
      $("#next").disabled = true;
      try {
        await api("/api/risk/submit", { answers });
        await refreshMe();
        go("#/result");
      } catch (e) { $("#err").textContent = e.message; $("#next").disabled = false; }
    };
    const sel = $(".opt[aria-checked=true]") || $(".opt");
    sel.focus();
  };
  document.onkeydown = (ev) => {
    if (!location.hash.startsWith("#/risk")) { document.onkeydown = null; return; }
    const d = "۱۲۳۴۵".indexOf(ev.key) >= 0 ? "۱۲۳۴۵".indexOf(ev.key) + 1 : +ev.key;
    if (d >= 1 && d <= 5) { const b = $(`.opt[data-j="${d - 1}"]`); if (b) b.click(); }
  };
  draw();
}

// ------------------------------------------------------------------ result
async function result(main) {
  const [{ profile: p, strategies, profile_desc }, botInfo] = await Promise.all([api("/api/risk/profile"), api("/api/bot")]);
  if (!p) return go("#/risk");
  const bot = botInfo.bot, rec = p.allocation, master = bot.mode === "master";
  const locked = master || bot.status === "running";
  let cur = master ? S.meta.founder_allocation : { ...bot.allocation };
  if (cur.low + cur.medium + cur.high !== 100) cur = { ...rec };
  main.innerHTML = `<div class="wrap page">
    <div class="result-top">
      <div>${gauge(p.score)}</div>
      <div>
        <div class="muted">پروفایل ریسک شما</div>
        <div class="pname-big">${esc(p.profile_name)}</div>
        <p class="muted" style="max-width:36em">${esc(profile_desc)}</p>
        <div class="dims">
          <div class="meter"><span>ظرفیت ریسک</span><i style="--w:${p.capacity}%"></i><b class="num">${fa(p.capacity)}</b></div>
          <div class="meter"><span>تمایل به ریسک</span><i style="--w:${p.willingness}%"></i><b class="num">${fa(p.willingness)}</b></div>
        </div>
        <p class="small muted" style="margin-top:10px">نمره‌ی نهایی میانگین این دو است، ولی بیش از ۱۰ امتیاز بالاتر از عدد کمتر نمی‌رود.</p>
      </div>
    </div>

    <div class="panel" style="margin-top:28px">
      <h2>${master ? "تخصیص ربات اصلی (از config.yaml)" : "تخصیص سرمایه‌ی شما"}</h2>
      <div id="split"></div>
      <div id="rows"></div>
      ${master ? `<p class="notice">حساب شما به ربات اصلی روی لیارا وصل است. تخصیص آن ${fa(cur.low)}/${fa(cur.medium)}/${fa(cur.high)} است و فقط از config.yaml عوض می‌شود. پیشنهاد پرسشنامه برای شما: ${fa(rec.low)}/${fa(rec.medium)}/${fa(rec.high)}.</p>`
    : locked ? `<p class="notice warn">ربات در حال معامله است. برای تغییر تخصیص، اول ربات را از داشبورد متوقف کنید.</p>`
      : `<h3 style="margin-top:22px">محافظه‌کارانه‌ترش کنید (اختیاری)</h3>
      <p class="small muted">پیشنهاد پروفایل شما ${fa(rec.low)}٪ / ${fa(rec.medium)}٪ / ${fa(rec.high)}٪ است. می‌توانید سهم پرریسک و متوسط را کم کنید، ولی بیشتر از پیشنهاد نه.</p>
      <div class="sliders">
        <div class="slider-row t-high"><label for="sh">سهم پرریسک</label><input type="range" id="sh" min="0" max="${rec.high}" value="${cur.high}" style="--c:var(--high)"><b class="num" id="vh"></b></div>
        <div class="slider-row t-mid"><label for="sm">سهم متوسط</label><input type="range" id="sm" min="0" value="${cur.medium}"><b class="num" id="vm"></b></div>
      </div>`}
      <div class="dial-stats" style="max-width:520px">
        <div><span class="small muted">میانگین بک‌تست (۲۷ ساعت)</span><b class="num" id="emean"></b></div>
        <div><span class="small muted">بدترین حالت ترکیبی</span><b class="num" id="eworst"></b></div>
      </div>
      <p class="small muted" style="margin-top:8px">${esc(p.expected.note)}</p>
      <p class="err" id="err" role="alert"></p>
      <div class="cta-row">
        ${master ? `<a class="btn primary" href="#/founder">اتاق کنترل</a>` : locked ? `<a class="btn primary" href="#/dashboard">داشبورد</a>`
      : `<button class="btn primary" id="ok">تأیید این تخصیص</button>`}
        <a class="btn ghost" href="#/risk">پرسشنامه را دوباره پر کنید</a>
      </div>
    </div></div>`;
  const draw = () => {
    if (!locked) {
      const sh = $("#sh"), sm = $("#sm");
      cur.high = +sh.value;
      sm.max = rec.high + rec.medium - cur.high;
      cur.medium = Math.min(+sm.value, +sm.max);
      sm.value = cur.medium;
      cur.low = 100 - cur.high - cur.medium;
      $("#vh").textContent = fa(cur.high) + "٪"; $("#vm").textContent = fa(cur.medium) + "٪";
    }
    $("#split").innerHTML = splitBar(cur, true);
    $("#rows").innerHTML = strategies.map((s, i) => `<div class="srow ${RISK[i][2]}"><span class="bar"></span>
      <div><h3>${esc(s.name)}</h3><p>${esc(faDigits(s.assets))}: ${esc(faDigits(s.how))}</p></div><div class="pct num">${fa(cur[s.key])}٪</div></div>`).join("");
    const e = expectedFor(cur);
    $("#emean").innerHTML = `<span class="${tone(e.mean)}">${pct(e.mean)}</span>`;
    $("#eworst").innerHTML = `<span class="${tone(e.worst)}">${pct(e.worst)}</span>`;
  };
  if (!locked) {
    $("#sh").oninput = draw; $("#sm").oninput = draw;
    $("#ok").onclick = async () => {
      $("#ok").disabled = true;
      try {
        await api("/api/allocation", cur);
        toast("تخصیص ذخیره شد");
        go(S.me.subscription ? "#/dashboard" : "#/billing?next=dashboard");
      } catch (e) { $("#err").textContent = e.message; $("#ok").disabled = false; }
    };
  }
  draw();
}

// ------------------------------------------------------------------ billing
async function billingPage(main, params) {
  const b = await api("/api/billing");
  const sub = b.subscription;
  main.innerHTML = `<div class="wrap page">
    <div class="page-head"><h1>اشتراک</h1>${sub ? `<span class="pill run">فعال تا ${esc(day(sub.expires_at))}</span>` : `<span class="pill warn">اشتراک فعال ندارید</span>`}</div>
    ${params.get("paid") ? `<p class="notice" style="margin-bottom:20px">پرداخت انجام شد و اشتراک شما فعال است.</p>` : ""}
    ${params.get("failed") ? `<p class="notice bad" style="margin-bottom:20px">پرداخت انجام نشد. اگر مبلغی کم شده، طی ۷۲ ساعت به حساب شما برمی‌گردد.</p>` : ""}
    ${b.provider === "demo" ? `<p class="notice warn" style="margin-bottom:20px">درگاه در حالت آزمایشی است: با زدن دکمه، اشتراک بدون پرداخت واقعی فعال می‌شود.</p>` : ""}
    ${sub ? `<div class="panel" style="margin-bottom:20px"><h2>اشتراک فعلی: ${esc(sub.name)}</h2><p class="muted">${fa(sub.days_left)} روز باقی مانده است. خرید دوباره، زمان را به انتهای اشتراک فعلی اضافه می‌کند.</p>
      <a class="btn primary" href="#/dashboard">رفتن به داشبورد</a></div>` : ""}
    ${plansHtml(b.plans, true)}
    <ul class="features">${b.features.map((f) => `<li>${esc(f)}</li>`).join("")}</ul>
    <p class="err" id="err" role="alert"></p>
    ${b.payments.length ? `<div class="panel" style="margin-top:28px"><h2>پرداخت‌ها</h2><div class="scroll"><table class="t">
      <tr><th>تاریخ</th><th>پلن</th><th>مبلغ</th><th>وضعیت</th><th>کد پیگیری</th></tr>
      ${b.payments.map((x) => `<tr><td>${esc(when(x.created_at))}</td><td>${esc(x.plan)}</td><td class="num">${tmn(x.amount_tmn)}</td>
        <td>${{ paid: "موفق", pending: "در انتظار", failed: "ناموفق" }[x.status] || esc(x.status)}${x.provider === "demo" ? " (آزمایشی)" : ""}</td><td class="ltr">${esc(x.ref_id)}</td></tr>`).join("")}
    </table></div></div>` : ""}
  </div>`;
  $$("[data-plan]").forEach((btn) => {
    btn.onclick = async () => {
      btn.disabled = true; $("#err").textContent = "";
      try {
        const r = await api("/api/billing/checkout", { plan: btn.dataset.plan });
        if (r.redirect) { location.href = r.redirect; return; }
        await refreshMe();
        toast("اشتراک فعال شد");
        go(params.get("next") === "dashboard" || !sub ? "#/dashboard" : "#/billing");
      } catch (e) { $("#err").textContent = e.message; btn.disabled = false; }
    };
  });
}

// ------------------------------------------------------------------ dashboard
const STATE_FA = { holding: "در حال نگهداری", waiting: "منتظر شرط ورود", stopped: "حد ضرر فعال شد؛ به تومان برگشت", empty: "سهمی ندارد", cash: "نقد تومانی (در حالت آزمایشی)" };

async function dashboard(main) {
  if (S.me.user.role === "founder") return go("#/founder");
  let info = await api("/api/bot");
  if (!info.checks.profile) {
    main.innerHTML = `<div class="wrap page"><div class="panel empty"><h2>اول ریسک‌پذیری‌تان را مشخص کنید</h2>
      <p>با ${fa(S.meta.questions)} سؤال کوتاه، سهم هر استراتژی برای شما تعیین می‌شود.</p><a class="btn primary" href="#/risk">شروع پرسشنامه</a></div></div>`;
    return;
  }
  if (info.bot.status !== "running") return startPanel(main, info);
  main.innerHTML = `<div class="wrap page">
    <div class="page-head"><h1>ربات من</h1><div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
      <span class="pill run"><span class="dot on"></span>در حال معامله</span><span class="pill">حالت آزمایشی</span>
      <button class="btn danger small" id="stop">توقف ربات</button></div></div>
    <div class="kpi-row" id="kpis"></div>
    <p class="regime-line" id="reg"></p>
    <div class="panel" style="margin-top:16px"><div class="page-head" style="margin-bottom:8px"><h2 style="margin:0">ارزش سرمایه</h2>
      <div class="seg" role="group" aria-label="بازه‌ی نمودار">${[[24, "۲۴ ساعت"], [168, "۷ روز"], [9600, "همه"]].map(([h, t], j) => `<button data-h="${h}" aria-pressed="${j === 1}">${t}</button>`).join("")}</div></div>
      <div class="chart" id="chart"></div></div>
    <div class="panel"><h2>سه سبد شما</h2><div id="split"></div><div class="sleeves" id="sleeves" style="margin-top:18px"></div></div>
    <div class="grid2" style="margin-top:20px">
      <div class="panel"><h2>چه اتفاقی افتاد</h2><ul class="feed" id="events"></ul></div>
      <div class="panel"><h2>معاملات</h2><div class="scroll" id="trades"></div></div>
    </div></div>`;
  let hours = 168;
  const drawBot = () => {
    const b = info.bot, m = b.market;
    $("#kpis").innerHTML = `<div class="kpi big"><span>ارزش فعلی</span><b class="num">${money(b.equity)}</b></div>
      <div class="kpi"><span>سود / زیان</span><b class="num ${tone(b.pnl_tmn)}">${signed(b.pnl_tmn, 0)}</b><div class="small ${tone(b.pnl_pct)} num">${pct(b.pnl_pct)}</div></div>
      <div class="kpi"><span>سرمایه‌ی اولیه</span><b class="num">${fa(b.capital_tmn)}</b><div class="small muted">از ${esc(day(b.started_at))}</div></div>
      <div class="kpi"><span>کارمزد پرداختی</span><b class="num">${fa(b.fees_tmn)}</b><div class="small muted">تومان</div></div>`;
    $("#reg").innerHTML = regimeLine(m);
    const vals = { low: b.sleeves.low.value, medium: b.sleeves.medium.value, high: b.sleeves.high.value };
    const tot = vals.low + vals.medium + vals.high || 1;
    $("#split").innerHTML = splitBar({ low: vals.low / tot * 100, medium: vals.medium / tot * 100, high: vals.high / tot * 100 }, true);
    $("#sleeves").innerHTML = RISK.map(([k, , t, name], i) => {
      const s = b.sleeves[k], strat = S.meta.strategies[i];
      return `<div class="sleeve ${t}" style="--c:var(--${["low", "mid", "high"][i]})"><h3>${esc(strat.name)}</h3>
        <div class="val num">${money(s.value)}</div><div class="state">${esc(STATE_FA[s.state] || s.state)} · سهم ${fa(b.allocation[k])}٪</div>
        ${s.positions.length ? `<table class="t" style="margin-top:8px"><tr><th>دارایی</th><th>ارزش</th><th>بازده</th></tr>
          ${s.positions.map((p) => `<tr><td class="ltr">${esc(p.asset)}</td><td class="num">${fa(p.value)}</td><td class="num ${tone(p.pnl_pct)}">${pct(p.pnl_pct)}</td></tr>`).join("")}</table>`
        : s.cash > 0 ? `<p class="small muted" style="margin-top:6px">${fa(s.cash)} تومان نقد</p>` : ""}
        ${s.stopped ? `<p class="small loss">${esc(faDigits(s.stopped))}</p>` : ""}</div>`;
    }).join("");
  };
  const loadActivity = async () => {
    const a = await api("/api/bot/activity");
    $("#events").innerHTML = a.events.length ? a.events.map((e) => `<li><time>${esc(clock(e.ts))}</time><div><span class="k ${esc(e.kind)}"></span>${esc(faDigits(e.text))}</div></li>`).join("")
      : `<li><span></span><span class="muted">هنوز رویدادی ثبت نشده است.</span></li>`;
    $("#trades").innerHTML = a.trades.length ? `<table class="t"><tr><th>زمان</th><th>سبد</th><th>نوع</th><th>دارایی</th><th>مبلغ (تومان)</th></tr>
      ${a.trades.map((t) => `<tr><td>${esc(when(t.ts))}</td><td>${{ medium: "متوسط", high: "پرریسک", low: "کم‌ریسک" }[t.sleeve] || ""}</td>
        <td class="${t.side === "BUY" ? "gain" : "loss"}">${t.side === "BUY" ? "خرید" : "فروش"}</td><td class="ltr">${esc(t.asset)}</td><td class="num">${fa(t.notional_tmn)}</td></tr>`).join("")}</table>`
      : `<p class="muted">ربات هنوز معامله‌ای نکرده است. سبدها وقتی شرط ورود برقرار شود خرید می‌کنند.</p>`;
  };
  const loadChart = async () => {
    const h = await api(`/api/bot/history?hours=${hours}`);
    lineChart($("#chart"), h.rows.map((r) => [r[0], r[1]]), { base: info.bot.capital_tmn, label: "ارزش سرمایه‌ی ربات" });
  };
  $$(".seg button").forEach((btn) => {
    btn.onclick = () => { hours = +btn.dataset.h; $$(".seg button").forEach((x) => x.setAttribute("aria-pressed", String(x === btn))); loadChart(); };
  });
  $("#stop").onclick = async () => {
    if (!confirm("ربات متوقف شود؟ همه‌ی دارایی‌های سبدها به تومان فروخته می‌شوند.")) return;
    try { await api("/api/bot/stop", {}); toast("ربات متوقف شد"); route(); } catch (e) { toast(e.message); }
  };
  drawBot(); loadActivity(); loadChart();
  every(15000, async () => { info = await api("/api/bot"); if (info.bot.status !== "running") return route(); drawBot(); loadActivity(); });
  every(60000, loadChart);
}

function startPanel(main, info) {
  const b = info.bot, c = info.checks;
  const alloc = b.allocation;
  main.innerHTML = `<div class="wrap page">
    <div class="page-head"><h1>ربات من</h1><span class="pill">${b.started_at ? "متوقف" : "هنوز شروع نشده"}</span></div>
    <div class="grid2">
      <div class="panel"><h2>سرمایه و تخصیص</h2>
        <div class="field"><label for="cap">سرمایه‌ی ربات (تومان)</label><input class="input num ltr" id="cap" inputmode="numeric" value="${(b.capital_tmn || 50000000).toLocaleString("en-US")}"></div>
        ${splitBar(alloc, true)}<div id="leg"></div>
        <p class="small muted" style="margin-top:12px"><a href="#/result">تغییر تخصیص</a></p>
      </div>
      <div class="panel"><h2>قبل از شروع</h2>
        <ul class="checks">
          <li class="${c.profile ? "ok" : ""}">پروفایل ریسک ${c.profile ? "مشخص است" : `ندارید — <a href="#/risk">پرسشنامه</a>`}</li>
          <li class="${c.subscription ? "ok" : ""}">${c.subscription ? "اشتراک فعال است" : `اشتراک فعال ندارید — <a href="#/billing?next=dashboard">خرید اشتراک</a>`}</li>
          <li class="${c.market ? "ok" : ""}">${c.market ? "قیمت‌های لحظه‌ای بازار دریافت می‌شود" : "قیمت‌های بازار در حال دریافت است (ربات بعد از دریافت شروع به معامله می‌کند)"}</li>
        </ul>
        <p class="notice">حالت آزمایشی: ربات با پول مجازی و با همان قوانین ربات اصلی روی قیمت‌های لحظه‌ای والکس معامله می‌کند. وصل‌کردن حساب واقعی والکس در فاز بعد اضافه می‌شود.</p>
        <p class="err" id="err" role="alert"></p>
        <button class="btn primary" id="go" ${c.profile && c.subscription ? "" : "disabled"}>شروع ربات</button>
      </div>
    </div></div>`;
  const leg = () => { const n = parseNum($("#cap").value); $("#leg").innerHTML = legend(alloc, { low: n * alloc.low / 100, medium: n * alloc.medium / 100, high: n * alloc.high / 100 }); };
  $("#cap").oninput = () => { const n = parseNum($("#cap").value); $("#cap").value = n ? n.toLocaleString("en-US") : ""; leg(); };
  leg();
  $("#go").onclick = async () => {
    $("#go").disabled = true; $("#err").textContent = "";
    try { await api("/api/bot/start", { capital_tmn: parseNum($("#cap").value) }); await refreshMe(); toast("ربات شروع به کار کرد"); route(); }
    catch (e) { $("#err").textContent = e.message; $("#go").disabled = false; }
  };
}

// ------------------------------------------------------------------ founder
const FILTERS = [["all", "همه"], ["ai", "تصمیم‌های AI"], ["trade", "معاملات"], ["risk", "ریسک"], ["guard", "محافظ‌ها"], ["error", "خطاها"]];
const SLEEVE_FA = { cash: "تومان", low: "بازارساز", medium: "سبد ریال", high: "سبد بتا", other: "تتر" };

async function founder(main) {
  main.innerHTML = `<div class="wrap page">
    <div class="page-head"><div><h1>اتاق کنترل</h1><p class="muted" style="margin:0">حساب واقعی شما در والکس و الگوریتمی که روی لیارا اجرا می‌شود، لحظه‌به‌لحظه.</p></div>
      <span class="regime-line" style="margin:0" id="upd"></span></div>
    <div id="warn"></div>
    <div class="grid2"><section class="panel" id="wallex"></section><section class="panel" id="algo"></section></div>
    <div class="panel" style="margin-top:20px"><div class="page-head" style="margin-bottom:8px"><h2 style="margin:0">نمودار ارزش</h2>
      <div class="seg" role="group" aria-label="کدام نمودار"><button data-c="algo" aria-pressed="true">الگوریتم</button><button data-c="wallex" aria-pressed="false">حساب واقعی والکس</button></div></div>
      <div class="chart" id="chart"></div></div>
    <div class="grid2" style="margin-top:20px"><section class="panel" id="ai"></section><section class="panel" id="regime"></section></div>
    <div class="panel" style="margin-top:20px"><h2>رویدادهای الگوریتم</h2><div class="chips" id="chips"></div><ul class="feed" id="feed"></ul>
      <details style="margin-top:14px"><summary>خروجی خام ربات (کنسول)</summary><pre class="console" id="console"></pre></details></div>
    <div class="panel" style="margin-top:20px"><h2>پلتفرم</h2><div class="kpi-row" id="pk"></div>
      <div class="grid2" style="margin-top:18px"><div><h3>پروفایل ریسک کاربران</h3><div class="bars" id="dist"></div></div><div id="cfg"></div></div>
      <h3 style="margin-top:22px">کاربران</h3><div class="scroll" id="users"></div></div>
  </div>`;
  let o = null, chartKind = "algo", filter = "all";
  $("#chips").innerHTML = FILTERS.map(([k, t]) => `<button data-f="${k}" aria-pressed="${k === filter}">${t}</button>`).join("");
  $$("#chips button").forEach((b) => { b.onclick = () => { filter = b.dataset.f; $$("#chips button").forEach((x) => x.setAttribute("aria-pressed", String(x === b))); feed(); }; });
  $$(".seg button").forEach((b) => { b.onclick = () => { chartKind = b.dataset.c; $$(".seg button").forEach((x) => x.setAttribute("aria-pressed", String(x === b))); chart(); }; });

  const chart = () => {
    if (chartKind === "algo") lineChart($("#chart"), o.bot.history, { base: o.bot.initial, label: "ارزش الگوریتم", empty: "داده‌ی تاریخچه‌ی الگوریتم هنوز نرسیده است." });
    else lineChart($("#chart"), (o.wallex_history || []).map((r) => [r[0], r[1]]), { base: o.wallex.initial_tmn, color: "var(--low)", label: "ارزش حساب واقعی", empty: "تاریخچه‌ی حساب واقعی بعد از اتصال کلید والکس، دقیقه‌به‌دقیقه ثبت می‌شود." });
  };
  const feed = () => {
    const ev = (o.bot.events || []).filter((e) => filter === "all" ? e.kind !== "guard" : e.kind === filter).slice(0, 80);
    $("#feed").innerHTML = ev.length ? ev.map((e) => `<li><time>${esc(clock(e.ts))}</time><div><span class="k ${esc(e.kind)}"></span>${esc(faDigits(e.text))}
      ${e.detail ? `<details><summary>جزئیات</summary><div class="detail">${esc(e.detail)}</div></details>` : ""}</div></li>`).join("")
      : `<li><span></span><span class="muted">رویدادی در این دسته نیست.</span></li>`;
  };
  const draw = () => {
    const w = o.wallex, bt = o.bot, pf = o.platform;
    const warns = [];
    if (!o.config.wallex_key) warns.push("حساب واقعی والکس وصل نیست: متغیر <b class=\"ltr\">WALLEX_API_KEY</b> را در تنظیمات برنامه در لیارا وارد کنید.");
    if (!o.config.bot_status_url && !o.config.bot_logs_dir && !o.config.github) warns.push("منبع داده‌ی ربات تنظیم نشده است: <b class=\"ltr\">BOT_STATUS_URL</b> (آدرس برنامه‌ی ربات در لیارا) را وارد کنید.");
    if (o.market.source === "replay") warns.push("قیمت‌ها از داده‌ی بازپخش آفلاین می‌آیند (MARKET_SOURCE=replay)؛ روی سرور آن را wallex بگذارید.");
    $("#warn").innerHTML = warns.map((x) => `<p class="notice warn" style="margin-bottom:12px">${x}</p>`).join("");
    $("#upd").innerHTML = `<span class="dot ${bt.ok ? "on" : "err"}"></span> به‌روزرسانی ${esc(clock(Date.now() / 1000))}`;

    $("#wallex").innerHTML = !w.configured ? `<h2>حساب واقعی والکس</h2><p class="muted">کلید API والکس تنظیم نشده است.</p>`
      : !w.equity_tmn && !w.ok ? `<h2>حساب واقعی والکس</h2><p class="notice bad">اتصال به والکس برقرار نشد: <span class="ltr">${esc(w.error || "")}</span></p>`
        : `<h2>حساب واقعی والکس ${w.ok ? "" : `<span class="pill bad">قطع: آخرین داده</span>`}</h2>
      <div class="muted small">ارزش کل حساب (هر دارایی به بهترین قیمت خرید)</div>
      <div class="hero-num">${money(w.equity_tmn)}</div>
      <div class="sub-num ${tone(w.pnl_tmn)}">${signed(w.pnl_tmn, 0)} تومان (${pct(w.pnl_pct, 3)})</div>
      <div class="small muted">نسبت به سرمایه‌ی اولیه‌ی ${tmn(w.initial_tmn)}</div>
      <div style="margin-top:16px">${splitBar({ low: (w.by_sleeve.low + w.by_sleeve.cash + w.by_sleeve.other), medium: w.by_sleeve.medium, high: w.by_sleeve.high })}</div>
      <dl class="dl" style="margin-top:12px"><dt>تومان نقد</dt><dd class="num">${tmn(w.by_sleeve.cash)}</dd>
        <dt>بازارساز</dt><dd class="num">${tmn(w.by_sleeve.low)}</dd><dt>سبد ریال</dt><dd class="num">${tmn(w.by_sleeve.medium)}</dd>
        <dt>سبد بتا</dt><dd class="num">${tmn(w.by_sleeve.high)}</dd><dt>سفارش‌های باز</dt><dd class="num">${fa(w.open_orders)}</dd></dl>
      ${(w.holdings || []).filter((h) => h.asset !== "TMN").length ? `<table class="t" style="margin-top:12px"><tr><th>دارایی</th><th>مقدار</th><th>ارزش (تومان)</th><th>سبد</th></tr>
        ${w.holdings.filter((h) => h.asset !== "TMN").slice(0, 10).map((h) => `<tr><td class="ltr">${esc(h.asset)}</td><td class="num ltr">${esc(+h.qty.toPrecision(6))}</td><td class="num">${fa(h.value_tmn)}</td><td>${SLEEVE_FA[h.sleeve] || ""}</td></tr>`).join("")}</table>` : ""}`;

    const mode = bt.mode === "live" ? `<span class="pill live">واقعی (live)</span>` : bt.mode === "off" ? `<span class="pill bad">خاموش</span>` : `<span class="pill warn">تست سایه (shadow)</span>`;
    const fresh = bt.age_s == null ? "err" : bt.age_s < 180 ? "on" : bt.age_s < 900 ? "off" : "err";
    $("#algo").innerHTML = !bt.configured ? `<h2>الگوریتم روی لیارا</h2><p class="muted">منبع داده‌ی ربات تنظیم نشده است.</p>`
      : !bt.equity && !bt.ok ? `<h2>الگوریتم روی لیارا</h2><p class="notice bad">داده‌ای از ربات نرسید: <span class="ltr">${esc((bt.errors || []).join(" | "))}</span></p>`
        : `<h2 style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">الگوریتم روی لیارا ${mode}</h2>
      <p class="regime-line" style="margin:0 0 8px"><span class="dot ${fresh}"></span> آخرین داده ${esc(ago(bt.age_s))} ${bt.stale ? "(ارتباط قطع است)" : ""}</p>
      <div class="muted small">${bt.mode === "live" ? "ارزش حساب طبق ربات" : "ارزش پرتفوی آزمایشی (پول مجازی، دفترهای واقعی)"}</div>
      <div class="hero-num">${money(bt.equity)}</div>
      <div class="sub-num ${tone(bt.pnl_tmn)}">${signed(bt.pnl_tmn, 0)} تومان (${pct(bt.pnl_pct, 3)})</div>
      <dl class="dl" style="margin-top:14px"><dt>افت فعلی از اوج</dt><dd class="num">${pct(bt.drawdown_pct == null ? null : -bt.drawdown_pct)}</dd>
        <dt>بیشترین افت</dt><dd class="num">${pct(bt.max_drawdown_pct == null ? null : -bt.max_drawdown_pct)}</dd>
        <dt>بازارساز: معاملات</dt><dd class="num">${fa(bt.mm.fills)} پرشدن، سود محقق ${signed(bt.mm.pnl_tmn, 0)}</dd>
        <dt>موجودی بازارساز</dt><dd class="num">${tmn(bt.mm.inventory_tmn)}</dd>
        ${bt.sleeves ? ["rial", "beta"].filter((k) => bt.sleeves[k]).map((k) => `<dt>${k === "rial" ? "سبد ریال" : "سبد بتا"}</dt>
          <dd class="num">${tmn(bt.sleeves[k].value)} · <span class="${tone(bt.sleeves[k].ret_pct)}">${pct(bt.sleeves[k].ret_pct)}</span> · حضور ${fa(bt.sleeves[k].scale, 1)}</dd>`).join("") : ""}
      </dl><p class="small muted" style="margin-top:8px">منبع: ${esc((bt.sources || []).join("، "))}</p>`;

    const p = bt.policy;
    $("#ai").innerHTML = `<h2>آخرین تصمیم AI</h2>` + (!p ? `<p class="muted">هنوز تصمیمی دریافت نشده است.</p>`
      : `<p class="small muted">${esc(faDigits(bt.policy_time || ""))} · منبع: <span class="ltr">${esc(p.source)}</span></p>
      <dl class="dl"><dt>بازارها و پهنا</dt><dd class="ltr" style="text-align:right">${Object.entries(p.markets || {}).map(([k, v]) => `${esc(k)} ${esc(v)}%`).join(" · ") || "—"}</dd>
        <dt>حضور سبد ریال</dt><dd class="num">${fa((p.sleeves || {}).rial, 2)}</dd><dt>حضور سبد بتا</dt><dd class="num">${fa((p.sleeves || {}).beta, 2)}</dd>
        <dt>کوین‌های بتا</dt><dd class="ltr" style="text-align:right">${esc((p.beta_assets || []).join(", "))}</dd>
        <dt>توقف کامل</dt><dd>${p.pause ? "بله" : "خیر"}</dd></dl>
      ${p.reasoning ? `<blockquote class="ai-quote">${esc(p.reasoning)}</blockquote>` : ""}`);
    const r = bt.regime;
    $("#regime").innerHTML = `<h2>رژیم بازار و محافظ‌ها</h2>` + (r ? `<dl class="dl"><dt>تتر/تومان</dt><dd class="num">${fa(r.usdt_tmn)}</dd>
      <dt>تغییر ۶ ساعته</dt><dd class="num ${tone(r.ch6_pct)}">${pct(r.ch6_pct)}</dd><dt>تغییر ۲۴ ساعته</dt><dd class="num ${tone(r.ch24_pct)}">${pct(r.ch24_pct)}</dd>
      <dt>تغییر ۴۸ ساعته</dt><dd class="num ${tone(r.ch48_pct)}">${pct(r.ch48_pct)}</dd><dt>سقف حضور سبدها</dt><dd class="num">${fa(r.cap, 1)}</dd>
      <dt>زمان</dt><dd>${esc(faDigits(r.time || ""))}</dd></dl>` : `<p class="muted">هنوز رژیمی ثبت نشده است.</p>`)
      + `<p style="margin-top:14px">محافظ‌های خرید در ساعت گذشته <b class="num">${fa(bt.guards_last_hour)}</b> بار جلوی خرید بازارساز را گرفتند (افت سریع قیمت، لغزیدن دفتر، دفتر یخ‌زده).</p>`;
    feed();
    $("#console").textContent = (bt.console || []).join("\n") || "خروجی‌ای نرسیده است (فقط با BOT_STATUS_URL یا BOT_LOGS_DIR).";

    $("#pk").innerHTML = `<div class="kpi"><span>کاربران</span><b class="num">${fa(pf.users)}</b><div class="small muted">${fa(pf.signups_7d)} در ۷ روز اخیر</div></div>
      <div class="kpi"><span>اشتراک فعال</span><b class="num">${fa(pf.active_subscriptions)}</b><div class="small muted">${pf.demo_payments ? fa(pf.demo_payments) + " پرداخت آزمایشی" : "&nbsp;"}</div></div>
      <div class="kpi"><span>ربات‌های فعال</span><b class="num">${fa(pf.running_bots)}</b><div class="small muted">حالت آزمایشی</div></div>
      <div class="kpi"><span>سرمایه‌ی آزمایشی کاربران</span><b class="num">${fa(pf.paper_aum_tmn / 1e6, 1)}م</b><div class="small muted">درآمد واقعی: ${tmn(pf.revenue_tmn)}</div></div>`;
    const maxc = Math.max(1, ...Object.values(pf.profiles).map((x) => x.count));
    $("#dist").innerHTML = Object.values(pf.profiles).map((x) => `<div class="row"><span>${esc(x.name)}</span><i style="width:${x.count / maxc * 100}%"></i><b class="num">${fa(x.count)}</b></div>`).join("");
    $("#cfg").innerHTML = `<h3>اتصال‌ها</h3><ul class="checks">
      <li class="${o.config.wallex_key ? "ok" : ""}">کلید API والکس (فقط خواندن)</li>
      <li class="${o.config.bot_status_url ? "ok" : ""}">صفحه‌ی وضعیت ربات در لیارا</li>
      <li class="${o.config.github ? "ok" : ""}">تاریخچه از شاخه‌ی runtime-logs در GitHub</li>
      <li class="${o.market.fresh ? "ok" : ""}">قیمت‌های بازار (${o.market.source === "replay" ? "بازپخش" : "والکس"})</li>
      <li class="${o.config.payment_provider === "zarinpal" ? "ok" : ""}">درگاه پرداخت: ${o.config.payment_provider === "zarinpal" ? "زرین‌پال" : "آزمایشی"}</li></ul>`;
  };
  const users = async () => {
    const { users: us } = await api("/api/founder/users");
    $("#users").innerHTML = `<table class="t"><tr><th>نام</th><th>ایمیل</th><th>پروفایل</th><th>اشتراک</th><th>ربات</th><th>تخصیص</th><th>ارزش</th></tr>
      ${us.map((u) => `<tr><td>${esc(u.name)}${u.role === "founder" ? ' <span class="badge">بنیان‌گذار</span>' : ""}</td><td class="ltr">${esc(u.email)}</td>
        <td>${u.profile ? `${esc(u.profile)} <span class="muted num">(${fa(u.score)})</span>` : "—"}</td><td>${u.subscription ? esc(u.subscription.name) : "—"}</td>
        <td>${{ running: "فعال", stopped: "متوقف" }[u.bot_status] || "—"}</td>
        <td style="min-width:110px">${u.allocation && u.allocation[0] + u.allocation[1] + u.allocation[2] === 100 ? splitBar({ low: u.allocation[0], medium: u.allocation[1], high: u.allocation[2] }) : "—"}</td>
        <td class="num">${u.equity_tmn ? fa(u.equity_tmn) : "—"}</td></tr>`).join("")}</table>`;
  };
  const load = async () => { o = await api("/api/founder/overview"); draw(); chart(); };
  await load(); users();
  every(10000, load);
  every(60000, users);
}

// ------------------------------------------------------------------ boot
(async function boot() {
  try {
    [S.me, S.meta] = await Promise.all([api("/api/me"), api("/api/meta")]);
  } catch (e) {
    $("#view").innerHTML = `<div class="wrap page"><div class="panel empty"><h2>سرور در دسترس نیست</h2><p>${esc(e.message)}</p></div></div>`;
    return;
  }
  if (S.meta.market.source === "replay") {
    const b = document.createElement("div");
    b.className = "mode-banner";
    b.textContent = "نسخه‌ی نمایشی: قیمت‌ها از داده‌ی ذخیره‌شده‌ی والکس بازپخش می‌شوند، نه بازار زنده.";
    document.body.insertBefore(b, $("#view"));
  }
  window.addEventListener("hashchange", route);
  route();
})();
