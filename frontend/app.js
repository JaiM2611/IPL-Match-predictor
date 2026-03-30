/* ═══════════════════════════════════════════════════════════════
   IPL 2026 Match Predictor — Frontend Logic
   ═══════════════════════════════════════════════════════════════ */

const API = "";  // relative base; backend serves frontend from /

// Team colors for charts/UI (fallback if API is unavailable)
const TEAM_COLORS = {
  MI:   "#004BA0", CSK:  "#F9CD05", RCB:  "#EC1C24",
  KKR:  "#3A225D", SRH:  "#F26522", DC:   "#0078BC",
  RR:   "#EA1A85", PBKS: "#AA4545", GT:   "#1C2B5E", LSG: "#A72B2A",
};

const TEAM_ABBR_DISPLAY = {
  MI: "🔵 MI", CSK: "🟡 CSK", RCB: "🔴 RCB", KKR: "🟣 KKR",
  SRH: "🟠 SRH", DC: "🔵 DC", RR: "🩷 RR", PBKS: "🔴 PBKS",
  GT: "🔵 GT", LSG: "🔴 LSG",
};

// Chart instances (keep references for destruction)
let winProbChart = null;
let h2hChart = null;
let formChart = null;

// Auto-refresh intervals
let pointsTableRefreshInterval = null;
let injuriesRefreshInterval = null;

// Refresh intervals (in milliseconds)
const REFRESH_INTERVALS = {
  pointsTable: 5 * 60 * 1000,  // 5 minutes
  injuries: 5 * 60 * 1000,      // 5 minutes
};

/* ─── INIT ─────────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
  loadTeams();
  loadVenues();
  setupNavigation();
});

/* ─── NAVIGATION ───────────────────────────────────────────────── */
function setupNavigation() {
  document.querySelectorAll(".nav-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const tab = btn.dataset.tab;
      document.querySelectorAll(".nav-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      document.querySelectorAll(".tab-section").forEach((s) => s.classList.remove("active"));
      const section = document.getElementById(`tab-${tab}`);
      if (section) section.classList.add("active");

      // Clear existing refresh intervals
      if (pointsTableRefreshInterval) {
        clearInterval(pointsTableRefreshInterval);
        pointsTableRefreshInterval = null;
      }
      if (injuriesRefreshInterval) {
        clearInterval(injuriesRefreshInterval);
        injuriesRefreshInterval = null;
      }

      // Load data and setup auto-refresh for appropriate tabs
      if (tab === "points-table") {
        loadPointsTable();
        pointsTableRefreshInterval = setInterval(loadPointsTable, REFRESH_INTERVALS.pointsTable);
      }
      if (tab === "injuries") {
        loadInjuries();
        injuriesRefreshInterval = setInterval(loadInjuries, REFRESH_INTERVALS.injuries);
      }
    });
  });
}

/* ─── LOAD TEAMS & VENUES ──────────────────────────────────────── */
async function loadTeams() {
  try {
    const teams = await apiFetch("/api/teams");
    const selects = [
      document.getElementById("team1"),
      document.getElementById("team2"),
      document.getElementById("toss-winner"),
    ];
    teams.forEach((t) => {
      selects.forEach((sel, idx) => {
        const opt = document.createElement("option");
        opt.value = t.short;
        opt.textContent = t.name;
        if (idx === 2 && t.short === "") return;
        sel.appendChild(opt);
      });
    });

    // Wire up change handlers
    document.getElementById("team1").addEventListener("change", onTeamChange);
    document.getElementById("team2").addEventListener("change", onTeamChange);
    document.getElementById("predict-btn").addEventListener("click", runPrediction);
  } catch (e) {
    console.error("Failed to load teams:", e);
  }
}

async function loadVenues() {
  try {
    const venues = await apiFetch("/api/venues");
    const sel = document.getElementById("venue");
    venues.forEach((v) => {
      const opt = document.createElement("option");
      opt.value = v;
      opt.textContent = v;
      sel.appendChild(opt);
    });
    sel.addEventListener("change", onVenueChange);
  } catch (e) {
    console.error("Failed to load venues:", e);
  }
}

