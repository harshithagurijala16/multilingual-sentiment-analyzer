/**
 * IndicSentiment - Full Featured Frontend Application
 * Vanilla JS SPA with Tailwind CSS & Chart.js
 */

const STATE = {
  token: localStorage.getItem("indic_token") || null,
  user: JSON.parse(localStorage.getItem("indic_user") || "null"),
  activePage: "dashboard",
  theme: localStorage.getItem("indic_theme") || "light",
  products: [],
  charts: {},
  reviewsPage: 1,
  reviewsLimit: 10,
  reviewsTotal: 0,
  selectedReviewForCorrection: null,
};

// Preset examples for Live Analyzer
const ANALYZE_PRESETS = [
  {
    lang: "Telugu (Romanized)",
    text: "Ee smartphone camera quality chala bagundi, battery backup kuda superb!",
  },
  {
    lang: "Tamil (Code-Mixed)",
    text: "Delivery romba late aachu, but product packaging super-ah irundhuchu.",
  },
  {
    lang: "Hindi (Devanagari)",
    text: "उत्पाद की गुणवत्ता बहुत ही शानदार है, पैसा वसूल सामान है।",
  },
  {
    lang: "Kannada (Romanized)",
    text: "Screen display chennagide aadre battery tumba bega khali aaguthe.",
  },
  {
    lang: "Malayalam (Romanized)",
    text: "Kollam nalla product aanu, delivery valare vegathil aayirunnu.",
  },
  {
    lang: "Bengali (Bengali Script)",
    text: "পণ্যটি সত্যিই খুব ভালো এবং দাম অনুযায়ী একদম পারফেক্ট।",
  },
];

/* ==========================================================================
   TOAST NOTIFICATIONS
   ========================================================================== */
function showToast(message, type = "info") {
  const container = document.getElementById("toastContainer");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className =
    "pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-2xl shadow-xl text-xs font-semibold transform transition-all duration-300 translate-y-2 opacity-0";

  let bgClasses = "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900";
  let icon = "ℹ️";

  if (type === "success") {
    bgClasses = "bg-emerald-600 text-white shadow-emerald-500/20";
    icon = "✓";
  } else if (type === "error") {
    bgClasses = "bg-rose-600 text-white shadow-rose-500/20";
    icon = "✕";
  } else if (type === "warning") {
    bgClasses = "bg-amber-500 text-white shadow-amber-500/20";
    icon = "⚠️";
  }

  toast.className += " " + bgClasses;
  toast.innerHTML = `<span class="text-sm font-bold">${icon}</span><span>${message}</span>`;
  container.appendChild(toast);

  // Animate in
  requestAnimationFrame(() => {
    toast.classList.remove("translate-y-2", "opacity-0");
    toast.classList.add("translate-y-0", "opacity-100");
  });

  // Remove after 3.5s
  setTimeout(() => {
    toast.classList.remove("translate-y-0", "opacity-100");
    toast.classList.add("translate-y-2", "opacity-0");
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

/* ==========================================================================
   API HELPER
   ========================================================================== */
async function apiFetch(endpoint, options = {}) {
  const headers = options.headers || {};
  if (STATE.token) {
    headers["Authorization"] = `Bearer ${STATE.token}`;
  }
  if (!options.isFormData && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const config = {
    ...options,
    headers,
  };

  try {
    const res = await fetch(endpoint, config);
    if (res.status === 401) {
      // Session expired
      logout();
      showToast("Session expired. Please sign in again.", "warning");
      throw new Error("Unauthorized");
    }
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `HTTP Error ${res.status}`);
    }
    return await res.json();
  } catch (err) {
    if (err.message !== "Unauthorized") {
      showToast(err.message, "error");
    }
    throw err;
  }
}

/* ==========================================================================
   THEME TOGGLE
   ========================================================================== */
function initTheme() {
  const html = document.documentElement;
  const themeIcon = document.getElementById("themeIcon");

  if (STATE.theme === "dark") {
    html.classList.add("dark");
    if (themeIcon) themeIcon.textContent = "☀️";
  } else {
    html.classList.remove("dark");
    if (themeIcon) themeIcon.textContent = "🌙";
  }

  const toggleBtn = document.getElementById("themeToggleBtn");
  if (toggleBtn) {
    toggleBtn.addEventListener("click", () => {
      if (html.classList.contains("dark")) {
        html.classList.remove("dark");
        STATE.theme = "light";
        if (themeIcon) themeIcon.textContent = "🌙";
      } else {
        html.classList.add("dark");
        STATE.theme = "dark";
        if (themeIcon) themeIcon.textContent = "☀️";
      }
      localStorage.setItem("indic_theme", STATE.theme);
      // Re-render charts for dark theme grid contrast
      updateChartsTheme();
    });
  }
}

function updateChartsTheme() {
  const isDark = document.documentElement.classList.contains("dark");
  const textColor = isDark ? "#94a3b8" : "#64748b";
  Chart.defaults.color = textColor;
  // Trigger redraw if on dashboard
  if (STATE.activePage === "dashboard") {
    loadDashboardData();
  }
}

/* ==========================================================================
   AUTH CONTROLLER
   ========================================================================== */
function initAuth() {
  const tabLoginBtn = document.getElementById("tabLoginBtn");
  const tabRegisterBtn = document.getElementById("tabRegisterBtn");
  const loginForm = document.getElementById("loginForm");
  const registerForm = document.getElementById("registerForm");
  const quickDemoBtn = document.getElementById("quickDemoBtn");
  const logoutBtn = document.getElementById("logoutBtn");

  // Tab switching
  tabLoginBtn.addEventListener("click", () => {
    tabLoginBtn.className =
      "flex-1 pb-3 text-sm font-semibold text-brand-600 border-b-2 border-brand-600 transition-colors";
    tabRegisterBtn.className =
      "flex-1 pb-3 text-sm font-semibold text-slate-400 border-b-2 border-transparent hover:text-slate-600 transition-colors";
    loginForm.classList.remove("hidden");
    registerForm.classList.add("hidden");
  });

  tabRegisterBtn.addEventListener("click", () => {
    tabRegisterBtn.className =
      "flex-1 pb-3 text-sm font-semibold text-brand-600 border-b-2 border-brand-600 transition-colors";
    tabLoginBtn.className =
      "flex-1 pb-3 text-sm font-semibold text-slate-400 border-b-2 border-transparent hover:text-slate-600 transition-colors";
    registerForm.classList.remove("hidden");
    loginForm.classList.add("hidden");
  });

  // Login Submit
  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = document.getElementById("loginEmail").value.trim();
    const password = document.getElementById("loginPassword").value;
    await doLogin(email, password);
  });

  // Quick Demo Access
  quickDemoBtn.addEventListener("click", async () => {
    document.getElementById("loginEmail").value = "demo@example.com";
    document.getElementById("loginPassword").value = "demo1234";
    await doLogin("demo@example.com", "demo1234");
  });

  // Register Submit
  registerForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const org_name = document.getElementById("regOrg").value.trim();
    const email = document.getElementById("regEmail").value.trim();
    const password = document.getElementById("regPassword").value;

    try {
      const res = await apiFetch("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password, org_name }),
      });
      STATE.token = res.access_token;
      STATE.user = res.user;
      localStorage.setItem("indic_token", STATE.token);
      localStorage.setItem("indic_user", JSON.stringify(STATE.user));
      showToast("Account created successfully!", "success");
      enterApp();
    } catch {
      // Handled in apiFetch
    }
  });

  // Logout
  logoutBtn.addEventListener("click", () => {
    logout();
    showToast("Signed out successfully.", "info");
  });
}

