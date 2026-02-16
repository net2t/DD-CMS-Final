// Live dashboard demo (public CSV polling)

const CONFIG = {
    pollIntervalMs: 15000,
    tabs: {
        profiles: {
            label: "Profiles",
            csvUrl:
                "https://docs.google.com/spreadsheets/d/e/2PACX-1vTKKALF4TyTPNlHmAEBMGNL8SG7HW9a-4aMHo5DTVeYttUI_YspNAsffRFw6wZW7w7D9XAZctcYuZz5/pub?gid=143642608&single=true&output=csv",
        },
        runlist: {
            label: "RunList",
            csvUrl:
                "https://docs.google.com/spreadsheets/d/e/2PACX-1vTKKALF4TyTPNlHmAEBMGNL8SG7HW9a-4aMHo5DTVeYttUI_YspNAsffRFw6wZW7w7D9XAZctcYuZz5/pub?gid=652207062&single=true&output=csv",
        },
        dashboard: {
            label: "Dashboard",
            csvUrl:
                "https://docs.google.com/spreadsheets/d/e/2PACX-1vTKKALF4TyTPNlHmAEBMGNL8SG7HW9a-4aMHo5DTVeYttUI_YspNAsffRFw6wZW7w7D9XAZctcYuZz5/pub?gid=1956711073&single=true&output=csv",
        },
        onlinelog: {
            label: "OnlineLog",
            csvUrl:
                "https://docs.google.com/spreadsheets/d/e/2PACX-1vTKKALF4TyTPNlHmAEBMGNL8SG7HW9a-4aMHo5DTVeYttUI_YspNAsffRFw6wZW7w7D9XAZctcYuZz5/pub?gid=2031676954&single=true&output=csv",
        },
    },
    defaultTab: "profiles",
};

const el = (id) => document.getElementById(id);

let _viewMode = "cards"; // 'cards' | 'table'
let _page = 1;
const PAGE_SIZE = 6;

let _activeTab = CONFIG.defaultTab;
let _currentModel = { headers: [], rows: [], items: [] };

function getActiveTabConfig() {
    return CONFIG.tabs[_activeTab] || CONFIG.tabs[CONFIG.defaultTab];
}

function setHeroTitles() {
    const t = getActiveTabConfig();
    const h1 = document.querySelector(".hero .h1");
    if (h1) h1.textContent = `${t.label} Overview`;

    const panelH2 = document.querySelector(".panel .h2");
    if (panelH2) panelH2.textContent = t.label;
}

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
    if (_activeTab !== "profiles") {
        if (!filters.q) return true;
        const obj = it && it._obj ? it._obj : {};
        const hay = Object.values(obj)
            .map((v) => String(v || ""))
            .join(" ")
            .toLowerCase();
        return hay.includes(filters.q);
    }
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
    if (_activeTab !== "profiles") {
        renderGenericTable(items);
        return;
    }
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