/* ─── TEAM CHANGE ──────────────────────────────────────────────── */
async function onTeamChange() {
  const t1 = document.getElementById("team1").value;
  const t2 = document.getElementById("team2").value;
  const btn = document.getElementById("predict-btn");
  const venueVal = document.getElementById("venue").value;

  btn.disabled = !(t1 && t2 && venueVal);

  // Update toss-winner options
  const tw = document.getElementById("toss-winner");
  const current = tw.value;
  tw.innerHTML = '<option value="">Unknown / Not Yet</option>';
  [t1, t2].filter(Boolean).forEach((team) => {
    const opt = document.createElement("option");
    opt.value = team;
    opt.textContent = team;
    tw.appendChild(opt);
  });
  if ([t1, t2].includes(current)) tw.value = current;

  // Refresh injured players panel
  if (t1 && t2) await buildInjuredPanel(t1, t2);
}

async function onVenueChange() {
  const venue = document.getElementById("venue").value;
  const t1 = document.getElementById("team1").value;
  const t2 = document.getElementById("team2").value;
  const btn = document.getElementById("predict-btn");
  btn.disabled = !(t1 && t2 && venue);

  if (venue) await showVenueCard(venue);
}

/* ─── VENUE CARD ───────────────────────────────────────────────── */
async function showVenueCard(venue) {
  try {
    const venues = await apiFetch("/api/venues");
    // venues is an array of names; we need the full data from a predict call or dedicated endpoint
    // Since we have venue info in the predict response, show a simple placeholder here
    const card = document.getElementById("venue-info-card");
    card.style.display = "block";
    document.getElementById("venue-info-content").innerHTML = `
      <div class="venue-stat-row">
        <span class="venue-stat-label">Venue</span>
        <span class="venue-stat-value">${venue}</span>
      </div>
      <p class="muted small" style="margin-top:10px">Full venue analysis will appear after prediction.</p>
    `;
  } catch (e) { /* ignore */ }
}

/* ─── INJURED PLAYERS PANEL ────────────────────────────────────── */
async function buildInjuredPanel(t1, t2) {
  const container = document.getElementById("injured-container");
  container.innerHTML = '<div class="loading-spinner">Loading squads…</div>';

  try {
    const [squad1, squad2] = await Promise.all([
      apiFetch(`/api/squad/${t1}`),
      apiFetch(`/api/squad/${t2}`),
    ]);

    container.innerHTML = "";

    const renderTeam = (squad, teamShort) => {
      const label = document.createElement("div");
      label.className = "injured-team-label";
      label.textContent = `${squad.name} — mark injured/unavailable:`;
      container.appendChild(label);

      squad.squad.forEach((player) => {
        const row = document.createElement("label");
        row.className = "injured-player-row";
        row.innerHTML = `
          <input type="checkbox" name="injured" value="${player.name}" data-team="${teamShort}" />
          <span>${player.name}</span>
          <span class="muted" style="font-size:.76rem">(${player.role})</span>
        `;
        container.appendChild(row);
      });
    };

    renderTeam(squad1, t1);
    renderTeam(squad2, t2);
  } catch (e) {
    container.innerHTML = '<p class="muted">Could not load squad data.</p>';
  }
}

/* ─── RUN PREDICTION ───────────────────────────────────────────── */
async function runPrediction() {
  const team1 = document.getElementById("team1").value;
  const team2 = document.getElementById("team2").value;
  const venue = document.getElementById("venue").value;
  const matchType = document.getElementById("match-type").value;
  const timeOfDay = document.getElementById("time-of-day").value;
  const tossWinner = document.getElementById("toss-winner").value;
  const tossDecision = document.getElementById("toss-decision").value;

  const injuredCheckboxes = document.querySelectorAll('input[name="injured"]:checked');
  const injuredPlayers = Array.from(injuredCheckboxes).map((cb) => cb.value);

  const btn = document.getElementById("predict-btn");
  btn.disabled = true;
  btn.innerHTML = '<span class="btn-icon">⏳</span> Predicting…';

  try {
    const result = await apiFetch("/api/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        team1, team2, venue, match_type: matchType,
        time_of_day: timeOfDay, toss_winner: tossWinner,
        toss_decision: tossDecision, injured_players: injuredPlayers,
      }),
    });
    try {
      renderResults(result);
    } catch (renderErr) {
      console.error("Render error:", renderErr);
    }
  } catch (e) {
    alert(`Prediction failed: ${e.message}`);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span class="btn-icon">🔮</span> Predict Match';
  }
}