async function doLogin(email, password) {
  try {
    const res = await apiFetch("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    STATE.token = res.access_token;
    STATE.user = res.user;
    localStorage.setItem("indic_token", STATE.token);
    localStorage.setItem("indic_user", JSON.stringify(STATE.user));
    showToast("Signed in successfully!", "success");
    enterApp();
  } catch {
    // Handled in apiFetch
  }
}

function logout() {
  STATE.token = null;
  STATE.user = null;
  localStorage.removeItem("indic_token");
  localStorage.removeItem("indic_user");
  document.getElementById("mainApp").classList.add("hidden");
  document.getElementById("authView").classList.remove("hidden");
}

function enterApp() {
  document.getElementById("authView").classList.add("hidden");
  document.getElementById("mainApp").classList.remove("hidden");

  // Update user badge
  if (STATE.user) {
    document.getElementById("userOrgDisplay").textContent =
      STATE.user.org_name || STATE.user.email.split("@")[0];
    document.getElementById("userEmailDisplay").textContent = STATE.user.email;
  }

  loadProducts();
  switchPage("dashboard");
}

/* ==========================================================================
   NAVIGATION ROUTER
   ========================================================================== */
function initNavigation() {
  const navButtons = document.querySelectorAll(".nav-item");
  navButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetPage = btn.getAttribute("data-page");
      switchPage(targetPage);
    });
  });

  const quickAnalyzeBtn = document.getElementById("quickAnalyzeNavBtn");
  if (quickAnalyzeBtn) {
    quickAnalyzeBtn.addEventListener("click", () => switchPage("analyze"));
  }
}

function switchPage(pageKey) {
  STATE.activePage = pageKey;

  // Update sidebar active link styling
  document.querySelectorAll(".nav-item").forEach((btn) => {
    const isTarget = btn.getAttribute("data-page") === pageKey;
    if (isTarget) {
      btn.className =
        "nav-item w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-colors text-brand-600 bg-brand-50 dark:bg-brand-950/50 dark:text-brand-400";
    } else {
      btn.className =
        "nav-item w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-colors text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800";
    }
  });

  // Hide all views
  const views = [
    "pageDashboard",
    "pageAnalyze",
    "pageBulk",
    "pageReviews",
    "pageInsights",
    "pageReports",
  ];
  views.forEach((v) => {
    const el = document.getElementById(v);
    if (el) el.classList.add("hidden");
  });

  // Show active view & set page title
  const pageMap = {
    dashboard: { id: "pageDashboard", title: "Analytics Dashboard" },
    analyze: { id: "pageAnalyze", title: "Live Multilingual Review Analyzer" },
    bulk: { id: "pageBulk", title: "Bulk Ingestion & Processing" },
    reviews: { id: "pageReviews", title: "Customer Reviews Explorer" },
    insights: { id: "pageInsights", title: "Automated Deep Insights & Trends" },
    reports: { id: "pageReports", title: "Executive PDF Reports & CSV Export" },
  };

  const current = pageMap[pageKey] || pageMap["dashboard"];
  const targetEl = document.getElementById(current.id);
  if (targetEl) targetEl.classList.remove("hidden");
  document.getElementById("pageTitle").textContent = current.title;

  // Trigger page-specific data loaders
  if (pageKey === "dashboard") loadDashboardData();
  else if (pageKey === "reviews") loadReviewsData();
  else if (pageKey === "insights") loadInsightsData();
}

