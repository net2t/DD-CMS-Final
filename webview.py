"""
DD-CMS Web View Server
══════════════════════
Run with: python webview.py
Opens at: http://localhost:5050

Features:
- Profiles tab: Card grid with photo, nick, city, gender, age, etc.
  - Glowing ring animation on each card
  - Click card → popup with ALL profile info
  - Pagination: 100 per page, Prev/Next
  - Auto-refresh every 5 minutes
- Tags tab: View and edit Tags sheet
- RunList tab: View and manage RunList entries
- Dashboard tab: View-only run history
"""

import sys
import os
import json
import re
from pathlib import Path
from datetime import datetime

# ── sys.path fix ──────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(SCRIPT_DIR))

from flask import Flask, render_template_string, jsonify, request
from config.config_common import Config
from utils.sheets_manager import create_gsheets_client, SheetsManager

app = Flask(__name__)
app.secret_key = "ddcms-webview-secret"

# ── Sheets client (lazy init) ─────────────────────────────────────────────────
_sheets = None

def get_sheets():
    global _sheets
    if _sheets is None:
        client  = create_gsheets_client()
        _sheets = SheetsManager(client=client)
    return _sheets


# ══════════════════════════════════════════════════════════════════════════════
#  API Routes
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/profiles")
def api_profiles():
    """Return all profiles as JSON."""
    try:
        sh   = get_sheets()
        rows = sh.profiles_ws.get_all_values()
        if not rows:
            return jsonify({"profiles": [], "total": 0})
        headers = rows[0]
        profiles = []
        for row in rows[1:]:
            # Pad row to header length
            while len(row) < len(headers):
                row.append("")
            p = dict(zip(headers, row))
            profiles.append(p)
        return jsonify({"profiles": profiles, "total": len(profiles)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tags")
def api_tags():
    """Return Tags sheet data."""
    try:
        sh   = get_sheets()
        if not sh.tags_ws:
            return jsonify({"headers": [], "rows": []})
        rows = sh.tags_ws.get_all_values()
        return jsonify({"headers": rows[0] if rows else [], "rows": rows[1:] if len(rows) > 1 else []})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/runlist")
def api_runlist():
    """Return RunList sheet data."""
    try:
        sh   = get_sheets()
        rows = sh.target_ws.get_all_values()
        return jsonify({"headers": rows[0] if rows else [], "rows": rows[1:] if len(rows) > 1 else []})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/dashboard")
def api_dashboard():
    """Return Dashboard sheet data."""
    try:
        sh   = get_sheets()
        rows = sh.dashboard_ws.get_all_values()
        return jsonify({"headers": rows[0] if rows else [], "rows": rows[1:] if len(rows) > 1 else []})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/runlist/add", methods=["POST"])
def api_runlist_add():
    """Add a new entry to RunList."""
    try:
        data     = request.get_json()
        nickname = (data.get("nickname") or "").strip()
        tag      = (data.get("tag") or "").strip()
        if not nickname:
            return jsonify({"error": "Nickname required"}), 400
        sh = get_sheets()
        # Append row: nick, Pending, remarks blank, D blank, E blank, tag
        row = [nickname, Config.TARGET_STATUS_PENDING, "", "", "", tag]
        sh.target_ws.append_row(row)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/runlist/delete", methods=["POST"])
def api_runlist_delete():
    """Remove a RunList row by row index (1-based, skipping header)."""
    try:
        data    = request.get_json()
        row_num = int(data.get("row", 0))
        if row_num < 2:
            return jsonify({"error": "Invalid row"}), 400
        sh = get_sheets()
        sh.target_ws.delete_rows(row_num)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tags/update", methods=["POST"])
def api_tags_update():
    """Update a Tags cell."""
    try:
        data  = request.get_json()
        row   = int(data.get("row", 0))
        col   = int(data.get("col", 0))
        value = str(data.get("value", "")).strip()
        sh    = get_sheets()
        sh.tags_ws.update_cell(row, col, value)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
#  Main Page (Single-page HTML)
# ══════════════════════════════════════════════════════════════════════════════

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DD-CMS Web View</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;500;600;700&family=Share+Tech+Mono&family=Orbitron:wght@700;900&display=swap" rel="stylesheet">
<style>
/* ═══════════════════════════════════════════════════════════════════
   CSS Variables + Reset
═══════════════════════════════════════════════════════════════════ */
:root {
  --bg:        #0a0c12;
  --surface:   #10131e;
  --card:      #13172a;
  --border:    #1e2540;
  --accent:    #00e5ff;
  --accent2:   #7c3aed;
  --accent3:   #f59e0b;
  --danger:    #ef4444;
  --success:   #22c55e;
  --text:      #e2e8f0;
  --muted:     #64748b;
  --glow:      0 0 20px rgba(0,229,255,.35);
  --glow2:     0 0 30px rgba(124,58,237,.4);
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html { scroll-behavior: smooth; }

body {
  background: var(--bg);
  color: var(--text);
  font-family: 'Rajdhani', sans-serif;
  font-size: 15px;
  min-height: 100vh;
  overflow-x: hidden;
}

/* Animated grid background */
body::before {
  content: '';
  position: fixed; inset: 0;
  background-image:
    linear-gradient(rgba(0,229,255,.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0,229,255,.03) 1px, transparent 1px);
  background-size: 40px 40px;
  pointer-events: none;
  z-index: 0;
}

/* ═══════════════════════════════════════════════════════════════════
   Header
═══════════════════════════════════════════════════════════════════ */
header {
  position: sticky; top: 0; z-index: 100;
  background: rgba(10,12,18,.9);
  backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--border);
  padding: 0 24px;
  display: flex; align-items: center; gap: 32px;
}

.logo {
  font-family: 'Orbitron', monospace;
  font-size: 18px; font-weight: 900;
  color: var(--accent);
  text-shadow: var(--glow);
  letter-spacing: 3px;
  padding: 14px 0;
  white-space: nowrap;
}

.logo span { color: var(--accent2); }

nav {
  display: flex; gap: 4px; flex: 1;
}

.tab-btn {
  background: none; border: none;
  color: var(--muted);
  font-family: 'Rajdhani', sans-serif;
  font-size: 14px; font-weight: 600;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  padding: 18px 20px 14px;
  cursor: pointer;
  border-bottom: 3px solid transparent;
  transition: all .2s;
  position: relative;
}

.tab-btn:hover { color: var(--text); }
.tab-btn.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
  text-shadow: 0 0 12px rgba(0,229,255,.6);
}

.refresh-info {
  font-family: 'Share Tech Mono', monospace;
  font-size: 11px;
  color: var(--muted);
  text-align: right;
  white-space: nowrap;
}

.refresh-info span { color: var(--accent3); }

/* ═══════════════════════════════════════════════════════════════════
   Layout
═══════════════════════════════════════════════════════════════════ */
main {
  max-width: 1600px;
  margin: 0 auto;
  padding: 24px;
  position: relative; z-index: 1;
}

.tab-panel { display: none; }
.tab-panel.active { display: block; }

/* ═══════════════════════════════════════════════════════════════════
   Profiles Panel
═══════════════════════════════════════════════════════════════════ */
.profiles-toolbar {
  display: flex; gap: 12px; align-items: center;
  margin-bottom: 20px; flex-wrap: wrap;
}

.search-box {
  flex: 1; min-width: 200px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 16px;
  color: var(--text);
  font-family: 'Rajdhani', sans-serif;
  font-size: 14px;
  outline: none;
  transition: border-color .2s;
}
.search-box:focus { border-color: var(--accent); }
.search-box::placeholder { color: var(--muted); }

.filter-select {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 14px;
  color: var(--text);
  font-family: 'Rajdhani', sans-serif;
  font-size: 14px;
  outline: none;
  cursor: pointer;
}

.stat-bar {
  display: flex; gap: 20px; align-items: center;
  font-size: 13px; color: var(--muted);
}

.stat-bar strong { color: var(--accent); font-size: 16px; }

/* Card Grid */
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 20px;
  margin-bottom: 28px;
}