/* ─── RENDER RESULTS ───────────────────────────────────────────── */
function renderResults(data) {
  const section = document.getElementById("results-section");
  section.style.display = "block";
  section.scrollIntoView({ behavior: "smooth", block: "start" });

  renderWinnerBanner(data);
  renderCharts(data);
  renderInsights(data);
  renderPlayingXI(data);
  renderVenueStats(data);
}

function renderWinnerBanner(data) {
  const t1Color = data.team1_color || TEAM_COLORS[data.team1] || "#888";
  const t2Color = data.team2_color || TEAM_COLORS[data.team2] || "#555";

  // Team logos (colour circles with abbreviation)
  const logo1 = document.getElementById("team1-logo");
  logo1.style.background = t1Color;
  logo1.textContent = data.team1;

  const logo2 = document.getElementById("team2-logo");
  logo2.style.background = t2Color;
  logo2.textContent = data.team2;

  document.getElementById("team1-display-name").textContent = data.team1_name;
  document.getElementById("team2-display-name").textContent = data.team2_name;
  document.getElementById("team1-prob").textContent = `${data.team1_probability}%`;
  document.getElementById("team2-prob").textContent = `${data.team2_probability}%`;

  const badge = document.getElementById("confidence-badge");
  badge.textContent = `${data.confidence} confidence`;
  badge.className = `confidence-badge ${data.confidence}`;

  document.getElementById("winner-label").textContent =
    `🏆 Predicted Winner: ${data.predicted_winner_name}`;

  // Probability bar
  document.getElementById("t1-fill").style.width = `${data.team1_probability}%`;
  document.getElementById("t2-fill").style.width = `${data.team2_probability}%`;

  // Highlight winner team block
  const winnerBlock = data.predicted_winner === data.team1
    ? document.getElementById("team1-block")
    : document.getElementById("team2-block");
  winnerBlock.style.filter = "drop-shadow(0 0 12px rgba(63,185,80,.5))";
}

function renderCharts(data) {
  if (typeof Chart === "undefined") {
    console.warn("Chart.js not available — skipping charts.");
    document.querySelectorAll(".chart-card").forEach((el) => { el.style.display = "none"; });
    return;
  }

  const t1Color = data.team1_color || TEAM_COLORS[data.team1] || "#888";
  const t2Color = data.team2_color || TEAM_COLORS[data.team2] || "#555";

  // Destroy previous charts
  if (winProbChart) winProbChart.destroy();
  if (h2hChart) h2hChart.destroy();
  if (formChart) formChart.destroy();

  const chartDefaults = {
    plugins: {
      legend: { labels: { color: "#e6edf3", font: { size: 12 } } },
    },
  };

  // Win Probability — Doughnut
  winProbChart = new Chart(document.getElementById("winProbChart"), {
    type: "doughnut",
    data: {
      labels: [data.team1_name, data.team2_name],
      datasets: [{
        data: [data.team1_probability, data.team2_probability],
        backgroundColor: [t1Color, t2Color],
        borderColor: "#161b22",
        borderWidth: 3,
      }],
    },
    options: {
      ...chartDefaults,
      cutout: "65%",
      maintainAspectRatio: false,
    },
  });

  // Head-to-Head — Bar
  const h2h = data.h2h;
  h2hChart = new Chart(document.getElementById("h2hChart"), {
    type: "bar",
    data: {
      labels: [data.team1_name, data.team2_name],
      datasets: [{
        label: "Total Wins",
        data: [h2h.team1_wins, h2h.team2_wins],
        backgroundColor: [t1Color, t2Color],
        borderRadius: 6,
        borderSkipped: false,
      }],
    },
    options: {
      ...chartDefaults,
      maintainAspectRatio: false,
      scales: {
        x: { ticks: { color: "#8b949e" }, grid: { color: "#30363d" } },
        y: { ticks: { color: "#8b949e" }, grid: { color: "#30363d" } },
      },
    },
  });

  // Recent Form — last 5 matches as stacked bar (W/L)
  const form1 = data.recent_form[data.team1]?.last5 || [];
  const form2 = data.recent_form[data.team2]?.last5 || [];

  const countWins = (arr) => arr.filter((x) => x === "W").length;
  const f1w = countWins(form1);
  const f2w = countWins(form2);

  formChart = new Chart(document.getElementById("formChart"), {
    type: "bar",
    data: {
      labels: [data.team1_name, data.team2_name],
      datasets: [
        {
          label: "Wins (Last 5)",
          data: [f1w, f2w],
          backgroundColor: ["rgba(63,185,80,.8)", "rgba(63,185,80,.6)"],
          borderRadius: 4,
        },
        {
          label: "Losses (Last 5)",
          data: [5 - f1w, 5 - f2w],
          backgroundColor: ["rgba(248,81,73,.5)", "rgba(248,81,73,.4)"],
          borderRadius: 4,
        },
      ],
    },
    options: {
      ...chartDefaults,
      maintainAspectRatio: false,
      scales: {
        x: { stacked: true, ticks: { color: "#8b949e" }, grid: { color: "#30363d" } },
        y: { stacked: true, ticks: { color: "#8b949e" }, grid: { color: "#30363d" }, max: 5 },
      },
    },
  });
}