/* ==========================================================================
   PRODUCTS FETCHER & POPULATOR
   ========================================================================== */
async function loadProducts() {
  try {
    const products = await apiFetch("/api/reviews/products");
    STATE.products = products || [];

    // Populate all product select dropdowns
    const selects = [
      document.getElementById("dashProductFilter"),
      document.getElementById("analyzeProductSelect"),
      document.getElementById("revProductFilter"),
    ];

    selects.forEach((sel) => {
      if (!sel) return;
      const currentVal = sel.value;
      sel.innerHTML = `<option value="">All Products</option>`;
      STATE.products.forEach((p) => {
        const opt = document.createElement("option");
        opt.value = p.id;
        opt.textContent = `${p.name} (${p.category})`;
        sel.appendChild(opt);
      });
      sel.value = currentVal;
    });
  } catch (err) {
    console.warn("Could not load products:", err);
  }
}

/* ==========================================================================
   PAGE 1: DASHBOARD
   ========================================================================== */
function initDashboard() {
  const refreshBtn = document.getElementById("refreshDashBtn");
  const productFilter = document.getElementById("dashProductFilter");
  const langFilter = document.getElementById("dashLanguageFilter");
  const trendInterval = document.getElementById("trendIntervalSelect");

  refreshBtn.addEventListener("click", () => loadDashboardData());
  productFilter.addEventListener("change", () => loadDashboardData());
  langFilter.addEventListener("change", () => loadDashboardData());
  trendInterval.addEventListener("change", () => loadTrendChart());
}

async function loadDashboardData() {
  const productId = document.getElementById("dashProductFilter").value;
  const language = document.getElementById("dashLanguageFilter").value;

  const queryParams = new URLSearchParams();
  if (productId) queryParams.set("product_id", productId);
  if (language && language !== "all") queryParams.set("language", language);

  try {
    // 1. Summary KPI
    const summary = await apiFetch(`/api/analytics/summary?${queryParams.toString()}`);
    document.getElementById("kpiTotalReviews").textContent = summary.total_reviews.toLocaleString();
    document.getElementById("kpiLanguagesCount").textContent = `Across ${summary.total_languages} language(s)`;
    document.getElementById("kpiPosPct").textContent = `${summary.positive_pct}%`;
    document.getElementById("kpiPosCount").textContent = `${summary.positive_count} reviews`;
    document.getElementById("kpiNegPct").textContent = `${summary.negative_pct}%`;
    document.getElementById("kpiNegCount").textContent = `${summary.negative_count} reviews`;
    document.getElementById("kpiNeuPct").textContent = `${summary.neutral_pct}%`;
    document.getElementById("kpiNeuCount").textContent = `${summary.neutral_count} reviews`;
    document.getElementById("kpiNpsScore").textContent = `${summary.nps_score >= 0 ? "+" : ""}${summary.nps_score}`;
    document.getElementById("kpiAvgConfidence").textContent = `Avg Confidence: ${Math.round(summary.average_confidence * 100)}%`;

    // 2. Charts
    loadDonutChart(queryParams);
    loadLanguageChart();
    loadTrendChart();
    loadAspectsChart();
    loadTopProductsTable();
  } catch (err) {
    console.error("Dashboard error:", err);
  }
}

async function loadDonutChart(queryParams) {
  const data = await apiFetch(`/api/analytics/distribution?${queryParams.toString()}`);
  const ctx = document.getElementById("sentimentDonutChart").getContext("2d");

  if (STATE.charts.donut) STATE.charts.donut.destroy();

  STATE.charts.donut = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: data.map((d) => d.sentiment),
      datasets: [
        {
          data: data.map((d) => d.count),
          backgroundColor: ["#10b981", "#ef4444", "#64748b"],
          borderWidth: 2,
          borderColor: document.documentElement.classList.contains("dark") ? "#0f172a" : "#ffffff",
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "bottom" },
      },
      cutout: "70%",
    },
  });
}