/* ═══════════════════════════════════════════════════════════════════
   Profile Card + Glow Ring Animation
═══════════════════════════════════════════════════════════════════ */
.profile-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 20px 16px 16px;
  cursor: pointer;
  transition: transform .25s, border-color .25s;
  position: relative;
  overflow: hidden;
}

.profile-card:hover {
  transform: translateY(-4px);
  border-color: rgba(0,229,255,.4);
}

/* Glow ring: a rotating conic-gradient border */
.profile-card::before {
  content: '';
  position: absolute;
  inset: -2px;
  border-radius: 18px;
  background: conic-gradient(
    from var(--ring-angle, 0deg),
    transparent 0deg,
    var(--accent) 60deg,
    var(--accent2) 120deg,
    transparent 180deg,
    transparent 360deg
  );
  animation: ring-spin 3s linear infinite;
  opacity: 0;
  transition: opacity .3s;
  z-index: 0;
}

.profile-card::after {
  content: '';
  position: absolute;
  inset: 1px;
  border-radius: 16px;
  background: var(--card);
  z-index: 1;
}

.profile-card:hover::before { opacity: 1; }

@property --ring-angle {
  syntax: '<angle>';
  inherits: false;
  initial-value: 0deg;
}

@keyframes ring-spin {
  to { --ring-angle: 360deg; }
}

.card-content {
  position: relative; z-index: 2;
  display: flex; flex-direction: column; align-items: center;
  gap: 8px;
}

/* Avatar */
.avatar-wrap {
  position: relative;
  width: 88px; height: 88px;
}

.avatar-img {
  width: 88px; height: 88px;
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid var(--border);
  background: var(--surface);
  display: block;
}

.avatar-initial {
  width: 88px; height: 88px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-family: 'Orbitron', monospace;
  font-size: 28px; font-weight: 700;
  color: var(--bg);
  border: 2px solid var(--border);
}

/* Run mode badge on avatar */
.run-badge {
  position: absolute; bottom: 2px; right: 2px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 9px; font-weight: 700;
  letter-spacing: 1px;
  padding: 2px 5px;
  color: var(--muted);
}

.run-badge.online { color: var(--accent); border-color: var(--accent); }
.run-badge.target { color: var(--accent3); border-color: var(--accent3); }