function renderInsights(data) {
  const list = document.getElementById("insights-list");
  list.innerHTML = "";
  (data.key_insights || []).forEach((ins) => {
    const item = document.createElement("div");
    item.className = `insight-item ${ins.impact}`;
    item.innerHTML = `
      <div class="insight-factor">${ins.factor}</div>
      <div class="insight-detail">${ins.detail}</div>
    `;
    list.appendChild(item);
  });
}

function renderPlayingXI(data) {
  document.getElementById("xi-title-1").textContent = `🏏 ${data.team1_name} — Probable XI`;
  document.getElementById("xi-title-2").textContent = `🏏 ${data.team2_name} — Probable XI`;

  renderXIList("xi-team1", data.team1_playing_xi);
  renderXIList("xi-team2", data.team2_playing_xi);
}

function renderXIList(containerId, players) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";
  players.forEach((p, idx) => {
    const roleClass = getRoleClass(p.role);
    const roleShort = getRoleShort(p.role);
    const row = document.createElement("div");
    row.className = "xi-player";
    row.innerHTML = `
      <span class="xi-num">${idx + 1}</span>
      <span class="xi-player-name">${p.name}</span>
      ${p.key_player ? '<span class="xi-key-star">★</span>' : ""}
      <span class="xi-role-badge ${roleClass}">${roleShort}</span>
      ${p.is_overseas ? '<span class="xi-overseas-badge">Overseas</span>' : ""}
    `;
    container.appendChild(row);
  });
}

function getRoleClass(role) {
  if (!role) return "";
  const r = role.toLowerCase();
  if (r.includes("wicket")) return "keeper";
  if (r.includes("all")) return "allrounder";
  if (r.includes("bowl")) return "bowler";
  return "batsman";
}

function getRoleShort(role) {
  if (!role) return "";
  const r = role.toLowerCase();
  if (r.includes("wicket")) return "WK";
  if (r.includes("all")) return "AR";
  if (r.includes("bowl")) return "Bowl";
  return "Bat";
}