async function loadLanguageChart() {
  const data = await apiFetch("/api/analytics/by-language");
  const ctx = document.getElementById("languageStackedChart").getContext("2d");

  if (STATE.charts.lang) STATE.charts.lang.destroy();

  STATE.charts.lang = new Chart(ctx, {
    type: "bar",
    data: {
      labels: data.map((d) => d.language),
      datasets: [
        {
          label: "Positive",
          data: data.map((d) => d.positive),
          backgroundColor: "#10b981",
        },
        {
          label: "Negative",
          data: data.map((d) => d.negative),
          backgroundColor: "#ef4444",
        },
        {
          label: "Neutral",
          data: data.map((d) => d.neutral),
          backgroundColor: "#64748b",
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { stacked: true },
        y: { stacked: true },
      },
      plugins: {
        legend: { position: "top" },
      },
    },
  });
}

async function loadTrendChart() {
  const interval = document.getElementById("trendIntervalSelect").value;
  const data = await apiFetch(`/api/analytics/trend?interval=${interval}`);
  const ctx = document.getElementById("trendLineChart").getContext("2d");

  if (STATE.charts.trend) STATE.charts.trend.destroy();

  STATE.charts.trend = new Chart(ctx, {
    type: "line",
    data: {
      labels: data.map((d) => d.date),
      datasets: [
        {
          label: "Positive",
          data: data.map((d) => d.positive),
          borderColor: "#10b981",
          backgroundColor: "rgba(16, 185, 129, 0.1)",
          fill: true,
          tension: 0.3,
        },
        {
          label: "Negative",
          data: data.map((d) => d.negative),
          borderColor: "#ef4444",
          backgroundColor: "rgba(239, 68, 68, 0.1)",
          fill: true,
          tension: 0.3,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "top" },
      },
    },
  });
}

async function loadAspectsChart() {
  const data = await apiFetch("/api/analytics/aspects");
  const ctx = document.getElementById("aspectsBarChart").getContext("2d");

  if (STATE.charts.aspects) STATE.charts.aspects.destroy();

  STATE.charts.aspects = new Chart(ctx, {
    type: "bar",
    data: {
      labels: data.map((d) => d.aspect.toUpperCase()),
      datasets: [
        {
          label: "Positive %",
          data: data.map((d) => d.positive_pct),
          backgroundColor: "#10b981",
        },
        {
          label: "Negative %",
          data: data.map((d) => d.negative_pct),
          backgroundColor: "#ef4444",
        },
      ],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { max: 100 },
      },
      plugins: {
        legend: { position: "top" },
      },
    },
  });
}