/* Card text */
.card-nick {
  font-family: 'Orbitron', monospace;
  font-size: 13px; font-weight: 700;
  color: var(--accent);
  text-align: center;
  letter-spacing: 1px;
  max-width: 100%;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

.card-city {
  font-size: 12px;
  color: var(--muted);
  text-align: center;
}

.card-meta {
  display: flex; gap: 8px; align-items: center;
  flex-wrap: wrap; justify-content: center;
}

.gender-icon { font-size: 16px; }
.meta-chip {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 2px 8px;
  font-size: 11px;
  color: var(--text);
}

/* Stats badges (GitHub-style) */
.stats-row {
  display: flex; gap: 6px; flex-wrap: wrap; justify-content: center;
}

.stat-badge {
  display: flex; align-items: center; gap: 4px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 3px 10px;
  font-size: 11px; font-weight: 600;
}

.stat-badge .label { color: var(--muted); }
.stat-badge .value { color: var(--accent3); }

.card-date {
  font-family: 'Share Tech Mono', monospace;
  font-size: 10px; color: var(--muted);
  text-align: center;
}

/* Tags */
.card-tags {
  display: flex; gap: 4px; flex-wrap: wrap; justify-content: center;
}

.tag-chip {
  background: rgba(124,58,237,.15);
  border: 1px solid rgba(124,58,237,.35);
  border-radius: 12px;
  padding: 2px 8px;
  font-size: 10px; font-weight: 600;
  color: #a78bfa;
}

/* Card links */
.card-links {
  display: flex; gap: 8px; justify-content: center;
  flex-wrap: wrap;
}

.card-link {
  display: flex; align-items: center; gap: 4px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 5px 10px;
  font-size: 11px; font-weight: 600;
  color: var(--text);
  text-decoration: none;
  transition: border-color .2s, color .2s;
}

.card-link:hover { border-color: var(--accent); color: var(--accent); }
.card-link svg { width: 12px; height: 12px; flex-shrink: 0; }

/* ═══════════════════════════════════════════════════════════════════
   Pagination
═══════════════════════════════════════════════════════════════════ */
.pagination {
  display: flex; gap: 8px; align-items: center; justify-content: center;
  padding: 8px 0 24px;
  flex-wrap: wrap;
}

.page-btn {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 8px 16px;
  color: var(--text);
  font-family: 'Rajdhani', sans-serif;
  font-size: 14px; font-weight: 600;
  cursor: pointer;
  transition: all .2s;
}

.page-btn:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
.page-btn:disabled { opacity: .3; cursor: not-allowed; }
.page-btn.current {
  background: rgba(0,229,255,.1);
  border-color: var(--accent);
  color: var(--accent);
}

.page-info {
  font-family: 'Share Tech Mono', monospace;
  font-size: 12px; color: var(--muted);
  padding: 0 8px;
}

/* ═══════════════════════════════════════════════════════════════════
   Modal / Popup
═══════════════════════════════════════════════════════════════════ */
.modal-overlay {
  position: fixed; inset: 0; z-index: 999;
  background: rgba(0,0,0,.75);
  backdrop-filter: blur(6px);
  display: flex; align-items: center; justify-content: center;
  padding: 24px;
  opacity: 0; pointer-events: none;
  transition: opacity .25s;
}

.modal-overlay.open {
  opacity: 1; pointer-events: all;
}

.modal {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 20px;
  width: 100%; max-width: 720px;
  max-height: 88vh;
  overflow: hidden;
  display: flex; flex-direction: column;
  box-shadow: 0 0 60px rgba(0,229,255,.15);
  transform: scale(.95);
  transition: transform .25s;
}

.modal-overlay.open .modal { transform: scale(1); }

.modal-header {
  display: flex; align-items: center; gap: 16px;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border);
}

.modal-avatar {
  width: 60px; height: 60px;
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid var(--accent);
  flex-shrink: 0;
}

.modal-avatar-initial {
  width: 60px; height: 60px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-family: 'Orbitron', monospace;
  font-size: 22px; font-weight: 700;
  color: var(--bg);
  border: 2px solid var(--accent);
  flex-shrink: 0;
}

.modal-title {
  flex: 1;
}

.modal-nick {
  font-family: 'Orbitron', monospace;
  font-size: 18px; font-weight: 900;
  color: var(--accent);
  letter-spacing: 2px;
}

.modal-sub {
  font-size: 13px; color: var(--muted);
  margin-top: 2px;
}

.modal-close {
  background: none; border: none;
  color: var(--muted); font-size: 24px;
  cursor: pointer; line-height: 1;
  transition: color .2s; padding: 4px;
}
.modal-close:hover { color: var(--danger); }

.modal-body {
  overflow-y: auto;
  padding: 20px 24px 24px;
  flex: 1;
}

/* Detail grid */
.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}

.detail-item {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 10px 14px;
}

.detail-label {
  font-size: 10px; font-weight: 700;
  letter-spacing: 2px;
  color: var(--muted);
  text-transform: uppercase;
  margin-bottom: 4px;
}

.detail-value {
  font-size: 13px; color: var(--text);
  word-break: break-all;
  white-space: pre-wrap;
  line-height: 1.5;
}

.detail-value a {
  color: var(--accent);
  text-decoration: none;
}

.detail-value a:hover { text-decoration: underline; }

.detail-value.empty { color: var(--muted); font-style: italic; font-size: 12px; }