function renderGenericTable(items) {
    const tbody = el("profilesTbody");
    const filters = getFilters();
    const filtered = items.filter((it) => matchesFilters(it, filters));

    el("totalCount").textContent = String(items.length);
    el("shownCount").textContent = String(filtered.length);

    if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="9" class="muted">No rows match filters.</td></tr>`;
        return;
    }

    const headers = (_currentModel && _currentModel.headers) || [];
    const hA = headers[0] || "Row";
    const hB = headers[1] || "";
    const hC = headers[2] || "";

    tbody.innerHTML = filtered
        .slice(0, 400)
        .map((it, idx) => {
            const rowNo = idx + 1;
            const a = escapeHtml(String(it._obj?.[String(hA)] ?? ""));
            const b = escapeHtml(String(it._obj?.[String(hB)] ?? ""));
            const c = escapeHtml(String(it._obj?.[String(hC)] ?? ""));

            return `
        <tr data-idx="${it._i}">
          <td class="mono">${rowNo}</td>
          <td><strong>${a || "—"}</strong></td>
          <td>${b || ""}</td>
          <td>${c || ""}</td>
          <td>${escapeHtml(getActiveTabConfig().label)}</td>
          <td class="mono">${it._i}</td>
          <td class="mono">${escapeHtml(JSON.stringify(it._obj, null, 2))}</td>
          <td></td>
          <td class="mono"></td>
        </tr>
      `;
        })
        .join("");

    tbody.querySelectorAll("tr[data-idx]").forEach((tr) => {
        tr.addEventListener("click", () => {
            const idx = parseInt(tr.getAttribute("data-idx") || "0", 10);
            const item = filtered.find((x) => x._i === idx) || null;
            if (item) openDetailModal(item);
        });
    });
}

function renderCards(items) {
    const container = el("cardsContainer");
    if (_activeTab !== "profiles") {
        renderGenericCards(items);
        return;
    }
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
        <article class="profile-card" data-idx="${it._i}" data-link="${escapeHtml(profileLink || publicLink)}">
          <div class="profile-bg" style="background-image:url('${escapeHtml(img)}')"></div>
          <div class="shine" aria-hidden="true"></div>
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

    container.querySelectorAll(".profile-card[data-idx]").forEach((card) => {
        card.addEventListener("click", () => {
            const idx = parseInt(card.getAttribute("data-idx") || "0", 10);
            const item = _currentItems.find((x) => x._i === idx) || null;
            if (item) openDetailModal(item);
        });
    });
}

function renderGenericCards(items) {
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

    const headers = (_currentModel && _currentModel.headers) || [];
    const hA = headers[0] || "Row";
    const hB = headers[1] || "";
    const hC = headers[2] || "";

    if (filtered.length === 0) {
        container.innerHTML = `<div class="muted">No rows match filters.</div>`;
        return;
    }

    container.innerHTML = pageItems
        .map((it) => {
            const a = escapeHtml(String(it._obj?.[String(hA)] ?? ""));
            const b = escapeHtml(String(it._obj?.[String(hB)] ?? ""));
            const c = escapeHtml(String(it._obj?.[String(hC)] ?? ""));
            return `
        <article class="profile-card" data-idx="${it._i}" data-link="">
          <div class="profile-head">
            <div class="profile-title">
              <div class="profile-nick">${a || "—"}</div>
              <div class="profile-sub">${b}${b && c ? " • " : ""}${c}</div>
            </div>
            <div><span class="badge info"><span class="badge-dot"></span>${escapeHtml(getActiveTabConfig().label)}</span></div>
          </div>
          <div class="profile-body" style="grid-template-columns: 1fr;">
            ${headers
                .slice(3, 8)
                .map((h) => {
                    const v = it._obj?.[String(h)] ?? "";
                    return `<div class="kv"><div class="k">${escapeHtml(String(h || ""))}</div><div class="v">${escapeHtml(
                        String(v || "—")
                    )}</div></div>`;
                })
                .join("")}
          </div>
          <div class="profile-foot">
            <div class="tag-pill">Row #${it._i}</div>
            <span class="link">Details</span>
          </div>
        </article>
      `;
        })
        .join("");

    container.querySelectorAll(".profile-card[data-idx]").forEach((card) => {
        card.addEventListener("click", () => {
            const idx = parseInt(card.getAttribute("data-idx") || "0", 10);
            const item = filtered.find((x) => x._i === idx) || null;
            if (item) openDetailModal(item);
        });
    });
}

function safeUrl(url) {
    const u = String(url || "").trim();
    if (!u) return "";
    if (/^https?:\/\//i.test(u)) return u;
    return "";
}

function setFiltersVisibility() {
    const show = _activeTab === "profiles";
    const status = el("statusFilter");
    const phase2 = el("phase2Filter");
    if (status) status.style.display = show ? "" : "none";
    if (phase2) phase2.style.display = show ? "" : "none";
}

function deriveGenericModel(rows) {
    if (!rows || rows.length < 1) return { headers: [], rows: [], items: [] };
    const headers = rows[0] || [];
    const dataRows = rows
        .slice(1)
        .filter((r) => Array.isArray(r) && r.some((c) => String(c || "").trim() !== ""));

    const items = dataRows.map((r, i) => {
        const obj = {};
        for (let c = 0; c < headers.length; c++) {
            const key = String(headers[c] || `COL_${c + 1}`);
            obj[key] = r[c] ?? "";
        }
        return { _i: i + 1, _raw: r, _obj: obj };
    });

    return { headers, rows: dataRows, items };
}

function openDetailModal(item) {
    const modal = el("detailModal");
    if (!modal) return;

    const headers = (_currentModel && _currentModel.headers) || [];
    const title = el("detailTitle");
    const sub = el("detailSub");
    const body = el("detailBody");
    const openLink = el("detailOpenLink");

    const primary = (() => {
        if (_activeTab === "profiles") return item.nick || "Profile";
        const h0 = headers[0];
        const v0 = item && item._obj ? item._obj[String(h0 || "")] : "";
        return String(v0 || "Row").trim() || "Row";
    })();

    if (title) title.textContent = primary;
    if (sub) sub.textContent = `${getActiveTabConfig().label} • Row #${item._i || "—"}`;

    const kvHtml = headers
        .map((h, i) => {
            const key = String(h || "");
            const value = (() => {
                if (_activeTab === "profiles") {
                    const raw = item && item._raw ? item._raw[i] : "";
                    return raw ?? "";
                }
                return item && item._obj ? item._obj[key] : "";
            })();
            return `<div class="kv"><div class="k">${escapeHtml(key || `COL_${i + 1}`)}</div><div class="v">${escapeHtml(
                String(value ?? "")
            )}</div></div>`;
        })
        .join("");

    if (body) body.innerHTML = `<div class="profiles-grid" style="padding:0;grid-template-columns:1fr 1fr;">${kvHtml}</div>`;

    const candidateLink = (() => {
        if (_activeTab === "profiles") return safeUrl(item.profileLink) || safeUrl(item.postUrl) || "";
        const obj = item && item._obj ? item._obj : {};
        for (const k of Object.keys(obj)) {
            const v = safeUrl(obj[k]);
            if (v) return v;
        }
        return "";
    })();

    if (openLink) {
        if (candidateLink) {
            openLink.href = candidateLink;
            openLink.style.display = "";
        } else {
            openLink.href = "#";
            openLink.style.display = "none";
        }
    }

    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");
    modal._activeItem = item;
}