async function loadTopProductsTable() {
  const data = await apiFetch("/api/analytics/by-product");
  const tbody = document.getElementById("topProductsTableBody");
  tbody.innerHTML = "";

  data.forEach((p) => {
    const tr = document.createElement("tr");
    tr.className = "hover:bg-slate-50/50 dark:hover:bg-slate-800/40 transition-colors";
    tr.innerHTML = `
      <td class="py-3 px-4 font-bold text-slate-900 dark:text-slate-100">${p.product_name}</td>
      <td class="py-3 px-4 text-slate-500">${p.category}</td>
      <td class="py-3 px-4 font-medium">${p.total_reviews}</td>
      <td class="py-3 px-4 font-bold ${p.positive_pct >= 60 ? "text-emerald-600" : "text-slate-600"}">${p.positive_pct}%</td>
      <td class="py-3 px-4 font-extrabold ${p.nps_score >= 0 ? "text-indigo-600 dark:text-indigo-400" : "text-rose-600"}">${p.nps_score >= 0 ? "+" : ""}${p.nps_score}</td>
      <td class="py-3 px-4">
        <div class="flex items-center gap-1.5 w-32">
          <div class="h-2 rounded-full bg-emerald-500" style="width: ${p.positive_pct}%"></div>
          <div class="h-2 rounded-full bg-rose-500" style="width: ${100 - p.positive_pct}%"></div>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

/* ==========================================================================
   PAGE 2: LIVE ANALYZER
   ========================================================================== */
function initAnalyzer() {
  const input = document.getElementById("analyzeInputText");
  const charCount = document.getElementById("charCount");
  const submitBtn = document.getElementById("analyzeSubmitBtn");
  const clearBtn = document.getElementById("analyzeClearBtn");
  const spinner = document.getElementById("analyzeSpinner");
  const resultPanel = document.getElementById("analyzeResultPanel");
  const presetsContainer = document.getElementById("presetButtonsContainer");
  const saveCheckbox = document.getElementById("analyzeSaveCheckbox");
  const productSelect = document.getElementById("analyzeProductSelect");

  // Populate presets
  presetsContainer.innerHTML = "";
  ANALYZE_PRESETS.forEach((preset) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className =
      "px-2.5 py-1 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/60 hover:border-brand-500 hover:text-brand-600 text-[11px] font-medium transition-all";
    btn.textContent = preset.lang;
    btn.addEventListener("click", () => {
      input.value = preset.text;
      charCount.textContent = `${preset.text.length} characters`;
    });
    presetsContainer.appendChild(btn);
  });

  input.addEventListener("input", () => {
    charCount.textContent = `${input.value.length} characters`;
  });

  saveCheckbox.addEventListener("change", () => {
    if (saveCheckbox.checked) productSelect.classList.remove("hidden");
    else productSelect.classList.add("hidden");
  });

  clearBtn.addEventListener("click", () => {
    input.value = "";
    charCount.textContent = "0 characters";
    resultPanel.classList.add("hidden");
  });

  submitBtn.addEventListener("click", async () => {
    const text = input.value.trim();
    if (!text) {
      showToast("Please enter a review text to analyze.", "warning");
      return;
    }

    spinner.classList.remove("hidden");
    submitBtn.disabled = true;

    try {
      const payload = {
        review: text,
        save: saveCheckbox.checked,
        product_id: saveCheckbox.checked && productSelect.value ? parseInt(productSelect.value) : null,
      };

      const res = await apiFetch("/api/reviews/analyze", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      // Render Results
      resultPanel.classList.remove("hidden");
      renderAnalysisResult(res);
      showToast("Review analyzed successfully!", "success");
    } catch {
      // Handled in apiFetch
    } finally {
      spinner.classList.add("hidden");
      submitBtn.disabled = false;
    }
  });
}

function renderAnalysisResult(res) {
  // Sentiment badge
  const badge = document.getElementById("resSentimentBadge");
  badge.textContent = res.sentiment;
  if (res.sentiment === "Positive") {
    badge.className = "px-3 py-1 rounded-full text-xs font-bold uppercase badge-pos";
  } else if (res.sentiment === "Negative") {
    badge.className = "px-3 py-1 rounded-full text-xs font-bold uppercase badge-neg";
  } else {
    badge.className = "px-3 py-1 rounded-full text-xs font-bold uppercase badge-neu";
  }

  // Summary pills
  document.getElementById("resLanguage").textContent = res.language;
  document.getElementById("resScript").textContent = res.script + (res.is_romanized ? " (Romanized)" : "");
  document.getElementById("resCodeMixed").textContent = res.is_code_mixed ? "Yes" : "No";
  document.getElementById("resConfidence").textContent = `${Math.round(res.confidence * 100)}%`;

  // Transliteration Box
  const translitBox = document.getElementById("resTransliterationBox");
  if (res.is_romanized && res.transliterated_text) {
    translitBox.classList.remove("hidden");
    document.getElementById("resTransliteratedText").textContent = res.transliterated_text;
  } else {
    translitBox.classList.add("hidden");
  }

  // Probabilities Bars
  const pPos = Math.round(res.prob_pos * 100);
  const pNeg = Math.round(res.prob_neg * 100);
  const pNeu = Math.round(res.prob_neu * 100);

  document.getElementById("resProbPos").textContent = `${pPos}%`;
  document.getElementById("resBarPos").style.width = `${pPos}%`;

  document.getElementById("resProbNeg").textContent = `${pNeg}%`;
  document.getElementById("resBarNeg").style.width = `${pNeg}%`;

  document.getElementById("resProbNeu").textContent = `${pNeu}%`;
  document.getElementById("resBarNeu").style.width = `${pNeu}%`;

  // Aspects
  const aspectsContainer = document.getElementById("resAspectsTags");
  aspectsContainer.innerHTML = "";
  if (res.aspects && res.aspects.length > 0) {
    res.aspects.forEach((asp) => {
      const tag = document.createElement("span");
      tag.className =
        "px-2.5 py-1 rounded-lg text-xs font-semibold bg-indigo-50 dark:bg-indigo-950/60 text-brand-600 dark:text-indigo-400 border border-indigo-100 dark:border-indigo-900";
      tag.textContent = `#${asp.toUpperCase()}`;
      aspectsContainer.appendChild(tag);
    });
  } else {
    aspectsContainer.innerHTML = `<span class="text-xs text-slate-400 italic">No specific domain aspects detected</span>`;
  }
}

/* ==========================================================================
   PAGE 3: BULK UPLOAD
   ========================================================================== */