/* ═══════════════════════════════════════════════════════════════════
   Tables (Tags / RunList / Dashboard)
═══════════════════════════════════════════════════════════════════ */
.table-wrap {
  overflow-x: auto;
  border: 1px solid var(--border);
  border-radius: 12px;
  margin-top: 16px;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

th {
  background: var(--surface);
  padding: 12px 16px;
  text-align: left;
  font-weight: 700;
  letter-spacing: 1px;
  font-size: 11px;
  color: var(--muted);
  text-transform: uppercase;
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}

td {
  padding: 10px 16px;
  border-bottom: 1px solid rgba(30,37,64,.5);
  vertical-align: top;
  color: var(--text);
}

tr:last-child td { border-bottom: none; }
tr:hover td { background: rgba(255,255,255,.02); }

.editable-cell {
  cursor: pointer;
  border-radius: 4px;
  transition: background .15s;
}
.editable-cell:hover { background: rgba(0,229,255,.08); }

.editable-input {
  background: var(--card);
  border: 1px solid var(--accent);
  border-radius: 4px;
  padding: 4px 8px;
  color: var(--text);
  font-family: 'Rajdhani', sans-serif;
  font-size: 13px;
  width: 100%;
  outline: none;
}

/* Status chips */
.status-chip {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 11px; font-weight: 700;
}

.status-done     { background: rgba(34,197,94,.15); color: var(--success); }
.status-pending  { background: rgba(245,158,11,.15); color: var(--accent3); }
.status-error    { background: rgba(239,68,68,.15); color: var(--danger); }
.status-skip     { background: rgba(100,116,139,.15); color: var(--muted); }

/* ═══════════════════════════════════════════════════════════════════
   RunList Add Form
═══════════════════════════════════════════════════════════════════ */
.add-form {
  display: flex; gap: 10px; flex-wrap: wrap;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
}

.add-form input {
  flex: 1; min-width: 160px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 14px;
  color: var(--text);
  font-family: 'Rajdhani', sans-serif;
  font-size: 14px;
  outline: none;
}
.add-form input:focus { border-color: var(--accent); }
.add-form input::placeholder { color: var(--muted); }

/* Buttons */
.btn {
  background: none;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 18px;
  color: var(--text);
  font-family: 'Rajdhani', sans-serif;
  font-size: 13px; font-weight: 700;
  letter-spacing: 1px;
  cursor: pointer;
  transition: all .2s;
  text-transform: uppercase;
}

.btn-primary {
  background: rgba(0,229,255,.1);
  border-color: var(--accent);
  color: var(--accent);
}
.btn-primary:hover { background: rgba(0,229,255,.2); box-shadow: var(--glow); }

.btn-danger {
  background: rgba(239,68,68,.1);
  border-color: var(--danger);
  color: var(--danger);
}
.btn-danger:hover { background: rgba(239,68,68,.2); }

/* ═══════════════════════════════════════════════════════════════════
   Loading / Error states
═══════════════════════════════════════════════════════════════════ */
.loading {
  display: flex; align-items: center; justify-content: center;
  gap: 12px;
  padding: 60px;
  color: var(--muted);
  font-family: 'Share Tech Mono', monospace;
  font-size: 14px;
}

.spinner {
  width: 24px; height: 24px;
  border: 3px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin .8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.empty-state {
  text-align: center;
  padding: 60px 24px;
  color: var(--muted);
  font-size: 15px;
}

/* Toast */
.toast {
  position: fixed; bottom: 24px; right: 24px; z-index: 9999;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 12px 20px;
  font-size: 14px;
  transform: translateY(80px);
  transition: transform .3s;
  max-width: 320px;
}

.toast.show { transform: translateY(0); }
.toast.ok    { border-color: var(--success); color: var(--success); }
.toast.error { border-color: var(--danger);  color: var(--danger); }

/* Dashboard metrics row */
.dash-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.metric-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
  text-align: center;
}

.metric-val {
  font-family: 'Orbitron', monospace;
  font-size: 28px; font-weight: 900;
  color: var(--accent);
}

.metric-label {
  font-size: 11px; font-weight: 700;
  letter-spacing: 2px;
  color: var(--muted);
  text-transform: uppercase;
  margin-top: 4px;
}

/* Scroll bar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--muted); }
</style>
</head>
<body>

<!-- HEADER -->
<header>
  <div class="logo">DD<span>-</span>CMS</div>
  <nav id="tabs">
    <button class="tab-btn active" data-tab="profiles">Profiles</button>
    <button class="tab-btn" data-tab="tags">Tags</button>
    <button class="tab-btn" data-tab="runlist">RunList</button>
    <button class="tab-btn" data-tab="dashboard">Dashboard</button>
  </nav>
  <div class="refresh-info">
    Auto-refresh in <span id="refresh-countdown">5:00</span>
  </div>
</header>

<main>

  <!-- ════════════════════════════════ PROFILES TAB ════════════════════════════ -->
  <div class="tab-panel active" id="panel-profiles">
    <div class="profiles-toolbar">
      <input class="search-box" type="text" id="search-input" placeholder="Search by nickname, city, tags...">
      <select class="filter-select" id="filter-mode">
        <option value="">All Modes</option>
        <option value="Online">Online</option>
        <option value="Target">Target</option>
      </select>
      <select class="filter-select" id="filter-gender">
        <option value="">All Genders</option>
        <option value="FEMALE">Female</option>
        <option value="MALE">Male</option>
      </select>
      <div class="stat-bar">
        Total: <strong id="total-count">—</strong>
        &nbsp;|&nbsp;
        Showing: <strong id="showing-count">—</strong>
      </div>
    </div>
    <div class="card-grid" id="card-grid">
      <div class="loading"><div class="spinner"></div>Loading profiles...</div>
    </div>
    <div class="pagination" id="pagination"></div>
  </div>

  <!-- ════════════════════════════════ TAGS TAB ════════════════════════════════ -->
  <div class="tab-panel" id="panel-tags">
    <div class="table-wrap">
      <table id="tags-table">
        <thead id="tags-thead"></thead>
        <tbody id="tags-tbody"></tbody>
      </table>
    </div>
  </div>

  <!-- ════════════════════════════════ RUNLIST TAB ═════════════════════════════ -->
  <div class="tab-panel" id="panel-runlist">
    <div class="add-form">
      <input type="text" id="rl-nick" placeholder="Nickname">
      <input type="text" id="rl-tag" placeholder="Tag / List value (optional)">
      <button class="btn btn-primary" onclick="addRunlistEntry()">+ Add Entry</button>
    </div>
    <div class="table-wrap">
      <table id="runlist-table">
        <thead id="runlist-thead"></thead>
        <tbody id="runlist-tbody"></tbody>
      </table>
    </div>
  </div>

  <!-- ════════════════════════════════ DASHBOARD TAB ══════════════════════════ -->
  <div class="tab-panel" id="panel-dashboard">
    <div class="dash-metrics" id="dash-metrics"></div>
    <div class="table-wrap">
      <table id="dash-table">
        <thead id="dash-thead"></thead>
        <tbody id="dash-tbody"></tbody>
      </table>
    </div>
  </div>

</main>

<!-- MODAL -->
<div class="modal-overlay" id="modal-overlay" onclick="closeModal(event)">
  <div class="modal" id="modal">
    <div class="modal-header">
      <div id="modal-avatar-wrap"></div>
      <div class="modal-title">
        <div class="modal-nick" id="modal-nick"></div>
        <div class="modal-sub" id="modal-sub"></div>
      </div>
      <button class="modal-close" onclick="closeModalBtn()">✕</button>
    </div>
    <div class="modal-body">
      <div class="detail-grid" id="modal-details"></div>
    </div>
  </div>
</div>

<!-- TOAST -->
<div class="toast" id="toast"></div>

<script>
/* ═══════════════════════════════════════════════════════════════════════════
   State
═══════════════════════════════════════════════════════════════════════════ */
let allProfiles   = [];
let filteredProf  = [];
let currentPage   = 1;
const PAGE_SIZE   = 100;

// Avatar color palette (10 colors for initials)
const AVATAR_COLORS = [
  '#00e5ff','#7c3aed','#f59e0b','#22c55e','#ef4444',
  '#ec4899','#06b6d4','#84cc16','#f97316','#8b5cf6'
];

function avatarColor(nick) {
  let hash = 0;
  for (let c of (nick || '')) hash = (hash * 31 + c.charCodeAt(0)) & 0xffffffff;
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

/* ═══════════════════════════════════════════════════════════════════════════
   Tabs
═══════════════════════════════════════════════════════════════════════════ */
const TAB_LOADERS = { tags: loadTags, runlist: loadRunlist, dashboard: loadDashboard };
const loadedTabs  = new Set(['profiles']);

document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    const tab = btn.dataset.tab;
    document.getElementById(`panel-${tab}`).classList.add('active');
    if (!loadedTabs.has(tab) && TAB_LOADERS[tab]) {
      TAB_LOADERS[tab]();
      loadedTabs.add(tab);
    }
  });
});