function renderVenueStats(data) {
  const v = data.venue_info;
  if (!v) return;
  const container = document.getElementById("venue-stats-content");
  const grid = [
    { label: "Avg 1st Innings Score", value: v.avg_first_innings_score || "N/A", sub: "runs" },
    { label: "Par Score", value: v.par_score || "N/A", sub: "runs" },
    { label: "Pitch Type", value: capitalize(v.pitch_type || "Balanced"), sub: "surface" },
    { label: "Dew Factor", value: capitalize(v.dew_factor || "Low"), sub: "night matches" },
    { label: "Spin Friendly", value: v.spin_friendly ? "Yes" : "No", sub: v.spin_friendly ? "Take extra spinners" : "" },
    { label: "Boundary Size", value: capitalize((v.boundary_size || "medium").replace("_", " ")), sub: "" },
  ];
  container.innerHTML = grid.map((item) => `
    <div class="venue-stat-box">
      <div class="label">${item.label}</div>
      <div class="value">${item.value}</div>
      ${item.sub ? `<div class="sub">${item.sub}</div>` : ""}
    </div>
  `).join("");

  // Update venue info card too
  const card = document.getElementById("venue-info-card");
  card.style.display = "block";
  document.getElementById("venue-info-content").innerHTML = `
    <div class="venue-stat-row">
      <span class="venue-stat-label">City</span>
      <span class="venue-stat-value">${v.city || data.venue}</span>
    </div>
    <div class="venue-stat-row">
      <span class="venue-stat-label">Avg 1st Innings</span>
      <span class="venue-stat-value">${v.avg_first_innings_score || "—"}</span>
    </div>
    <div class="venue-stat-row">
      <span class="venue-stat-label">Dew Factor</span>
      <span class="venue-stat-value">${capitalize(v.dew_factor || "—")}</span>
    </div>
    <div class="venue-stat-row">
      <span class="venue-stat-label">Pitch Type</span>
      <span class="venue-stat-value">${capitalize(v.pitch_type || "—")}</span>
    </div>
    <p class="muted small" style="margin-top:12px;font-size:.8rem">${v.historical_notes || ""}</p>
  `;
}

/* ─── POINTS TABLE ─────────────────────────────────────────────── */
async function loadPointsTable() {
  const container = document.getElementById("points-table-container");
  const badge = document.getElementById("points-source-badge");

  // Show loading only if container is empty
  if (!container.querySelector("table")) {
    container.innerHTML = '<div class="loading-spinner">Fetching latest standings…</div>';
  }

  try {
    // Use V2 endpoint with multi-source fallback
    const resp = await apiFetch("/api/v2/standings");

    // Update badge based on source
    const source = resp.source || "N/A";
    const isLive = ["cric_api", "freewebapi", "espncricinfo"].includes(source);
    const isCached = source === "cached";
    const isStale = resp.is_stale || false;

    if (isStale) {
      badge.textContent = "⚠️ Stale Data";
      badge.className = "source-badge stale";
    } else if (isLive) {
      badge.textContent = "🟢 Live";
      badge.className = "source-badge live";
    } else if (isCached) {
      badge.textContent = "🔵 Cached";
      badge.className = "source-badge cached";
    } else {
      badge.textContent = `📡 ${source}`;
      badge.className = "source-badge";
    }

    const table = document.createElement("table");
    table.className = "points-table";
    table.innerHTML = `
      <thead>
        <tr>
          <th>#</th><th>Team</th><th>M</th><th>W</th>
          <th>L</th><th>Pts</th><th>NRR</th><th>Form</th>
        </tr>
      </thead>
      <tbody></tbody>
    `;
    const tbody = table.querySelector("tbody");

    resp.data.forEach((row, idx) => {
      const isPlayoff = idx < 4;
      const tr = document.createElement("tr");
      if (isPlayoff) tr.className = "playoff-zone";

      const nrr = parseFloat(row.nrr || 0);
      const nrrClass = nrr >= 0 ? "nrr-pos" : "nrr-neg";
      const nrrStr = nrr >= 0 ? `+${nrr.toFixed(3)}` : nrr.toFixed(3);

      // Team color dot
      const teamColor = TEAM_COLORS[row.team] || "#888";

      tr.innerHTML = `
        <td class="pos-number">${idx + 1}${isPlayoff ? " 🔸" : ""}</td>
        <td><div class="team-name-cell">
          <span class="team-dot" style="background:${teamColor}"></span>
          ${row.name || row.team}
        </div></td>
        <td>${row.matches || "—"}</td>
        <td>${row.wins || "—"}</td>
        <td>${row.losses || "—"}</td>
        <td class="pts">${row.points || "—"}</td>
        <td class="${nrrClass}">${nrrStr}</td>
        <td>${renderFormPills(row.team)}</td>
      `;
      tbody.appendChild(tr);
    });

    container.innerHTML = "";
    container.appendChild(table);

    // Add last updated timestamp if available
    if (resp.timestamp || resp.fetched_at) {
      const timestamp = resp.timestamp || new Date(resp.fetched_at * 1000).toISOString();
      const timeEl = document.createElement("p");
      timeEl.className = "muted small";
      timeEl.style.marginTop = "10px";
      timeEl.textContent = `Last updated: ${new Date(timestamp).toLocaleString()}`;
      container.appendChild(timeEl);
    }
  } catch (e) {
    container.innerHTML = `<p class="error-message">⚠️ Failed to load points table: ${e.message}</p>`;
    badge.textContent = "❌ Error";
    badge.className = "source-badge error";
  }
}