function initBulkUpload() {
  const dropZone = document.getElementById("dropZone");
  const fileInput = document.getElementById("bulkFileInput");
  const fileInfoBox = document.getElementById("fileInfoBox");
  const fileName = document.getElementById("fileName");
  const fileSize = document.getElementById("fileSize");
  const removeFileBtn = document.getElementById("removeFileBtn");
  const submitBtn = document.getElementById("bulkSubmitBtn");
  const progressContainer = document.getElementById("bulkProgressContainer");
  const progressBar = document.getElementById("bulkProgressBar");
  const progressPct = document.getElementById("bulkProgressPct");
  const resultsBanner = document.getElementById("bulkResultsBanner");

  let selectedFile = null;

  dropZone.addEventListener("click", () => fileInput.click());

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("border-brand-500", "bg-indigo-50/20");
  });

  dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("border-brand-500", "bg-indigo-50/20");
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("border-brand-500", "bg-indigo-50/20");
    if (e.dataTransfer.files.length) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files.length) {
      handleFileSelected(e.target.files[0]);
    }
  });

  function handleFileSelected(file) {
    if (!file.name.endsWith(".csv")) {
      showToast("Please select a valid CSV file.", "error");
      return;
    }
    selectedFile = file;
    fileName.textContent = file.name;
    fileSize.textContent = `(${Math.round(file.size / 1024)} KB)`;
    fileInfoBox.classList.remove("hidden");
    submitBtn.disabled = false;
  }

  removeFileBtn.addEventListener("click", () => {
    selectedFile = null;
    fileInput.value = "";
    fileInfoBox.classList.add("hidden");
    submitBtn.disabled = true;
  });

  submitBtn.addEventListener("click", async () => {
    if (!selectedFile) return;

    submitBtn.disabled = true;
    progressContainer.classList.remove("hidden");
    progressBar.style.width = "40%";
    progressPct.textContent = "40%";

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      progressBar.style.width = "75%";
      progressPct.textContent = "75%";

      const res = await apiFetch("/api/reviews/bulk", {
        method: "POST",
        body: formData,
        isFormData: true,
      });

      progressBar.style.width = "100%";
      progressPct.textContent = "100%";

      // Render results
      resultsBanner.classList.remove("hidden");
      document.getElementById("bResTotal").textContent = res.total_rows;
      document.getElementById("bResSaved").textContent = res.saved_count;
      document.getElementById("bResSkipped").textContent = res.skipped_count;
      document.getElementById("bResAvgConf").textContent = `${Math.round(res.average_confidence * 100)}%`;

      if (res.skipped_count > 0 && res.skipped_rows.length > 0) {
        document.getElementById("skippedRowsContainer").classList.remove("hidden");
        document.getElementById("skippedRowsList").textContent = JSON.stringify(res.skipped_rows, null, 2);
      }

      showToast(`Processed ${res.saved_count} reviews successfully!`, "success");
    } catch {
      // Handled in apiFetch
    } finally {
      setTimeout(() => {
        progressContainer.classList.add("hidden");
        submitBtn.disabled = false;
      }, 1000);
    }
  });
}

/* ==========================================================================
   PAGE 4: REVIEWS EXPLORER
   ========================================================================== */
function initReviewsExplorer() {
  const searchInput = document.getElementById("revSearchInput");
  const sentimentFilter = document.getElementById("revSentimentFilter");
  const langFilter = document.getElementById("revLangFilter");
  const productFilter = document.getElementById("revProductFilter");
  const prevBtn = document.getElementById("prevPageBtn");
  const nextBtn = document.getElementById("nextPageBtn");

  let searchTimeout;
  searchInput.addEventListener("input", () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      STATE.reviewsPage = 1;
      loadReviewsData();
    }, 350);
  });

  sentimentFilter.addEventListener("change", () => {
    STATE.reviewsPage = 1;
    loadReviewsData();
  });
  langFilter.addEventListener("change", () => {
    STATE.reviewsPage = 1;
    loadReviewsData();
  });
  productFilter.addEventListener("change", () => {
    STATE.reviewsPage = 1;
    loadReviewsData();
  });

  prevBtn.addEventListener("click", () => {
    if (STATE.reviewsPage > 1) {
      STATE.reviewsPage--;
      loadReviewsData();
    }
  });

  nextBtn.addEventListener("click", () => {
    const maxPage = Math.ceil(STATE.reviewsTotal / STATE.reviewsLimit);
    if (STATE.reviewsPage < maxPage) {
      STATE.reviewsPage++;
      loadReviewsData();
    }
  });

  initCorrectionModal();
}

