// Live dashboard demo (public CSV polling)

const CONFIG = {
    pollIntervalMs: 15000,
    profilesCsvUrl: "https://docs.google.com/spreadsheets/d/e/2PACX-1vTKKALF4TyTPNlHmAEBMGNL8SG7HW9a-4aMHo5DTVeYttUI_YspNAsffRFw6wZW7w7D9XAZctcYuZz5/pub?gid=143642608&single=true&output=csv",
};

const el = (id) => document.getElementById(id);

let _viewMode = "cards"; // 'cards' | 'table'
let _page = 1;
const PAGE_SIZE = 6;

function setSyncState(state, text) {
    const dot = el("syncDot");
    const label = el("syncText");
    if (!dot || !label) return;

    dot.classList.remove("is-good", "is-bad", "is-warn");
    if (state === "good") dot.classList.add("is-good");
    if (state === "bad") dot.classList.add("is-bad");
    if (state === "warn") dot.classList.add("is-warn");
    label.textContent = text;
}

function nowTime() {
    const d = new Date();
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

// Robust-enough CSV parsing for Google Sheets export (quoted fields, commas, newlines)
function parseCsv(text) {
    const rows = [];
    let row = [];
    let field = "";
    let inQuotes = false;

    for (let i = 0; i < text.length; i++) {
        const c = text[i];
        const n = text[i + 1];

        if (inQuotes) {
            if (c === '"' && n === '"') {
                field += '"';
                i++;
                continue;
            }
            if (c === '"') {
                inQuotes = false;
                continue;
            }
            field += c;
            continue;
        }

        if (c === '"') {
            inQuotes = true;
            continue;
        }

        if (c === ',') {
            row.push(field);
            field = "";
            continue;
        }

        if (c === '\n') {
            row.push(field);
            field = "";
            // Trim possible CR
            if (row.length === 1 && row[0] === "") {
                row = [];
                continue;
            }
            rows.push(row);
            row = [];
            continue;
        }

        if (c === '\r') {
            continue;
        }

        field += c;
    }

    // last field
    if (field.length > 0 || row.length > 0) {
        row.push(field);
        rows.push(row);
    }

    return rows;
}

function normalizeHeader(h) {
    return String(h || "")
        .replace(/\s+/g, " ")
        .trim()
        .toUpperCase();
}

function safeInt(v) {
    const s = String(v ?? "").replace(/[^0-9-]/g, "");
    const n = parseInt(s, 10);
    return Number.isFinite(n) ? n : 0;
}

function statusBadge(statusRaw) {
    const status = String(statusRaw || "").trim().toUpperCase();
    let cls = "info";
    if (status === "VERIFIED") cls = "good";
    else if (status === "UNVERIFIED") cls = "warn";
    else if (status === "BANNED" || status === "DEAD") cls = "bad";
    return `<span class="badge ${cls}"><span class="badge-dot"></span>${escapeHtml(status || "—")}</span>`;
}

function phase2Badge(vRaw) {
    const v = String(vRaw || "").trim();
    if (!v) return `<span class="badge info"><span class="badge-dot"></span>—</span>`;
    if (/ready/i.test(v)) return `<span class="badge good"><span class="badge-dot"></span>${escapeHtml(v)}</span>`;
    if (/not\s*eligible/i.test(v)) return `<span class="badge bad"><span class="badge-dot"></span>${escapeHtml(v)}</span>`;
    return `<span class="badge info"><span class="badge-dot"></span>${escapeHtml(v)}</span>`;
}

function escapeHtml(str) {
    return String(str ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

function getField(row, idxMap, keys) {
    for (const k of keys) {
        const idx = idxMap.get(k);
        if (idx !== undefined && idx < row.length) {
            return row[idx];
        }
    }
    return "";
}

function buildIdxMap(headers) {
    const m = new Map();
    headers.forEach((h, i) => m.set(normalizeHeader(h), i));
    return m;
}

function deriveProfilesModel(rows) {
    if (!rows || rows.length < 2) return { headers: [], items: [] };
    const headers = rows[0];
    const idx = buildIdxMap(headers);

    const items = rows
        .slice(1)
        .filter((r) => r.some((c) => String(c || "").trim() !== ""))
        .map((r, i) => {
            const nick = getField(r, idx, ["NICK NAME", "NICKNAME", "NICK NAME"]);
            const tags = getField(r, idx, ["TAGS"]);
            const city = getField(r, idx, ["CITY"]);
            const status = getField(r, idx, ["STATUS"]);
            const posts = getField(r, idx, ["POSTS"]);
            const followers = getField(r, idx, ["FOLLOWERS"]);
            const gender = getField(r, idx, ["GENDER"]);
            const married = getField(r, idx, ["MARRIED", "MARITAL"]);
            const age = getField(r, idx, ["AGE"]);
            const phase2 = getField(r, idx, ["PHASE 2", "PHASE2"]);
            const scraped = getField(r, idx, ["DATETIME SCRAP", "DATETIME SCRAPED", "DATETIME"]);
            const profileLink = getField(r, idx, ["PROFILE LINK", "PROFILE"]);
            const image = getField(r, idx, ["IMAGE", "AVATAR", "PROFILE IMAGE"]);
            const postUrl = getField(r, idx, ["POST URL", "PUBLIC PROFILE", "POSTURL"]);

            return {
                _i: i + 1,
                nick: String(nick || "").trim(),
                tags: String(tags || "").trim(),
                city: String(city || "").trim(),
                status: String(status || "").trim(),
                posts: String(posts || "").trim(),
                followers: String(followers || "").trim(),
                gender: String(gender || "").trim(),
                married: String(married || "").trim(),
                age: String(age || "").trim(),
                phase2: String(phase2 || "").trim(),
                scraped: String(scraped || "").trim(),
                profileLink: String(profileLink || "").trim(),
                image: String(image || "").trim(),
                postUrl: String(postUrl || "").trim(),
                _raw: r,
            };
        });

    return { headers, items };
}

function computeKpis(items) {
    const total = items.length;
    let verified = 0;
    let unverified = 0;
    let banned = 0;
    let phase2Ready = 0;
    let phase2NotEligible = 0;
    let newestScrape = "";

    for (const it of items) {
        const s = String(it.status || "").toUpperCase();
        if (s === "VERIFIED") verified++;
        else if (s === "UNVERIFIED") unverified++;
        else if (s === "BANNED" || s === "DEAD") banned++;

        if (/ready/i.test(it.phase2 || "")) phase2Ready++;
        if (/not\s*eligible/i.test(it.phase2 || "")) phase2NotEligible++;

        if (it.scraped && (!newestScrape || it.scraped > newestScrape)) {
            newestScrape = it.scraped;
        }
    }

    return {
        total,
        verified,
        unverified,
        banned,
        phase2Ready,
        phase2NotEligible,
        newestScrape: newestScrape || "—",
    };
}

function applyKpis(kpis) {
    el("kpiTotal").textContent = String(kpis.total);
    el("kpiVerified").textContent = String(kpis.verified);
    el("kpiUnverified").textContent = String(kpis.unverified);
    el("kpiBanned").textContent = String(kpis.banned);
    el("kpiNewest").textContent = String(kpis.newestScrape);
    el("kpiRows").textContent = String(kpis.total);

    el("phase2Ready").textContent = String(kpis.phase2Ready);
    el("phase2NotEligible").textContent = String(kpis.phase2NotEligible);

    const denom = kpis.phase2Ready + kpis.phase2NotEligible;
    const rate = denom > 0 ? (kpis.phase2Ready / denom) * 100 : 0;
    el("phase2Rate").textContent = `${rate.toFixed(0)}%`;
    el("phase2Bar").style.width = `${Math.max(0, Math.min(100, rate))}%`;

    el("freshness").textContent = String(kpis.newestScrape);
}

function getFilters() {
    const q = String(el("searchInput").value || "").trim().toLowerCase();
    const status = String(el("statusFilter").value || "").trim().toUpperCase();
    const phase2 = String(el("phase2Filter").value || "").trim();
    return { q, status, phase2 };
}

function matchesFilters(it, filters) {
    if (filters.status) {
        if (String(it.status || "").trim().toUpperCase() !== filters.status) return false;
    }
    if (filters.phase2) {
        if (String(it.phase2 || "").trim() !== filters.phase2) return false;
    }
    if (filters.q) {
        const hay = `${it.nick} ${it.city} ${it.tags} ${it.status} ${it.phase2}`.toLowerCase();
        if (!hay.includes(filters.q)) return false;
    }
    return true;
}

function renderTable(items) {
    const tbody = el("profilesTbody");
    const filters = getFilters();
    const filtered = items.filter((it) => matchesFilters(it, filters));

    el("totalCount").textContent = String(items.length);
    el("shownCount").textContent = String(filtered.length);

    if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="9" class="muted">No rows match filters.</td></tr>`;
        return;
    }

    tbody.innerHTML = filtered
        .slice(0, 400)
        .map((it, idx) => {
            const rowNo = idx + 1;
            const posts = escapeHtml(it.posts || "");
            const followers = escapeHtml(it.followers || "");
            const nick = escapeHtml(it.nick || "");
            const tags = escapeHtml(it.tags || "");
            const city = escapeHtml(it.city || "");
            const scraped = escapeHtml(it.scraped || "");
            const status = statusBadge(it.status);
            const phase2 = phase2Badge(it.phase2);
            const link = escapeHtml(it.profileLink || "");

            return `
        <tr data-link="${link}">
          <td class="mono">${rowNo}</td>
          <td><strong>${nick || "—"}</strong></td>
          <td>${tags || ""}</td>
          <td>${city || ""}</td>
          <td>${status}</td>
          <td class="mono">${posts || ""}</td>
          <td class="mono">${followers || ""}</td>
          <td>${phase2}</td>
          <td class="mono">${scraped || ""}</td>
        </tr>
      `;
        })
        .join("");

    tbody.querySelectorAll("tr[data-link]").forEach((tr) => {
        tr.addEventListener("click", () => {
            const link = tr.getAttribute("data-link") || "";
            if (link && /^https?:\/\//i.test(link)) {
                window.open(link, "_blank", "noreferrer");
            }
        });
    });
}

function renderCards(items) {
    const container = el("cardsContainer");
    const filters = getFilters();
    const filtered = items.filter((it) => matchesFilters(it, filters));

    const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
    if (_page > totalPages) _page = totalPages;
    if (_page < 1) _page = 1;

    const start = (_page - 1) * PAGE_SIZE;
    const pageItems = filtered.slice(start, start + PAGE_SIZE);

    const pageLabel = el("pageLabel");
    if (pageLabel) pageLabel.textContent = `Page ${_page} / ${totalPages}`;
    const prevBtn = el("prevPageBtn");
    const nextBtn = el("nextPageBtn");
    if (prevBtn) prevBtn.disabled = _page <= 1;
    if (nextBtn) nextBtn.disabled = _page >= totalPages;

    el("totalCount").textContent = String(items.length);
    el("shownCount").textContent = String(filtered.length);

    if (filtered.length === 0) {
        container.innerHTML = `<div class="muted">No rows match filters.</div>`;
        return;
    }

    container.innerHTML = pageItems
        .map((it) => {
            const nick = escapeHtml(it.nick || "—");
            const city = escapeHtml(it.city || "");
            const tags = escapeHtml(it.tags || "");
            const scraped = escapeHtml(it.scraped || "");

            const img = safeUrl(it.image);
            const posts = safeInt(it.posts || "");
            const followers = safeInt(it.followers || "");

            const gender = escapeHtml(it.gender || "—");
            const married = escapeHtml(it.married || "—");
            const age = escapeHtml(it.age || "—");

            const profileLink = safeUrl(it.profileLink);
            const publicLink = safeUrl(it.postUrl);

            const status = statusBadge(it.status);
            const phase2 = phase2Badge(it.phase2);

            return `
        <article class="profile-card" data-link="${escapeHtml(profileLink || publicLink)}">
          <div class="profile-bg" style="background-image:url('${escapeHtml(img)}')"></div>
          <div class="profile-head">
            <div class="avatar-wrap">
              <img class="avatar" alt="${nick}" src="${img || ""}" onerror="this.style.display='none'" />
            </div>
            <div class="profile-title">
              <div class="profile-nick">${nick}</div>
              <div class="profile-sub">${city ? city : ""}${city && scraped ? " • " : ""}${scraped}</div>
            </div>
            <div>${status}</div>
          </div>
          <div class="profile-body">
            <div class="kv"><div class="k">GENDER</div><div class="v">${gender}</div></div>
            <div class="kv"><div class="k">MARRIED</div><div class="v">${married}</div></div>
            <div class="kv"><div class="k">AGE</div><div class="v">${age}</div></div>
            <div class="kv"><div class="k">FOLLOWERS</div><div class="v">${followers}</div></div>
            <div class="kv"><div class="k">POSTS</div><div class="v">${posts}</div></div>
            <div class="kv" style="grid-column: 1 / -1;"><div class="k">PHASE 2</div><div class="v">${phase2}</div></div>
          </div>
          <div class="profile-foot">
            <div class="tag-pill">${tags || "No tags"}</div>
            <a class="link" href="${escapeHtml(publicLink || profileLink || "#")}" target="_blank" rel="noreferrer">Open</a>
          </div>
        </article>
      `;
        })
        .join("");

    container.querySelectorAll(".profile-card[data-link]").forEach((card) => {
        card.addEventListener("click", (ev) => {
            const a = ev.target && ev.target.closest ? ev.target.closest("a") : null;
            if (a) return;
            const link = card.getAttribute("data-link") || "";
            if (link && /^https?:\/\//i.test(link)) {
                window.open(link, "_blank", "noreferrer");
            }
        });
    });
}

function safeUrl(url) {
    const u = String(url || "").trim();
    if (!u) return "";
    if (/^https?:\/\//i.test(u)) return u;
    return "";
}

let _pollTimer = null;
let _currentItems = [];

async function fetchProfiles() {
    const url = CONFIG.profilesCsvUrl;
    el("csvLink").href = url;

    setSyncState("warn", "Syncing…");
    const startedAt = Date.now();

    const res = await fetch(`${url}&_ts=${Date.now()}`, { cache: "no-store" });
    if (!res.ok) {
        throw new Error(`CSV fetch failed: ${res.status}`);
    }
    const text = await res.text();
    const rows = parseCsv(text);
    const model = deriveProfilesModel(rows);

    // Extend model items with more fields used in cards
    _currentItems = model.items.map((it) => ({
        ...it,
        imageUrl: it.imageUrl || it.image || "",
        postUrl: it.postUrl || "",
    }));

    const kpis = computeKpis(model.items);
    applyKpis(kpis);
    if (_viewMode === "table") {
        renderTable(_currentItems);
    } else {
        renderCards(_currentItems);
    }

    const ms = Date.now() - startedAt;
    setSyncState("good", `Live • ${ms}ms`);
    el("lastSync").textContent = `${nowTime()}`;
}

function schedulePolling() {
    if (_pollTimer) clearInterval(_pollTimer);
    _pollTimer = setInterval(() => {
        fetchProfiles().catch((e) => {
            console.error(e);
            setSyncState("bad", "Sync error");
        });
    }, CONFIG.pollIntervalMs);
}

function bindUi() {
    el("pollIntervalLabel").textContent = `${Math.round(CONFIG.pollIntervalMs / 1000)}s`;

    el("refreshBtn").addEventListener("click", () => {
        fetchProfiles().catch((e) => {
            console.error(e);
            setSyncState("bad", "Sync error");
        });
    });

    ["searchInput", "statusFilter", "phase2Filter"].forEach((id) => {
        el(id).addEventListener("input", () => {
            _page = 1;
            if (_viewMode === "table") renderTable(_currentItems);
            else renderCards(_currentItems);
        });
        el(id).addEventListener("change", () => {
            _page = 1;
            if (_viewMode === "table") renderTable(_currentItems);
            else renderCards(_currentItems);
        });
    });

    el("cardViewBtn").addEventListener("click", () => {
        _viewMode = "cards";
        applyViewMode();
        renderCards(_currentItems);
    });

    el("tableViewBtn").addEventListener("click", () => {
        _viewMode = "table";
        applyViewMode();
        renderTable(_currentItems);
    });

    const prevBtn = el("prevPageBtn");
    const nextBtn = el("nextPageBtn");
    if (prevBtn && nextBtn) {
        prevBtn.addEventListener("click", () => {
            _page = Math.max(1, _page - 1);
            if (_viewMode === "cards") renderCards(_currentItems);
        });
        nextBtn.addEventListener("click", () => {
            _page = _page + 1;
            if (_viewMode === "cards") renderCards(_currentItems);
        });
    }
}

function applyViewMode() {
    const cards = el("cardsContainer");
    const table = el("tableContainer");
    const cardBtn = el("cardViewBtn");
    const tableBtn = el("tableViewBtn");

    if (_viewMode === "table") {
        cards.style.display = "none";
        table.style.display = "block";
        cardBtn.classList.remove("is-active");
        tableBtn.classList.add("is-active");
        const pager = el("cardsPager");
        if (pager) pager.style.display = "none";
    } else {
        cards.style.display = "grid";
        table.style.display = "none";
        cardBtn.classList.add("is-active");
        tableBtn.classList.remove("is-active");
        const pager = el("cardsPager");
        if (pager) pager.style.display = "flex";
    }
}

function init() {
    bindUi();
    applyViewMode();
    fetchProfiles()
        .catch((e) => {
            console.error(e);
            setSyncState("bad", "Sync error");
        })
        .finally(() => schedulePolling());
}

document.addEventListener("DOMContentLoaded", init);