/* ═══════════════════════════════════════════════════════════════════════════
   Auto-refresh countdown (5 minutes)
═══════════════════════════════════════════════════════════════════════════ */
let countdown = 300;
function tick() {
  countdown--;
  if (countdown <= 0) {
    countdown = 300;
    loadProfiles();
    loadedTabs.clear(); loadedTabs.add('profiles');
  }
  const m = String(Math.floor(countdown / 60)).padStart(1,'0');
  const s = String(countdown % 60).padStart(2,'0');
  document.getElementById('refresh-countdown').textContent = `${m}:${s}`;
}
setInterval(tick, 1000);

/* ═══════════════════════════════════════════════════════════════════════════
   Toast
═══════════════════════════════════════════════════════════════════════════ */
let toastTimer;
function showToast(msg, type='ok') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = `toast ${type} show`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.className = 'toast', 3000);
}

/* ═══════════════════════════════════════════════════════════════════════════
   Profiles
═══════════════════════════════════════════════════════════════════════════ */
async function loadProfiles() {
  document.getElementById('card-grid').innerHTML =
    '<div class="loading"><div class="spinner"></div>Loading profiles...</div>';
  try {
    const r   = await fetch('/api/profiles');
    const d   = await r.json();
    allProfiles = d.profiles || [];
    document.getElementById('total-count').textContent = allProfiles.length;
    applyFilters();
  } catch(e) {
    document.getElementById('card-grid').innerHTML =
      `<div class="empty-state">Error loading profiles: ${e.message}</div>`;
  }
}