function renderFormPills(team) {
  // Use recent form from our local data (not available via API directly, use static)
  const formMap = {
    KKR: ["W","W","W","L","W"], CSK: ["W","W","L","W","W"],
    GT: ["W","W","L","W","L"],  MI: ["W","L","W","W","L"],
    RCB: ["L","W","W","L","W"], SRH: ["W","L","W","W","L"],
    DC: ["L","W","L","W","W"],  RR: ["W","W","L","L","W"],
    PBKS: ["L","W","W","W","L"], LSG: ["L","L","W","L","W"],
  };
  const form = formMap[team] || [];
  return `<div class="form-pills">${form.map((r) =>
    `<span class="form-pill ${r}">${r}</span>`
  ).join("")}</div>`;
}

/* ─── INJURY UPDATES ───────────────────────────────────────────── */
async function loadInjuries() {
  const container = document.getElementById("injuries-container");
  const badge = document.getElementById("injury-source-badge");

  // Show loading only if container is empty
  if (!container.querySelector(".injury-list")) {
    container.innerHTML = '<div class="loading-spinner">Fetching latest injury updates…</div>';
  }

  try {
    // Use V2 endpoint with multi-source fallback
    const resp = await apiFetch("/api/v2/injuries");

    // Update badge based on source
    const source = resp.source || "N/A";
    const isLive = ["news_api", "gnews_api", "espncricinfo"].includes(source);
    const isCached = source === "cached";
    const isStale = resp.is_stale || false;

    if (isStale) {
      badge.textContent = "⚠️ Stale Data";
      badge.className = "source-badge stale";
    } else if (isLive) {
      badge.textContent = "🟢 Live";
      badge.className = "source-badge live";
    } else if (isCached) {
      badge.textContent = "🔵 Cached";
      badge.className = "source-badge cached";
    } else {
      badge.textContent = `📡 ${source}`;
      badge.className = "source-badge";
    }

    const list = document.createElement("div");
    list.className = "injury-list";

    if (Array.isArray(resp.data) && resp.data.length > 0) {
      resp.data.forEach((item) => {
        const card = document.createElement("div");
        const status = item.status || "Available";
        card.className = `injury-card ${status.toLowerCase() === "available" ? "available" : "unavailable"}`;

        if (item.player) {
          card.innerHTML = `
            <span class="injury-team-badge">${item.team || "?"}</span>
            <span class="injury-player-name">${item.player}</span>
            <span class="injury-status ${status}">${status}</span>
            ${item.injury ? `<span class="muted small">${item.injury}</span>` : ""}
          `;
        } else if (item.text) {
          card.innerHTML = `<span class="injury-detail">${item.text}</span>`;
        }
        list.appendChild(card);
      });
    } else {
      list.innerHTML = '<p class="muted">No injury updates available.</p>';
    }

    container.innerHTML = "";
    container.appendChild(list);

    // Add last updated timestamp if available
    if (resp.timestamp || resp.fetched_at) {
      const timestamp = resp.timestamp || new Date(resp.fetched_at * 1000).toISOString();
      const timeEl = document.createElement("p");
      timeEl.className = "muted small";
      timeEl.style.marginTop = "10px";
      timeEl.textContent = `Last updated: ${new Date(timestamp).toLocaleString()}`;
      container.appendChild(timeEl);
    }
  } catch (e) {
    container.innerHTML = `<p class="error-message">⚠️ Failed to load injury data: ${e.message}</p>`;
    badge.textContent = "❌ Error";
    badge.className = "source-badge error";
  }
}

/* ─── UTILS ─────────────────────────────────────────────────────── */
async function apiFetch(url, options = {}) {
  const resp = await fetch(API + url, options);
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.error || `HTTP ${resp.status}`);
  }
  return resp.json();
}

function capitalize(str) {
  if (!str) return "";
  return str.charAt(0).toUpperCase() + str.slice(1);
}