async function loadReviewsData() {
  const search = document.getElementById("revSearchInput").value.trim();
  const sentiment = document.getElementById("revSentimentFilter").value;
  const language = document.getElementById("revLangFilter").value;
  const productId = document.getElementById("revProductFilter").value;

  const params = new URLSearchParams({
    page: STATE.reviewsPage,
    limit: STATE.reviewsLimit,
  });
  if (search) params.set("search", search);
  if (sentiment && sentiment !== "all") params.set("sentiment", sentiment);
  if (language && language !== "all") params.set("language", language);
  if (productId) params.set("product_id", productId);

  try {
    const res = await apiFetch(`/api/reviews?${params.toString()}`);
    STATE.reviewsTotal = res.total;

    // Pagination info
    const totalPages = Math.ceil(res.total / STATE.reviewsLimit) || 1;
    document.getElementById("reviewsCountDisplay").textContent = `Showing ${res.reviews.length} of ${res.total} reviews`;
    document.getElementById("pageNumberDisplay").textContent = `Page ${res.page} of ${totalPages}`;
    document.getElementById("prevPageBtn").disabled = res.page <= 1;
    document.getElementById("nextPageBtn").disabled = res.page >= totalPages;

    // Table rows
    const tbody = document.getElementById("reviewsTableBody");
    tbody.innerHTML = "";

    if (res.reviews.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" class="text-center py-8 text-slate-400">No reviews found matching the filters.</td></tr>`;
      return;
    }

    res.reviews.forEach((r) => {
      const tr = document.createElement("tr");
      tr.className = "hover:bg-slate-50/50 dark:hover:bg-slate-800/40 transition-colors";

      const badgeClass =
        r.sentiment === "Positive"
          ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-400"
          : r.sentiment === "Negative"
          ? "bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-400"
          : "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-400";

      const dateStr = r.review_date ? new Date(r.review_date).toLocaleDateString() : "-";
      const aspectsList = r.aspects && r.aspects.length > 0 ? r.aspects.map((a) => `<span class="bg-indigo-50 dark:bg-indigo-950/60 text-brand-600 px-1.5 py-0.5 rounded text-[10px] font-medium mr-1">#${a}</span>`).join("") : "-";

      tr.innerHTML = `
        <td class="py-3 px-4 font-mono text-slate-400">${r.id}</td>
        <td class="py-3 px-4 font-semibold text-slate-700 dark:text-slate-300 truncate max-w-[140px]">${r.product_name || "-"}</td>
        <td class="py-3 px-4 max-w-sm">
          <div class="font-medium text-slate-900 dark:text-slate-100 line-clamp-2">${r.original_text}</div>
          ${r.is_romanized && r.transliterated_text ? `<div class="text-[11px] text-indigo-600 dark:text-indigo-400 mt-0.5 italic truncate">Native: ${r.transliterated_text}</div>` : ""}
        </td>
        <td class="py-3 px-4">
          <span class="inline-block px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">${r.language}</span>
        </td>
        <td class="py-3 px-4">
          <span class="px-2 py-0.5 rounded-full text-[11px] font-bold ${badgeClass}">${r.corrected_label || r.sentiment}</span>
          <div class="text-[10px] text-slate-400 mt-0.5">${Math.round(r.confidence * 100)}% conf</div>
        </td>
        <td class="py-3 px-4">${aspectsList}</td>
        <td class="py-3 px-4 text-slate-500 whitespace-nowrap">${dateStr}</td>
        <td class="py-3 px-4 text-right whitespace-nowrap">
          <button data-action="correct" data-id="${r.id}" class="text-brand-600 hover:text-brand-700 font-semibold text-xs mr-2">Correct</button>
          <button data-action="delete" data-id="${r.id}" class="text-rose-500 hover:text-rose-700 font-semibold text-xs">Delete</button>
        </td>
      `;

      // Event listeners for actions
      tr.querySelector('[data-action="correct"]').addEventListener("click", () => openCorrectionModal(r));
      tr.querySelector('[data-action="delete"]').addEventListener("click", () => deleteReviewItem(r.id));

      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Reviews load error:", err);
  }
}

function initCorrectionModal() {
  const modal = document.getElementById("correctionModal");
  const closeBtn = document.getElementById("closeModalBtn");
  const cancelBtn = document.getElementById("cancelModalBtn");
  const saveBtn = document.getElementById("saveModalBtn");

  closeBtn.addEventListener("click", () => modal.classList.add("hidden"));
  cancelBtn.addEventListener("click", () => modal.classList.add("hidden"));

  saveBtn.addEventListener("click", async () => {
    if (!STATE.selectedReviewForCorrection) return;
    const newSentiment = document.getElementById("modalSentimentSelect").value;

    try {
      await apiFetch(`/api/reviews/${STATE.selectedReviewForCorrection.id}/correct`, {
        method: "PUT",
        body: JSON.stringify({ corrected_label: newSentiment }),
      });
      showToast("Label correction saved for future fine-tuning!", "success");
      modal.classList.add("hidden");
      loadReviewsData();
    } catch {
      // Handled in apiFetch
    }
  });
}

function openCorrectionModal(review) {
  STATE.selectedReviewForCorrection = review;
  document.getElementById("modalReviewSnippet").textContent = `"${review.original_text}"`;
  document.getElementById("modalSentimentSelect").value = review.sentiment;
  document.getElementById("correctionModal").classList.remove("hidden");
}

async function deleteReviewItem(id) {
  if (!confirm("Are you sure you want to delete this review?")) return;
  try {
    await apiFetch(`/api/reviews/${id}`, { method: "DELETE" });
    showToast("Review deleted successfully.", "info");
    loadReviewsData();
  } catch {
    // Handled in apiFetch
  }
}

/* ==========================================================================
   PAGE 5: DEEP INSIGHTS
   ========================================================================== */
function initInsights() {
  const langSelect = document.getElementById("keywordsLangSelect");
  langSelect.addEventListener("change", () => loadKeywordsData());
}

async function loadInsightsData() {
  try {
    // 1. Plain language insights
    const res = await apiFetch("/api/analytics/insights");
    const container = document.getElementById("insightsListContainer");
    container.innerHTML = "";

    res.insights.forEach((insight, idx) => {
      const card = document.createElement("div");
      card.className =
        "p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800 flex items-start gap-3 hover-card";
      card.innerHTML = `
        <span class="flex-shrink-0 w-6 h-6 rounded-full bg-brand-100 dark:bg-brand-950 text-brand-600 flex items-center justify-center font-bold text-xs">${idx + 1}</span>
        <p class="text-xs text-slate-800 dark:text-slate-200 font-medium leading-relaxed">${insight}</p>
      `;
      container.appendChild(card);
    });

    // 2. Keywords
    loadKeywordsData();

    // 3. Low confidence queue
    loadLowConfidenceQueue();
  } catch (err) {
    console.error("Insights load error:", err);
  }
}

async function loadKeywordsData() {
  const lang = document.getElementById("keywordsLangSelect").value;
  try {
    const res = await apiFetch(`/api/analytics/keywords?language=${lang}`);
    const posBox = document.getElementById("posKeywordsContainer");
    const negBox = document.getElementById("negKeywordsContainer");

    posBox.innerHTML = "";
    negBox.innerHTML = "";

    if (res.positive_keywords && res.positive_keywords.length > 0) {
      res.positive_keywords.forEach(([word, count]) => {
        const chip = document.createElement("span");
        chip.className =
          "px-2.5 py-1 rounded-lg text-xs font-semibold bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-400";
        chip.textContent = `${word} (${count})`;
        posBox.appendChild(chip);
      });
    } else {
      posBox.innerHTML = `<span class="text-xs text-slate-400">No positive keywords detected</span>`;
    }

    if (res.negative_keywords && res.negative_keywords.length > 0) {
      res.negative_keywords.forEach(([word, count]) => {
        const chip = document.createElement("span");
        chip.className =
          "px-2.5 py-1 rounded-lg text-xs font-semibold bg-rose-100 dark:bg-rose-950/60 text-rose-800 dark:text-rose-400";
        chip.textContent = `${word} (${count})`;
        negBox.appendChild(chip);
      });
    } else {
      negBox.innerHTML = `<span class="text-xs text-slate-400">No negative keywords detected</span>`;
    }
  } catch (err) {
    console.error("Keywords error:", err);
  }
}

async function loadLowConfidenceQueue() {
  try {
    const items = await apiFetch("/api/analytics/low-confidence?threshold=0.60");
    document.getElementById("lowConfCountBadge").textContent = `${items.length} Pending`;

    const tbody = document.getElementById("lowConfTableBody");
    tbody.innerHTML = "";

    if (items.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="py-6 text-center text-slate-400">✓ All reviews have high model confidence (> 60%).</td></tr>`;
      return;
    }

    items.forEach((item) => {
      const tr = document.createElement("tr");
      tr.className = "hover:bg-slate-50/50 dark:hover:bg-slate-800/40 transition-colors";
      tr.innerHTML = `
        <td class="py-3 px-4 font-medium text-slate-800 dark:text-slate-200 max-w-sm">${item.original_text}</td>
        <td class="py-3 px-4 font-semibold text-slate-500">${item.language}</td>
        <td class="py-3 px-4 font-bold text-amber-600">${item.sentiment}</td>
        <td class="py-3 px-4 font-semibold">${Math.round(item.confidence * 100)}%</td>
        <td class="py-3 px-4 text-right">
          <button class="px-2.5 py-1 rounded-lg bg-brand-600 hover:bg-brand-700 text-white font-semibold text-xs shadow-sm">Review & Correct</button>
        </td>
      `;

      tr.querySelector("button").addEventListener("click", () => openCorrectionModal(item));
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Low confidence load error:", err);
  }
}

/* ==========================================================================
   PAGE 6: REPORTS & EXPORT
   ========================================================================== */
function initReports() {
  const downloadPdfBtn = document.getElementById("downloadPdfBtn");
  const downloadCsvBtn = document.getElementById("downloadCsvBtn");

  downloadPdfBtn.addEventListener("click", async () => {
    downloadPdfBtn.disabled = true;
    showToast("Generating PDF report via ReportLab...", "info");

    const lang = document.getElementById("reportPdfLang").value;
    const query = new URLSearchParams();
    if (lang && lang !== "all") query.set("language", lang);

    try {
      const res = await fetch(`/api/reports/pdf?${query.toString()}`, {
        headers: { Authorization: `Bearer ${STATE.token}` },
      });
      if (!res.ok) throw new Error("Could not generate PDF report.");

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `sentiment_analytics_report_${Date.now()}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      showToast("PDF report downloaded successfully!", "success");
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      downloadPdfBtn.disabled = false;
    }
  });

  downloadCsvBtn.addEventListener("click", async () => {
    downloadCsvBtn.disabled = true;
    showToast("Exporting dataset CSV...", "info");

    const sent = document.getElementById("reportCsvSentiment").value;
    const query = new URLSearchParams();
    if (sent && sent !== "all") query.set("sentiment", sent);

    try {
      const res = await fetch(`/api/reviews/export?${query.toString()}`, {
        headers: { Authorization: `Bearer ${STATE.token}` },
      });
      if (!res.ok) throw new Error("Could not export reviews.");

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `reviews_export_${Date.now()}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      showToast("CSV exported successfully!", "success");
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      downloadCsvBtn.disabled = false;
    }
  });
}

/* ==========================================================================
   APP INITIALIZATION
   ========================================================================== */
document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initAuth();
  initNavigation();
  initDashboard();
  initAnalyzer();
  initBulkUpload();
  initReviewsExplorer();
  initInsights();
  initReports();

  // If token already in localStorage, verify and enter
  if (STATE.token) {
    apiFetch("/api/auth/me")
      .then((user) => {
        STATE.user = user;
        localStorage.setItem("indic_user", JSON.stringify(user));
        enterApp();
      })
      .catch(() => {
        logout();
      });
  } else {
    logout();
  }
});