function applyFilters() {
  const q      = document.getElementById('search-input').value.toLowerCase().trim();
  const mode   = document.getElementById('filter-mode').value;
  const gender = document.getElementById('filter-gender').value;

  filteredProf = allProfiles.filter(p => {
    if (mode   && p['RUN MODE']  !== mode)   return false;
    if (gender && (p['GENDER']   || '').toUpperCase() !== gender) return false;
    if (q) {
      const hay = `${p['NICK NAME']} ${p['CITY']} ${p['TAGS']}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });

  currentPage = 1;
  document.getElementById('showing-count').textContent = filteredProf.length;
  renderCards();
  renderPagination();
}

['search-input','filter-mode','filter-gender'].forEach(id =>
  document.getElementById(id).addEventListener('input', applyFilters)
);

function renderCards() {
  const grid  = document.getElementById('card-grid');
  const start = (currentPage - 1) * PAGE_SIZE;
  const page  = filteredProf.slice(start, start + PAGE_SIZE);

  if (!page.length) {
    grid.innerHTML = '<div class="empty-state">No profiles found.</div>';
    return;
  }

  grid.innerHTML = page.map(p => buildCard(p)).join('');

  // Attach click handlers
  grid.querySelectorAll('.profile-card').forEach((card, i) => {
    card.addEventListener('click', () => openModal(filteredProf[start + i]));
  });
}

function buildCard(p) {
  const nick    = p['NICK NAME']  || '';
  const city    = p['CITY']       || '';
  const gender  = (p['GENDER']    || '').toLowerCase();
  const age     = p['AGE']        || '';
  const married = p['MARRIED']    || '';
  const follows = p['FOLLOWERS']  || '';
  const posts   = p['POSTS']      || '';
  const tags    = (p['TAGS']      || '').split(',').map(t => t.trim()).filter(Boolean);
  const date    = p['DATETIME SCRAP'] || '';
  const image   = p['IMAGE']      || '';
  const lastPost  = p['LAST POST']  || '';
  const profLink  = p['PROFILE LINK'] || '';
  const postUrl   = p['POST URL']   || '';
  const runMode   = p['RUN MODE']   || '';

  const genderIcon = gender.includes('female') ? '💃' : gender.includes('male') ? '🕺' : '';
  const runBadgeClass = runMode.toLowerCase() === 'online' ? 'online' : 'target';
  const color   = avatarColor(nick);

  const avatarHtml = image
    ? `<img class="avatar-img" src="${esc(image)}" alt="${esc(nick)}" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">\
       <div class="avatar-initial" style="display:none;background:${color}">${initials(nick)}</div>`
    : `<div class="avatar-initial" style="background:${color}">${initials(nick)}</div>`;

  const tagsHtml = tags.slice(0,3).map(t => `<span class="tag-chip">${esc(t)}</span>`).join('');

  const linksHtml = [
    lastPost  ? `<a class="card-link" href="${esc(lastPost)}"  target="_blank">${iconLink('Post')}</a>`    : '',
    profLink  ? `<a class="card-link" href="${esc(profLink)}"  target="_blank">${iconLink('Profile')}</a>` : '',
    postUrl   ? `<a class="card-link" href="${esc(postUrl)}"   target="_blank">${iconLink('Posts')}</a>`   : '',
  ].join('');

  return `<div class="profile-card">
  <div class="card-content">
    <div class="avatar-wrap">
      ${avatarHtml}
      ${runMode ? `<span class="run-badge ${runBadgeClass}">${runMode}</span>` : ''}
    </div>
    <div class="card-nick">${esc(nick)}</div>
    ${city ? `<div class="card-city">📍 ${esc(city)}</div>` : ''}
    <div class="card-meta">
      ${genderIcon ? `<span class="gender-icon">${genderIcon}</span>` : ''}
      ${age     ? `<span class="meta-chip">Age ${esc(age)}</span>` : ''}
      ${married ? `<span class="meta-chip">${esc(married)}</span>` : ''}
    </div>
    <div class="stats-row">
      <div class="stat-badge"><span class="label">Followers</span><span class="value">${esc(follows)||'–'}</span></div>
      <div class="stat-badge"><span class="label">Posts</span><span class="value">${esc(posts)||'–'}</span></div>
    </div>
    ${date ? `<div class="card-date">${esc(date)}</div>` : ''}
    ${tagsHtml ? `<div class="card-tags">${tagsHtml}</div>` : ''}
    ${linksHtml ? `<div class="card-links">${linksHtml}</div>` : ''}
  </div>
</div>`;
}

function iconLink(label) {
  return `<svg viewBox="0 0 16 16" fill="currentColor"><path d="M3.75 2h8.5A1.75 1.75 0 0 1 14 3.75v8.5A1.75 1.75 0 0 1 12.25 14h-8.5A1.75 1.75 0 0 1 2 12.25v-8.5A1.75 1.75 0 0 1 3.75 2Zm0 1.5a.25.25 0 0 0-.25.25v8.5c0 .138.112.25.25.25h8.5a.25.25 0 0 0 .25-.25v-8.5a.25.25 0 0 0-.25-.25h-8.5Z"/></svg>${label}`;
}

function initials(nick) {
  return (nick || '?').slice(0, 2).toUpperCase();
}

function esc(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function renderPagination() {
  const total = Math.ceil(filteredProf.length / PAGE_SIZE);
  const pag   = document.getElementById('pagination');
  if (total <= 1) { pag.innerHTML = ''; return; }

  let html = `<button class="page-btn" onclick="goPage(${currentPage-1})" ${currentPage===1?'disabled':''}>← Prev</button>`;
  const start = Math.max(1, currentPage - 2);
  const end   = Math.min(total, currentPage + 2);
  if (start > 1) html += `<button class="page-btn" onclick="goPage(1)">1</button>`;
  if (start > 2) html += `<span class="page-info">…</span>`;
  for (let i = start; i <= end; i++)
    html += `<button class="page-btn${i===currentPage?' current':''}" onclick="goPage(${i})">${i}</button>`;
  if (end < total - 1) html += `<span class="page-info">…</span>`;
  if (end < total) html += `<button class="page-btn" onclick="goPage(${total})">${total}</button>`;
  html += `<button class="page-btn" onclick="goPage(${currentPage+1})" ${currentPage===total?'disabled':''}>Next →</button>`;
  html += `<span class="page-info">Page ${currentPage} of ${total}</span>`;
  pag.innerHTML = html;
}

function goPage(n) {
  const total = Math.ceil(filteredProf.length / PAGE_SIZE);
  if (n < 1 || n > total) return;
  currentPage = n;
  renderCards(); renderPagination();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

/* ═══════════════════════════════════════════════════════════════════════════
   Modal
═══════════════════════════════════════════════════════════════════════════ */
function openModal(p) {
  const nick  = p['NICK NAME'] || '';
  const image = p['IMAGE']     || '';
  const color = avatarColor(nick);

  document.getElementById('modal-nick').textContent = nick;
  document.getElementById('modal-sub').textContent  =
    [p['CITY'], p['GENDER'], p['AGE'] ? `Age ${p['AGE']}` : ''].filter(Boolean).join(' · ');

  const aw = document.getElementById('modal-avatar-wrap');
  if (image) {
    aw.innerHTML = `<img class="modal-avatar" src="${esc(image)}" alt="${esc(nick)}"
      onerror="this.outerHTML='<div class=modal-avatar-initial style=background:${color}>${initials(nick)}</div>'">`;
  } else {
    aw.innerHTML = `<div class="modal-avatar-initial" style="background:${color}">${initials(nick)}</div>`;
  }

  // All fields
  const COLS = [
    'ID','NICK NAME','TAGS','CITY','GENDER','MARRIED','AGE','JOINED',
    'FOLLOWERS','LIST','POSTS','RUN MODE','DATETIME SCRAP',
    'LAST POST','LAST POST TIME','IMAGE','PROFILE LINK','POST URL',
    'RURL','MEH NAME','MEH LINK','MEH DATE','PHASE 2'
  ];
  const LINK_COLS = new Set(['LAST POST','PROFILE LINK','POST URL','RURL','MEH LINK']);

  const grid = document.getElementById('modal-details');
  grid.innerHTML = COLS.map(col => {
    const val = p[col] || '';
    let valHtml;
    if (!val) {
      valHtml = `<div class="detail-value empty">—</div>`;
    } else if (LINK_COLS.has(col)) {
      const links = val.split('\n').map(u => u.trim()).filter(Boolean);
      valHtml = `<div class="detail-value">${links.map(u =>
        `<a href="${esc(u)}" target="_blank">${esc(u.length > 40 ? u.slice(0,40)+'…' : u)}</a>`
      ).join('<br>')}</div>`;
    } else {
      valHtml = `<div class="detail-value">${esc(val)}</div>`;
    }
    return `<div class="detail-item">
      <div class="detail-label">${esc(col)}</div>
      ${valHtml}
    </div>`;
  }).join('');

  document.getElementById('modal-overlay').classList.add('open');
}

function closeModal(e) {
  if (e.target === document.getElementById('modal-overlay'))
    document.getElementById('modal-overlay').classList.remove('open');
}
function closeModalBtn() {
  document.getElementById('modal-overlay').classList.remove('open');
}
document.addEventListener('keydown', e => { if(e.key==='Escape') document.getElementById('modal-overlay').classList.remove('open'); });

/* ═══════════════════════════════════════════════════════════════════════════
   Tags Tab
═══════════════════════════════════════════════════════════════════════════ */
async function loadTags() {
  const thead = document.getElementById('tags-thead');
  const tbody = document.getElementById('tags-tbody');
  thead.innerHTML = tbody.innerHTML = '';
  try {
    const r = await fetch('/api/tags');
    const d = await r.json();
    if (!d.headers?.length) { tbody.innerHTML = '<tr><td>No Tags sheet found.</td></tr>'; return; }

    thead.innerHTML = `<tr>${d.headers.map(h => `<th>${esc(h)}</th>`).join('')}</tr>`;
    tbody.innerHTML = d.rows.map((row, ri) => `<tr>${d.headers.map((h, ci) => {
      const val = row[ci] || '';
      // Row number is ri+2 (1 header + 1-based)
      return `<td class="editable-cell" onclick="editCell(this, ${ri+2}, ${ci+1}, '${esc(val).replace(/'/g,"\\'")}')">${esc(val)}</td>`;
    }).join('')}</tr>`).join('');
  } catch(e) { tbody.innerHTML = `<tr><td>Error: ${e.message}</td></tr>`; }
}

function editCell(td, row, col, oldVal) {
  if (td.querySelector('input')) return;
  const input = document.createElement('input');
  input.className = 'editable-input';
  input.value     = td.textContent;
  td.innerHTML    = '';
  td.appendChild(input);
  input.focus();

  async function save() {
    const newVal = input.value.trim();
    if (newVal === oldVal) { td.textContent = oldVal; return; }
    try {
      const r = await fetch('/api/tags/update', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ row, col, value: newVal })
      });
      const d = await r.json();
      if (d.ok) { td.textContent = newVal; showToast('Saved!'); }
      else       { td.textContent = oldVal; showToast(d.error, 'error'); }
    } catch(e)   { td.textContent = oldVal; showToast(e.message, 'error'); }
  }

  input.addEventListener('blur',  save);
  input.addEventListener('keydown', e => { if(e.key==='Enter') input.blur(); if(e.key==='Escape') { td.textContent = oldVal; } });
}

/* ═══════════════════════════════════════════════════════════════════════════
   RunList Tab
═══════════════════════════════════════════════════════════════════════════ */
async function loadRunlist() {
  const thead = document.getElementById('runlist-thead');
  const tbody = document.getElementById('runlist-tbody');
  thead.innerHTML = tbody.innerHTML = '';
  try {
    const r = await fetch('/api/runlist');
    const d = await r.json();
    thead.innerHTML = `<tr>${(d.headers||[]).map(h => `<th>${esc(h)}</th>`).join('')}<th>Action</th></tr>`;
    tbody.innerHTML = (d.rows||[]).map((row, ri) => {
      const status = row[1] || '';
      let cls = 'status-pending';
      if (status.toLowerCase().includes('done'))    cls = 'status-done';
      if (status.toLowerCase().includes('error'))   cls = 'status-error';
      if (status.toLowerCase().includes('skip'))    cls = 'status-skip';

      const cells = row.map((v, ci) => ci === 1
        ? `<td><span class="status-chip ${cls}">${esc(v)}</span></td>`
        : `<td>${esc(v)}</td>`
      ).join('');
      return `<tr>${cells}<td>
        <button class="btn btn-danger" style="padding:4px 10px;font-size:11px" onclick="deleteRunlistRow(${ri+2}, this)">✕</button>
      </td></tr>`;
    }).join('');
  } catch(e) { tbody.innerHTML = `<tr><td>Error: ${e.message}</td></tr>`; }
}

async function addRunlistEntry() {
  const nick = document.getElementById('rl-nick').value.trim();
  const tag  = document.getElementById('rl-tag').value.trim();
  if (!nick) { showToast('Nickname is required', 'error'); return; }
  try {
    const r = await fetch('/api/runlist/add', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ nickname: nick, tag })
    });
    const d = await r.json();
    if (d.ok) {
      document.getElementById('rl-nick').value = '';
      document.getElementById('rl-tag').value  = '';
      showToast(`Added: ${nick}`);
      loadRunlist();
    } else showToast(d.error, 'error');
  } catch(e) { showToast(e.message, 'error'); }
}

async function deleteRunlistRow(rowNum, btn) {
  if (!confirm('Delete this entry?')) return;
  btn.disabled = true;
  try {
    const r = await fetch('/api/runlist/delete', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ row: rowNum })
    });
    const d = await r.json();
    if (d.ok) { showToast('Deleted'); loadRunlist(); }
    else { showToast(d.error, 'error'); btn.disabled = false; }
  } catch(e) { showToast(e.message, 'error'); btn.disabled = false; }
}

/* ═══════════════════════════════════════════════════════════════════════════
   Dashboard Tab
═══════════════════════════════════════════════════════════════════════════ */
async function loadDashboard() {
  const thead = document.getElementById('dash-thead');
  const tbody = document.getElementById('dash-tbody');
  const metr  = document.getElementById('dash-metrics');
  thead.innerHTML = tbody.innerHTML = metr.innerHTML = '';
  try {
    const r = await fetch('/api/dashboard');
    const d = await r.json();
    const headers = d.headers || [];
    const rows    = d.rows    || [];

    // Quick stats from latest row
    if (rows.length) {
      const latest = rows[0];
      const pairs  = [
        ['Total Profiles',  latest[2]],
        ['Successful',      latest[3]],
        ['New',             latest[5]],
        ['Updated',         latest[6]],
        ['Failed',          latest[4]],
        ['Duration (min)',  latest[7]],
      ];
      metr.innerHTML = pairs.map(([lbl, val]) =>
        `<div class="metric-card">
          <div class="metric-val">${esc(val||'–')}</div>
          <div class="metric-label">${esc(lbl)}</div>
        </div>`
      ).join('');
    }

    thead.innerHTML = `<tr>${headers.map(h => `<th>${esc(h)}</th>`).join('')}</tr>`;
    tbody.innerHTML = rows.map(row =>
      `<tr>${row.map(v => `<td>${esc(v)}</td>`).join('')}</tr>`
    ).join('');
  } catch(e) { tbody.innerHTML = `<tr><td>Error: ${e.message}</td></tr>`; }
}

/* ═══════════════════════════════════════════════════════════════════════════
   Init
═══════════════════════════════════════════════════════════════════════════ */
loadProfiles();
</script>
</body>
</html>"""

@app.route("/")
def index():
    return render_template_string(HTML)


if __name__ == "__main__":
    print("\n" + "="*60)
    print("  DD-CMS Web View")
    print("  Opening at: http://localhost:5050")
    print("  Press Ctrl+C to stop")
    print("="*60 + "\n")
    app.run(host="0.0.0.0", port=5050, debug=False)