function closeDetailModal() {
    const modal = el("detailModal");
    if (!modal) return;
    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");
}

let _pollTimer = null;
let _currentItems = [];

function resolveTabFromUrl() {
    const u = new URL(window.location.href);
    const tab = String(u.searchParams.get("tab") || "").trim().toLowerCase();
    if (tab && CONFIG.tabs[tab]) return tab;
    return CONFIG.defaultTab;
}

function writeTabToUrl(tab) {
    const u = new URL(window.location.href);
    u.searchParams.set("tab", tab);
    window.history.replaceState({}, "", u.toString());
}

function applyActiveTabUi() {
    document.querySelectorAll(".tab[data-tab]").forEach((b) => {
        const t = b.getAttribute("data-tab");
        b.classList.toggle("is-active", t === _activeTab);
    });
    setHeroTitles();
    setFiltersVisibility();
}

async function fetchActiveTab() {
    const { csvUrl } = getActiveTabConfig();
    el("csvLink").href = csvUrl;

    setSyncState("warn", "Syncing…");
    const startedAt = Date.now();

    const res = await fetch(`${csvUrl}&_ts=${Date.now()}`, { cache: "no-store" });
    if (!res.ok) {
        throw new Error(`CSV fetch failed: ${res.status}`);
    }
    const text = await res.text();
    const rows = parseCsv(text);

    if (_activeTab === "profiles") {
        const model = deriveProfilesModel(rows);
        _currentModel = { headers: model.headers, rows: rows.slice(1), items: model.items };
        _currentItems = model.items.map((it) => ({
            ...it,
            imageUrl: it.imageUrl || it.image || "",
            postUrl: it.postUrl || "",
        }));

        const kpis = computeKpis(model.items);
        applyKpis(kpis);
    } else {
        const model = deriveGenericModel(rows);
        _currentModel = model;
        _currentItems = model.items;
        applyKpis({
            total: model.items.length,
            verified: 0,
            unverified: 0,
            banned: 0,
            phase2Ready: 0,
            phase2NotEligible: 0,
            newestScrape: "—",
        });
        const freshness = el("freshness");
        if (freshness) freshness.textContent = "—";
    }

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
        fetchActiveTab().catch((e) => {
            console.error(e);
            setSyncState("bad", "Sync error");
        });
    }, CONFIG.pollIntervalMs);
}

function bindUi() {
    el("pollIntervalLabel").textContent = `${Math.round(CONFIG.pollIntervalMs / 1000)}s`;

    document.querySelectorAll(".tab[data-tab]").forEach((btn) => {
        btn.addEventListener("click", () => {
            const t = btn.getAttribute("data-tab");
            if (!t || !CONFIG.tabs[t]) return;
            _activeTab = t;
            _page = 1;
            writeTabToUrl(_activeTab);
            applyActiveTabUi();
            fetchActiveTab().catch((e) => {
                console.error(e);
                setSyncState("bad", "Sync error");
            });
        });
    });

    el("refreshBtn").addEventListener("click", () => {
        fetchActiveTab().catch((e) => {
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

    const closeBtn = el("detailCloseBtn");
    if (closeBtn) closeBtn.addEventListener("click", closeDetailModal);

    const modal = el("detailModal");
    if (modal) {
        modal.addEventListener("click", (ev) => {
            const t = ev.target;
            if (t && t.getAttribute && t.getAttribute("data-close") === "true") {
                closeDetailModal();
            }
        });
    }

    document.addEventListener("keydown", (ev) => {
        if (ev.key === "Escape") closeDetailModal();
    });

    const copyBtn = el("detailCopyBtn");
    if (copyBtn) {
        copyBtn.addEventListener("click", async () => {
            const m = el("detailModal");
            const item = m ? m._activeItem : null;
            if (!item) return;
            const payload = _activeTab === "profiles" ? item : item._obj || {};
            try {
                await navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
            } catch (e) {
                console.error(e);
            }
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
    _activeTab = resolveTabFromUrl();
    applyActiveTabUi();
    bindUi();
    applyViewMode();
    fetchActiveTab()
        .catch((e) => {
            console.error(e);
            setSyncState("bad", "Sync error");
        })
        .finally(() => schedulePolling());
}

document.addEventListener("DOMContentLoaded", init);