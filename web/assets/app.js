(() => {
  "use strict";

  const MS_PER_MONTH = 850;
  const HOLD_MS = 3500;
  const NS = "http://www.w3.org/2000/svg";
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const $ = (id) => document.getElementById(id);
  const nf = (d = 0) => new Intl.NumberFormat("vi-VN", { minimumFractionDigits: d, maximumFractionDigits: d });
  const fmtInt = (v) => nf(0).format(Math.round(v));
  const fmtMoney = (v) => {
    if (Math.abs(v) >= 1e6) return "R$ " + nf(2).format(v / 1e6) + " tr";
    if (Math.abs(v) >= 1e3) return "R$ " + nf(1).format(v / 1e3) + " N";
    return "R$ " + nf(2).format(v);
  };
  const monthVi = (m) => { const [y, mm] = m.split("-"); return `Tháng ${Number(mm)}/${y}`; };
  const monthShort = (m) => { const [y, mm] = m.split("-"); return `${mm}/${y.slice(2)}`; };
  const el = (tag, attrs = {}, parent) => {
    const n = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
    if (parent) parent.appendChild(n);
    return n;
  };
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  fetch("data/kpi.json", { cache: "no-cache" })
    .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(init)
    .catch((e) => { $("ticker").textContent = "Không tải được data/kpi.json (" + e.message + "). Chạy scripts/export_landing_kpi.py rồi tải lại."; });

  function init(d) {
    fillStatic(d);
    fillInsights(d);
    startReplay(d.monthly);
  }

  /* ---------- Số liệu tĩnh: hero, badge, feature ---------- */
  function fillStatic(d) {
    const q = d.quality, p = d.performance, load = d.load || {}, inv = d.inventory;
    const facts = $("hero-facts");
    facts.querySelector('[data-k="rows"]').textContent = fmtInt(load.rows || 0);
    facts.querySelector('[data-k="anchors"]').textContent = `${q.anchors_passed}/${q.anchors_total}`;
    facts.querySelector('[data-k="server_ms"]').textContent = nf(2).format(p.query_server_median_ms) + " ms";
    $("b-anchors").textContent = `${q.anchors_passed}/${q.anchors_total}`;
    $("b-tables").textContent = `${q.tables_matched}/${q.tables_total}`;
    $("f-load").textContent = `${load.tables} bảng · ${fmtInt(load.rows)} dòng · ${nf(1).format(load.parquet_bytes / 1048576)} MB Parquet`;
    $("f-inv").textContent = `${inv.tables} bảng · ${inv.views} view trên Neon`;
    $("f-hints").textContent = `${d.decision_hints.length} luật · ${d.watchlist.red}/${d.watchlist.sellers} seller mức ĐỎ`;
    const s = p.scale, first = s[0], last = s[s.length - 1];
    if (first && last) {
      $("f-scale").textContent = `×${last.factor}: ${nf(0).format(first.raw_month_category_ms)} → ${nf(0).format(last.raw_month_category_ms)} ms thô · ${nf(1).format(last.preaggregated_view_ms)} ms view`;
    }
    const gen = new Date(d.generated_at).toLocaleString("vi-VN", { dateStyle: "medium", timeStyle: "short" });
    $("gen-at").textContent = gen;
    $("foot-gen").textContent = gen;
    const m = d.monthly;
    $("range").textContent = `${m[0].month} → ${m[m.length - 1].month}`;
  }

  /* ---------- Insight ---------- */
  function fillInsights(d) {
    const cats = d.top_categories, maxC = cats[0].revenue;
    $("ins-cat").innerHTML = cats.map((c) =>
      `<li><span class="lbl">${esc(c.category.replace(/_/g, " "))}</span><span class="val">${fmtMoney(c.revenue)} · ${nf(1).format(c.revenue_share_pct)}%</span>
       <span class="trk"><span class="fill" data-w="${(100 * c.revenue / maxC).toFixed(1)}"></span></span></li>`).join("");

    const st = d.top_states, maxS = st[0].revenue;
    $("ins-state").innerHTML = st.map((s) => {
      const warn = s.late_delivery_pct > 10 ? " warn" : "";
      return `<li><span class="lbl">${esc(s.customer_state)} · ${esc(s.state_name)}</span>
        <span class="val">${nf(1).format(s.revenue_share_pct)}% DT · trễ ${nf(1).format(s.late_delivery_pct)}% · ★ ${nf(2).format(s.avg_review_score)}</span>
        <span class="trk"><span class="fill${warn}" data-w="${(100 * s.revenue / maxS).toFixed(1)}"></span></span></li>`;
    }).join("");

    const colors = ["#34d399", "#22d3ee", "#f472b6", "#818cf8", "#a78bfa", "#475569"];
    const seg = d.rfm_segments;
    $("ins-rfm").innerHTML = seg.map((s, i) =>
      `<span style="width:${Math.max(s.pct_customers, 0.6)}%;background:${colors[i % colors.length]}" title="${esc(s.rfm_segment)}"></span>`).join("");
    $("ins-rfm-l").innerHTML = seg.map((s, i) =>
      `<li><i style="background:${colors[i % colors.length]}"></i><div><b>${esc(s.rfm_segment)}</b> · ${fmtInt(s.customers)} (${nf(2).format(s.pct_customers)}%)<small>${esc(s.crm_action)}</small></div></li>`).join("");

    const hints = d.decision_hints.filter((h) => h.severity === "CAO").concat(d.decision_hints.filter((h) => h.severity !== "CAO")).slice(0, 4);
    $("ins-hints").innerHTML = hints.map((h) =>
      `<li><span class="sev ${h.severity === "CAO" ? "cao" : "tb"}">${esc(h.severity)}</span><b>${esc(h.topic)}:</b> ${esc(h.signal)}<small>→ ${esc(h.action)}</small></li>`).join("");

    const fills = document.querySelectorAll(".bars .fill");
    const show = () => fills.forEach((f) => { f.style.width = f.dataset.w + "%"; });
    if ("IntersectionObserver" in window && !reduceMotion) {
      const io = new IntersectionObserver((es) => { if (es.some((e) => e.isIntersecting)) { show(); io.disconnect(); } }, { threshold: 0.2 });
      io.observe($("insight"));
    } else show();
  }

  /* ---------- Live replay chart ---------- */
  function startReplay(months) {
    const svg = $("chart"), wrap = svg.parentElement, tip = $("chart-tip"), panel = $("live");
    const N = months.length;
    const maxRev = Math.max(...months.map((m) => m.revenue)) * 1.12;
    const maxOrd = Math.max(...months.map((m) => m.orders)) * 1.12;
    const cumRev = [], cumOrd = [];
    months.reduce((a, m, i) => (cumRev[i] = a + m.revenue), 0);
    months.reduce((a, m, i) => (cumOrd[i] = a + m.orders), 0);

    let W = 0, H = 0, pad, bw, bars = [], line, area, cursor, head, hits = [];
    let progress = reduceMotion ? N : 0, playing = !reduceMotion, last = 0, holdUntil = 0, lastShown = -1;

    const x = (i) => pad.l + (i + 0.5) * ((W - pad.l - pad.r) / N);
    const yRev = (v) => H - pad.b - (v / maxRev) * (H - pad.t - pad.b);
    const yOrd = (v) => H - pad.b - (v / maxOrd) * (H - pad.t - pad.b);

    function build() {
      W = Math.max(wrap.clientWidth, 280);
      H = wrap.clientHeight;
      const narrow = W < 460;
      pad = { l: narrow ? 34 : 44, r: narrow ? 30 : 40, t: 10, b: 22 };
      svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
      svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
      svg.innerHTML = "";
      const defs = el("defs", {}, svg);
      const grad = (id, c1, c2, o2) => {
        const g = el("linearGradient", { id, x1: 0, y1: 0, x2: 0, y2: 1 }, defs);
        el("stop", { offset: 0, "stop-color": c1 }, g);
        el("stop", { offset: 1, "stop-color": c2, "stop-opacity": o2 }, g);
      };
      grad("gBar", "#34d399", "#34d399", 0.15);
      grad("gBf", "#fbbf24", "#fbbf24", 0.2);
      grad("gArea", "#818cf8", "#818cf8", 0);

      for (let k = 0; k <= 4; k++) {
        const v = (maxRev / 1.12) * (k / 4) * 1.0;
        const yy = yRev(v);
        el("line", { class: "grid-l", x1: pad.l, x2: W - pad.r, y1: yy, y2: yy }, svg);
        el("text", { class: "ax", x: pad.l - 6, y: yy + 3, "text-anchor": "end" }, svg).textContent = nf(1).format(v / 1e6) + "tr";
        const o = (maxOrd / 1.12) * (k / 4);
        el("text", { class: "ax", x: W - pad.r + 6, y: yOrd(o) + 3 }, svg).textContent = o >= 1000 ? nf(1).format(o / 1000) + "N" : "0";
      }
      const step = narrow ? 4 : 3;
      months.forEach((m, i) => {
        if ((N - 1 - i) % step === 0) el("text", { class: "ax", x: x(i), y: H - 6, "text-anchor": "middle" }, svg).textContent = monthShort(m.month);
      });

      bw = ((W - pad.l - pad.r) / N) * 0.62;
      bars = months.map((m) => el("rect", { class: "bar" + (m.is_black_friday_month ? " bf" : ""), x: 0, y: H - pad.b, width: bw, height: 0, rx: 3 }, svg));
      area = el("path", { class: "area" }, svg);
      line = el("path", { class: "line" }, svg);
      cursor = el("line", { class: "cursor", y1: pad.t, y2: H - pad.b }, svg);
      head = el("circle", { class: "head", r: 4.5 }, svg);
      const cw = (W - pad.l - pad.r) / N;
      hits = months.map((m, i) => {
        const r = el("rect", { class: "hit", x: pad.l + i * cw, y: pad.t, width: cw, height: H - pad.t - pad.b }, svg);
        r.addEventListener("pointerenter", () => showTip(i));
        r.addEventListener("pointerleave", () => { tip.hidden = true; });
        return r;
      });
      lastShown = -1;
      draw();
    }

    function showTip(i) {
      if (i > progress - 0.01) return;
      const m = months[i];
      tip.innerHTML = `<b>${monthVi(m.month)}</b>${m.is_black_friday_month ? " · Black Friday" : ""}<br>Doanh thu ${fmtMoney(m.revenue)} · ${fmtInt(m.orders)} đơn<br>Trễ ${nf(2).format(m.late_delivery_pct)}% · ★ ${nf(2).format(m.avg_review_score)}`;
      tip.style.left = `${(x(i) / W) * 100}%`;
      tip.style.top = `${(yRev(m.revenue) / H) * 100}%`;
      tip.hidden = false;
    }

    function draw() {
      const p = Math.min(progress, N);
      const full = Math.floor(p), frac = p - full;
      bars.forEach((b, i) => {
        const k = i < full ? 1 : i === full ? easeOut(frac) : 0;
        const h = (yRev(0) - yRev(months[i].revenue)) * k;
        b.setAttribute("x", x(i) - bw / 2);
        b.setAttribute("y", yRev(0) - h);
        b.setAttribute("height", Math.max(h, 0));
      });
      const pts = [];
      for (let i = 0; i < Math.min(full + 1, N); i++) pts.push([x(i), yOrd(months[i].orders)]);
      if (full < N - 1 && full >= 0 && frac > 0) {
        const a = months[full].orders, b = months[full + 1].orders;
        pts.push([x(full) + (x(full + 1) - x(full)) * frac, yOrd(a + (b - a) * frac)]);
      }
      const dPath = pts.map((q, i) => (i ? "L" : "M") + q[0].toFixed(1) + "," + q[1].toFixed(1)).join("");
      line.setAttribute("d", dPath);
      area.setAttribute("d", pts.length ? dPath + `L${pts[pts.length - 1][0].toFixed(1)},${yOrd(0)}L${pts[0][0].toFixed(1)},${yOrd(0)}Z` : "");
      const hp = pts[pts.length - 1] || [x(0), yOrd(0)];
      cursor.setAttribute("x1", hp[0]); cursor.setAttribute("x2", hp[0]);
      head.setAttribute("cx", hp[0]); head.setAttribute("cy", hp[1]);
      updateKpis(Math.min(full, N - 1), frac, p >= N);
    }

    function updateKpis(i, frac, done) {
      const lerp = (arr) => (done || i >= N - 1 ? arr[N - 1] : (i > 0 ? arr[i - 1] : 0) + (arr[i] - (i > 0 ? arr[i - 1] : 0)) * easeOut(frac));
      $("k-rev").textContent = fmtMoney(lerp(cumRev));
      $("k-ord").textContent = fmtInt(lerp(cumOrd));
      if (i === lastShown) return;
      lastShown = i;
      const m = months[i], prev = months[i - 1];
      $("k-aov").textContent = "R$ " + nf(2).format(m.avg_order_value);
      $("k-late").textContent = nf(2).format(m.late_delivery_pct) + "%";
      $("k-rv").textContent = "★ " + nf(2).format(m.avg_review_score);
      setAdded("k-rev-d", "+" + fmtMoney(m.revenue) + " trong tháng");
      setAdded("k-ord-d", "+" + fmtInt(m.orders) + " đơn trong tháng");
      setDelta("k-aov-d", prev ? m.avg_order_value - prev.avg_order_value : null, " R$", false);
      setDelta("k-late-d", prev ? m.late_delivery_pct - prev.late_delivery_pct : null, " điểm %", true);
      setDelta("k-rv-d", prev ? m.avg_review_score - prev.avg_review_score : null, "", false);

      const mom = m.revenue_mom_pct;
      let t = `<b>${monthVi(m.month)}</b> · doanh thu <b>${fmtMoney(m.revenue)}</b>`;
      if (mom != null) t += ` <span class="${mom >= 0 ? "up" : "down"}">(${mom >= 0 ? "+" : ""}${nf(2).format(mom)}% MoM)</span>`;
      t += ` · ${fmtInt(m.orders)} đơn`;
      if (m.is_black_friday_month) t += ` · <span class="bf">Black Friday</span>`;
      if (m.late_delivery_pct > 15) t += ` · <span class="down">giao trễ ${nf(2).format(m.late_delivery_pct)}% vượt ngưỡng 15%</span>`;
      $("ticker").innerHTML = t;
    }

    function setAdded(id, text) {
      const n = $(id);
      n.textContent = text;
      n.className = "kpi-d up";
    }

    function setDelta(id, v, unit, lowerIsBetter) {
      const n = $(id);
      if (v == null || !isFinite(v)) { n.textContent = "tháng đầu kỳ"; n.className = "kpi-d flat"; return; }
      const good = lowerIsBetter ? v < 0 : v > 0;
      n.textContent = (v > 0 ? "▲ +" : v < 0 ? "▼ " : "") + nf(2).format(v) + unit;
      n.className = "kpi-d " + (Math.abs(v) < 0.005 ? "flat" : good ? "up" : "down");
    }

    function easeOut(t) { return 1 - Math.pow(1 - t, 3); }

    function frame(ts) {
      if (!last) last = ts;
      const dt = Math.min(ts - last, 100);
      last = ts;
      if (playing) {
        if (progress < N) {
          progress = Math.min(N, progress + dt / MS_PER_MONTH);
          if (progress >= N) holdUntil = ts + HOLD_MS;
          draw();
        } else if (ts > holdUntil) {
          progress = 0; lastShown = -1; draw();
        }
      }
      requestAnimationFrame(frame);
    }

    function setPlaying(v) {
      playing = v;
      panel.classList.toggle("paused", !v);
      $("btn-play").setAttribute("aria-label", v ? "Tạm dừng" : "Phát tiếp");
    }

    $("btn-play").addEventListener("click", () => {
      if (!playing && progress >= N) { progress = 0; lastShown = -1; }
      setPlaying(!playing);
    });
    $("btn-replay").addEventListener("click", () => { progress = 0; lastShown = -1; holdUntil = 0; setPlaying(true); draw(); });

    let rz;
    window.addEventListener("resize", () => { clearTimeout(rz); rz = setTimeout(build, 120); });
    build();
    setPlaying(playing);
    requestAnimationFrame(frame);
  }
})();
