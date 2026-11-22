/**
 * ONLINE SHOPPING BEHAVIOUR & PURCHASE TREND ANALYSIS
 * Pure Client-Side JavaScript Analytics Engine for GitHub Pages
 *
 * Implements:
 * - Ingestion of CSV (via PapaParse) and Excel XLSX (via SheetJS)
 * - Automatic column detection & interactive heuristic re-mapping
 * - Data quality inspection, duplicate purging & median/mode imputation
 * - Dynamic KPI computations from uploaded dataset (zero hardcoding)
 * - Category, product, customer segmentation & payment distribution analysis
 * - Unit 4: Bivariate scatter, Tukey's 3-Group Resistant Line vs OLS, contingency tables & Chi-square
 * - Unit 5: 3-Variable stratified contingency, Pearson/Spearman correlation heatmap, bubble charts
 * - Unit 5: Time-series frequency resampling (D, W, M, Q), rolling moving averages & seasonality
 * - Reactive global filtering (Date range, Categories, Payment methods, Locations)
 * - Exporting to CSV, HTML report, and browser PDF printing
 */

// Global Application State
const AppState = {
  rawDataset: [],
  cleanedDataset: [],
  filteredDataset: [],
  columnTypes: { numerical: [], categorical: [], datetime: [], all: [] },
  mapping: {
    order_id: null,
    customer_id: null,
    order_date: null,
    category: null,
    product_name: null,
    quantity: null,
    unit_price: null,
    discount: null,
    payment_method: null,
    location: null,
    total_amount: null
  },
  cleaningAudit: { originalRows: 0, cleanedRows: 0, removedDuplicates: 0, imputedColumns: [] },
  filters: {
    dateStart: null,
    dateEnd: null,
    selectedCategories: [],
    selectedPayments: [],
    selectedLocation: "All"
  },
  currentView: "view-overview",
  timeSeriesFreq: "M" // D, W, M, Q
};

// =============================================================================
// 1. INITIALIZATION & DATASET INGESTION
// =============================================================================

document.addEventListener("DOMContentLoaded", () => {
  setupNavigation();
  setupUploadHandlers();
  setupFilterEvents();
  loadInitialDataset();
});

/**
 * Loads default dataset on startup:
 * 1. Attempts fetch from assets/data/online_shopping_data.csv (works on GitHub Pages / HTTP server)
 * 2. If fetch fails (e.g. file:// protocol CORS block), uses window.DEFAULT_CSV_TEXT fallback
 */
function loadInitialDataset() {
  updateStatus("Loading default dataset...", "loading");

  fetch("assets/data/online_shopping_data.csv")
    .then(response => {
      if (!response.ok) throw new Error("Network response was not ok");
      return response.text();
    })
    .then(csvText => {
      parseAndProcessCSV(csvText, "online_shopping_data.csv (Bundled)");
    })
    .catch(() => {
      // Fallback to embedded global variable
      if (window.DEFAULT_CSV_TEXT) {
        parseAndProcessCSV(window.DEFAULT_CSV_TEXT, "online_shopping_data.csv (Local Bundled)");
      } else {
        updateStatus("Please upload a CSV or Excel file to begin.", "warning");
      }
    });
}

function updateStatus(message, type = "ready") {
  const statusEl = document.getElementById("status-text");
  const dotEl = document.getElementById("status-dot");
  if (statusEl) statusEl.textContent = message;
  if (dotEl) {
    dotEl.style.backgroundColor = type === "loading" ? "var(--warning)" : type === "warning" ? "var(--danger)" : "var(--success)";
  }
}

// =============================================================================
// 2. FILE PARSING & COLUMN DETECTION
// =============================================================================

function setupUploadHandlers() {
  const fileInput = document.getElementById("file-upload-input");
  const dropzone = document.getElementById("dropzone-container");
  const sampleSelect = document.getElementById("sample-dataset-select");

  if (fileInput) {
    fileInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files[0]) {
        handleUploadedFile(e.target.files[0]);
      }
    });
  }

  if (dropzone) {
    dropzone.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    });
    dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
    dropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        handleUploadedFile(e.dataTransfer.files[0]);
      }
    });
  }

  if (sampleSelect) {
    sampleSelect.addEventListener("change", (e) => {
      const choice = e.target.value;
      if (choice === "primary") {
        loadInitialDataset();
      } else if (choice === "alternative") {
        if (window.ALTERNATIVE_CSV_TEXT) {
          parseAndProcessCSV(window.ALTERNATIVE_CSV_TEXT, "alternative_retail_transactions (Sample)");
        } else {
          fetch("assets/data/alternative_retail_transactions.csv")
            .then(res => res.text())
            .then(txt => parseAndProcessCSV(txt, "alternative_retail_transactions.csv"))
            .catch(err => alert("Error loading sample: " + err));
        }
      }
    });
  }
}

function handleUploadedFile(file) {
  const filename = file.name.toLowerCase();
  updateStatus(`Parsing ${file.name}...`, "loading");

  if (filename.endsWith(".csv") || filename.endsWith(".txt")) {
    Papa.parse(file, {
      header: true,
      dynamicTyping: true,
      skipEmptyLines: true,
      complete: (results) => {
        processParsedRecords(results.data, file.name);
      },
      error: (err) => {
        alert("Failed to parse CSV: " + err.message);
        updateStatus("Upload error", "warning");
      }
    });
  } else if (filename.endsWith(".xlsx") || filename.endsWith(".xls")) {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = new Uint8Array(e.target.result);
        const workbook = XLSX.read(data, { type: "array" });
        const firstSheet = workbook.SheetNames[0];
        const worksheet = workbook.Sheets[firstSheet];
        const records = XLSX.utils.sheet_to_json(worksheet, { defval: null });
        processParsedRecords(records, file.name);
      } catch (err) {
        alert("Error parsing Excel spreadsheet: " + err.message);
        updateStatus("Excel parse error", "warning");
      }
    };
    reader.readAsArrayBuffer(file);
  } else {
    alert("Unsupported file format! Please upload a .csv, .xlsx, or .xls file.");
    updateStatus("Unsupported format", "warning");
  }
}

function parseAndProcessCSV(csvText, sourceName) {
  Papa.parse(csvText, {
    header: true,
    dynamicTyping: true,
    skipEmptyLines: true,
    complete: (results) => {
      processParsedRecords(results.data, sourceName);
    }
  });
}

function processParsedRecords(records, sourceName) {
  if (!records || records.length === 0) {
    alert("Dataset contains no valid records!");
    return;
  }

  AppState.rawDataset = records;
  document.getElementById("current-dataset-label").textContent = `${sourceName} (${records.length.toLocaleString()} rows)`;

  // 1. Detect column types
  detectColumnTypes(records);

  // 2. Auto-map columns with heuristics
  autoMapColumns();

  // 3. Populate Mapping UI
  renderColumnMappingUI();

  // 4. Run Cleaning Pipeline
  runDataCleaningPipeline();

  // 5. Initialize Filters
  initializeFilterControls();

  // 6. Apply Filters & Render Dashboard
  applyFiltersAndRender();

  updateStatus(`Active: ${records.length.toLocaleString()} records`, "ready");
}

function detectColumnTypes(records) {
  const sample = records.slice(0, 100);
  const cols = Object.keys(records[0] || {});
  const numCols = [];
  const catCols = [];
  const dateCols = [];

  cols.forEach(col => {
    let numericCount = 0;
    let dateCount = 0;
    let nonNullCount = 0;

    sample.forEach(row => {
      const val = row[col];
      if (val !== null && val !== undefined && val !== "") {
        nonNullCount++;
        if (typeof val === "number") {
          numericCount++;
        } else if (typeof val === "string") {
          const lower = col.toLowerCase();
          if (lower.includes("date") || lower.includes("time") || lower.includes("timestamp")) {
            dateCount++;
          } else if (!isNaN(Date.parse(val)) && isNaN(Number(val))) {
            dateCount++;
          }
        }
      }
    });

    if (nonNullCount > 0 && numericCount / nonNullCount > 0.6) {
      numCols.push(col);
    } else if (dateCount > 0) {
      dateCols.push(col);
    } else {
      catCols.push(col);
    }
  });

  AppState.columnTypes = { numerical: numCols, categorical: catCols, datetime: dateCols, all: cols };
}

function autoMapColumns() {
  const cols = AppState.columnTypes.all;
  const lowerCols = cols.map(c => ({ original: c, clean: c.toLowerCase().replace(/[\s\-_]/g, "") }));

  function match(keywords) {
    for (const kw of keywords) {
      const found = lowerCols.find(item => item.clean.includes(kw));
      if (found) return found.original;
    }
    return null;
  }

  AppState.mapping = {
    order_id: match(["orderid", "invoiceno", "invoice", "transid", "ordernum", "transaction"]),
    customer_id: match(["customerid", "custid", "userid", "usercode", "clientid", "customer"]),
    order_date: match(["orderdate", "transdate", "date", "timestamp", "invoicedate"]),
    category: match(["category", "department", "prodcategory", "itemgroup", "type"]),
    product_name: match(["productname", "product", "itemname", "description", "itemdescription", "title"]),
    quantity: match(["quantity", "qty", "units", "unitspurchased", "count"]),
    unit_price: match(["unitprice", "price", "itemrate", "rate", "cost"]),
    discount: match(["discount", "discountrate", "markdown", "rebate"]),
    payment_method: match(["paymentmethod", "payment", "channel", "settlementchannel", "paymode"]),
    location: match(["location", "city", "state", "region", "country", "customerlocation", "province"]),
    total_amount: match(["totalamount", "total", "amount", "netsalesvalue", "sales", "revenue", "spend"])
  };

  // Fallbacks if not detected
  if (!AppState.mapping.order_date && AppState.columnTypes.datetime.length > 0) {
    AppState.mapping.order_date = AppState.columnTypes.datetime[0];
  }
  if (!AppState.mapping.category && AppState.columnTypes.categorical.length > 0) {
    AppState.mapping.category = AppState.columnTypes.categorical[0];
  }
  if (!AppState.mapping.total_amount && AppState.columnTypes.numerical.length > 0) {
    AppState.mapping.total_amount = AppState.columnTypes.numerical[AppState.columnTypes.numerical.length - 1];
  }
}

function renderColumnMappingUI() {
  const container = document.getElementById("column-mapping-container");
  if (!container) return;

  const roles = [
    { key: "order_date", label: "Date / Timestamp Column", required: true },
    { key: "total_amount", label: "Total Amount / Revenue", required: true },
    { key: "quantity", label: "Quantity / Units Sold", required: false },
    { key: "unit_price", label: "Unit Price", required: false },
    { key: "category", label: "Product Category", required: true },
    { key: "product_name", label: "Product Name / Description", required: false },
    { key: "customer_id", label: "Customer ID", required: false },
    { key: "payment_method", label: "Payment Method", required: false },
    { key: "location", label: "Customer Location / Region", required: false },
    { key: "discount", label: "Discount Rate", required: false },
    { key: "order_id", label: "Order / Invoice ID", required: false }
  ];

  const cols = ["None", ...AppState.columnTypes.all];

  let html = `<div class="grid-2">`;
  roles.forEach(role => {
    const selected = AppState.mapping[role.key] || "None";
    html += `
      <div class="form-group">
        <label class="form-label">${role.label} ${role.required ? '<span style="color:var(--danger)">*</span>' : ''}</label>
        <select class="form-select mapping-select" data-role="${role.key}">
          ${cols.map(c => `<option value="${c}" ${c === selected ? 'selected' : ''}>${c}</option>`).join("")}
        </select>
      </div>
    `;
  });
  html += `</div>
    <div style="margin-top:16px; display:flex; gap:12px;">
      <button class="btn btn-primary btn-sm" id="btn-apply-mapping">Apply Column Mapping</button>
      <button class="btn btn-secondary btn-sm" id="btn-reset-mapping">Auto-Detect Defaults</button>
    </div>
  `;

  container.innerHTML = html;

  document.getElementById("btn-apply-mapping").addEventListener("click", () => {
    document.querySelectorAll(".mapping-select").forEach(sel => {
      const role = sel.getAttribute("data-role");
      AppState.mapping[role] = sel.value === "None" ? null : sel.value;
    });
    runDataCleaningPipeline();
    initializeFilterControls();
    applyFiltersAndRender();
    alert("Column mappings applied successfully!");
  });

  document.getElementById("btn-reset-mapping").addEventListener("click", () => {
    autoMapColumns();
    renderColumnMappingUI();
    runDataCleaningPipeline();
    applyFiltersAndRender();
  });
}

// =============================================================================
// 3. DATA QUALITY & CLEANING ENGINE
// =============================================================================

function runDataCleaningPipeline() {
  const raw = AppState.rawDataset;
  if (!raw || raw.length === 0) return;

  const dropDuplicates = document.getElementById("clean-dups-toggle") ? document.getElementById("clean-dups-toggle").checked : true;
  const fillMissing = document.getElementById("clean-impute-toggle") ? document.getElementById("clean-impute-toggle").checked : true;

  let cleaned = [];
  const seenRows = new Set();
  let dupCount = 0;

  // 1. Duplicate Detection & De-duplication
  raw.forEach(row => {
    const serialized = JSON.stringify(row);
    if (seenRows.has(serialized)) {
      dupCount++;
      if (!dropDuplicates) cleaned.push({ ...row });
    } else {
      seenRows.add(serialized);
      cleaned.push({ ...row });
    }
  });

  // 2. Numerical Medians & Categorical Modes for Imputation
  const medians = {};
  const modes = {};

  if (fillMissing) {
    AppState.columnTypes.all.forEach(col => {
      const vals = cleaned.map(r => r[col]).filter(v => v !== null && v !== undefined && v !== "");
      if (typeof vals[0] === "number") {
        const sorted = vals.slice().sort((a, b) => a - b);
        const mid = Math.floor(sorted.length / 2);
        medians[col] = sorted.length % 2 === 0 ? (sorted[mid - 1] + sorted[mid]) / 2 : sorted[mid];
      } else {
        const freq = {};
        vals.forEach(v => { freq[v] = (freq[v] || 0) + 1; });
        let best = "Unknown", bestCount = -1;
        for (const k in freq) {
          if (freq[k] > bestCount) { bestCount = freq[k]; best = k; }
        }
        modes[col] = best;
      }
    });
  }

  // 3. Apply Imputations & Datetime Parsing
  const dateCol = AppState.mapping.order_date;
  const amtCol = AppState.mapping.total_amount;
  const qtyCol = AppState.mapping.quantity;
  const priceCol = AppState.mapping.unit_price;
  const discCol = AppState.mapping.discount;

  cleaned = cleaned.map(row => {
    const newRow = { ...row };

    // Missing value imputation
    if (fillMissing) {
      AppState.columnTypes.all.forEach(col => {
        if (newRow[col] === null || newRow[col] === undefined || newRow[col] === "") {
          newRow[col] = medians[col] !== undefined ? medians[col] : (modes[col] !== undefined ? modes[col] : null);
        }
      });
    }

    // Datetime conversion
    if (dateCol && newRow[dateCol]) {
      let dt;
      // Handle Excel serial dates if numeric
      if (typeof newRow[dateCol] === "number" && newRow[dateCol] > 20000 && newRow[dateCol] < 60000) {
        dt = new Date(Math.round((newRow[dateCol] - 25569) * 86400 * 1000));
      } else {
        dt = new Date(newRow[dateCol]);
      }

      if (!isNaN(dt.getTime())) {
        newRow.__parsedDate = dt;
        newRow.__year = dt.getFullYear();
        newRow.__month = dt.getMonth() + 1;
        newRow.__monthYear = `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, "0")}`;
        newRow.__monthName = dt.toLocaleString("en-US", { month: "short" });
        newRow.__quarter = `Q${Math.floor(dt.getMonth() / 3) + 1} ${dt.getFullYear()}`;
        newRow.__dayOfWeek = dt.toLocaleString("en-US", { weekday: "long" });
        newRow.__hour = dt.getHours();
      }
    }

    // Math validation of Total Amount if missing
    if (amtCol) {
      if (newRow[amtCol] === null || isNaN(newRow[amtCol])) {
        if (qtyCol && priceCol && newRow[qtyCol] && newRow[priceCol]) {
          const d = discCol && newRow[discCol] ? Number(newRow[discCol]) : 0;
          newRow[amtCol] = Math.round(Number(newRow[qtyCol]) * Number(newRow[priceCol]) * (1 - d) * 100) / 100;
        } else {
          newRow[amtCol] = medians[amtCol] || 0;
        }
      } else {
        newRow[amtCol] = Number(newRow[amtCol]);
      }
    }

    return newRow;
  });

  AppState.cleanedDataset = cleaned;
  AppState.cleaningAudit = {
    originalRows: raw.length,
    cleanedRows: cleaned.length,
    removedDuplicates: dupCount,
    imputedColumns: Object.keys(medians).concat(Object.keys(modes))
  };

  renderDataQualityAudit();
}

function renderDataQualityAudit() {
  const audit = AppState.cleaningAudit;
  const raw = AppState.rawDataset;

  const totalMissing = AppState.columnTypes.all.reduce((acc, col) => {
    return acc + raw.filter(r => r[col] === null || r[col] === undefined || r[col] === "").length;
  }, 0);

  // Render KPIs in Quality view
  document.getElementById("qual-raw-rows").textContent = audit.originalRows.toLocaleString();
  document.getElementById("qual-clean-rows").textContent = audit.cleanedRows.toLocaleString();
  document.getElementById("qual-duplicates").textContent = audit.removedDuplicates.toLocaleString();
  document.getElementById("qual-missing-cells").textContent = totalMissing.toLocaleString();

  // Missing values table
  const tbody = document.getElementById("missing-table-body");
  if (tbody) {
    let rowsHtml = "";
    AppState.columnTypes.all.forEach(col => {
      const missCount = raw.filter(r => r[col] === null || r[col] === undefined || r[col] === "").length;
      const missPct = ((missCount / audit.originalRows) * 100).toFixed(2);
      const dtype = AppState.columnTypes.numerical.includes(col) ? "Numerical" : (AppState.columnTypes.datetime.includes(col) ? "Datetime" : "Categorical");
      rowsHtml += `
        <tr>
          <td><strong>${col}</strong></td>
          <td>${dtype}</td>
          <td>${missCount.toLocaleString()}</td>
          <td>
            <div style="display:flex; align-items:center; gap:8px;">
              <div style="flex:1; background:#e2e8f0; height:6px; border-radius:3px; overflow:hidden;">
                <div style="width:${missPct}%; background:var(--danger); height:100%;"></div>
              </div>
              <span style="font-size:0.75rem;">${missPct}%</span>
            </div>
          </td>
        </tr>
      `;
    });
    tbody.innerHTML = rowsHtml;
  }
}

// =============================================================================
// 4. GLOBAL FILTERS
// =============================================================================

function setupFilterEvents() {
  const startInput = document.getElementById("filter-date-start");
  const endInput = document.getElementById("filter-date-end");
  const locSelect = document.getElementById("filter-location-select");
  const resetBtn = document.getElementById("btn-reset-filters");

  if (startInput) startInput.addEventListener("change", applyFiltersAndRender);
  if (endInput) endInput.addEventListener("change", applyFiltersAndRender);
  if (locSelect) locSelect.addEventListener("change", applyFiltersAndRender);
  if (resetBtn) resetBtn.addEventListener("click", resetFilters);

  const cleanDupsToggle = document.getElementById("clean-dups-toggle");
  const cleanImputeToggle = document.getElementById("clean-impute-toggle");
  if (cleanDupsToggle) cleanDupsToggle.addEventListener("change", () => { runDataCleaningPipeline(); applyFiltersAndRender(); });
  if (cleanImputeToggle) cleanImputeToggle.addEventListener("change", () => { runDataCleaningPipeline(); applyFiltersAndRender(); });
}

function initializeFilterControls() {
  const data = AppState.cleanedDataset;
  if (!data || data.length === 0) return;

  // 1. Date Range
  const dates = data.map(r => r.__parsedDate).filter(Boolean);
  if (dates.length > 0) {
    const minDate = new Date(Math.min(...dates));
    const maxDate = new Date(Math.max(...dates));

    const startInput = document.getElementById("filter-date-start");
    const endInput = document.getElementById("filter-date-end");
    if (startInput && endInput) {
      startInput.value = minDate.toISOString().split("T")[0];
      startInput.min = minDate.toISOString().split("T")[0];
      startInput.max = maxDate.toISOString().split("T")[0];

      endInput.value = maxDate.toISOString().split("T")[0];
      endInput.min = minDate.toISOString().split("T")[0];
      endInput.max = maxDate.toISOString().split("T")[0];
    }
  }

  // 2. Category Chips
  const catCol = AppState.mapping.category;
  const catContainer = document.getElementById("category-filter-chips");
  if (catCol && catContainer) {
    const cats = [...new Set(data.map(r => r[catCol]).filter(Boolean))].sort();
    AppState.filters.selectedCategories = [...cats];
    catContainer.innerHTML = cats.map(cat => `
      <div class="filter-chip active" data-val="${cat}" onclick="toggleFilterChip(this, 'category')">${cat}</div>
    `).join("");
  }

  // 3. Payment Method Chips
  const payCol = AppState.mapping.payment_method;
  const payContainer = document.getElementById("payment-filter-chips");
  if (payCol && payContainer) {
    const pays = [...new Set(data.map(r => r[payCol]).filter(Boolean))].sort();
    AppState.filters.selectedPayments = [...pays];
    payContainer.innerHTML = pays.map(pay => `
      <div class="filter-chip active" data-val="${pay}" onclick="toggleFilterChip(this, 'payment')">${pay}</div>
    `).join("");
  }

  // 4. Location Dropdown
  const locCol = AppState.mapping.location;
  const locSelect = document.getElementById("filter-location-select");
  if (locCol && locSelect) {
    const locs = [...new Set(data.map(r => r[locCol]).filter(Boolean))].sort();
    locSelect.innerHTML = `<option value="All">All Locations</option>` + locs.map(l => `<option value="${l}">${l}</option>`).join("");
  }
}

function toggleFilterChip(el, filterType) {
  el.classList.toggle("active");
  const val = el.getAttribute("data-val");

  if (filterType === "category") {
    const list = AppState.filters.selectedCategories;
    const idx = list.indexOf(val);
    if (idx >= 0) list.splice(idx, 1);
    else list.push(val);
  } else if (filterType === "payment") {
    const list = AppState.filters.selectedPayments;
    const idx = list.indexOf(val);
    if (idx >= 0) list.splice(idx, 1);
    else list.push(val);
  }

  applyFiltersAndRender();
}

function resetFilters() {
  initializeFilterControls();
  applyFiltersAndRender();
}

function applyFiltersAndRender() {
  let filtered = [...AppState.cleanedDataset];
  const catCol = AppState.mapping.category;
  const payCol = AppState.mapping.payment_method;
  const locCol = AppState.mapping.location;

  // Date filter
  const startInput = document.getElementById("filter-date-start");
  const endInput = document.getElementById("filter-date-end");
  if (startInput && endInput && startInput.value && endInput.value) {
    const startDate = new Date(startInput.value);
    const endDate = new Date(endInput.value);
    endDate.setHours(23, 59, 59, 999);

    filtered = filtered.filter(row => {
      if (!row.__parsedDate) return true;
      return row.__parsedDate >= startDate && row.__parsedDate <= endDate;
    });
  }

  // Category filter
  if (catCol && AppState.filters.selectedCategories.length > 0) {
    filtered = filtered.filter(row => AppState.filters.selectedCategories.includes(row[catCol]));
  }

  // Payment filter
  if (payCol && AppState.filters.selectedPayments.length > 0) {
    filtered = filtered.filter(row => AppState.filters.selectedPayments.includes(row[payCol]));
  }

  // Location filter
  const locSelect = document.getElementById("filter-location-select");
  if (locCol && locSelect && locSelect.value !== "All") {
    filtered = filtered.filter(row => row[locCol] === locSelect.value);
  }

  AppState.filteredDataset = filtered;
  document.getElementById("filtered-records-count").textContent = `${filtered.length.toLocaleString()} / ${AppState.cleanedDataset.length.toLocaleString()}`;

  // Render active view
  renderCurrentView();
}

// =============================================================================
// 5. VIEW NAVIGATION & ROUTING
// =============================================================================

function setupNavigation() {
  const navItems = document.querySelectorAll(".nav-item");
  navItems.forEach(item => {
    item.addEventListener("click", () => {
      navItems.forEach(n => n.classList.remove("active"));
      item.classList.add("active");

      const viewId = item.getAttribute("data-view");
      showView(viewId);
    });
  });

  const menuToggle = document.getElementById("menu-toggle");
  const sidebar = document.querySelector("aside.sidebar");
  if (menuToggle && sidebar) {
    menuToggle.addEventListener("click", () => sidebar.classList.toggle("open"));
  }
}

function showView(viewId) {
  AppState.currentView = viewId;
  document.querySelectorAll(".view-section").forEach(sec => sec.classList.remove("active"));
  const target = document.getElementById(viewId);
  if (target) {
    target.classList.add("active");
    renderCurrentView();
  }
  // Close sidebar on mobile
  const sidebar = document.querySelector("aside.sidebar");
  if (sidebar && window.innerWidth <= 768) sidebar.classList.remove("open");
}

function renderCurrentView() {
  switch (AppState.currentView) {
    case "view-overview":
      renderOverviewView();
      break;
    case "view-preview":
      renderDataPreviewTable();
      break;
    case "view-category":
      renderCategoryProductView();
      break;
    case "view-customer":
      renderCustomerBehaviourView();
      break;
    case "view-payment":
      renderPaymentAnalysisView();
      break;
    case "view-bivariate":
      renderBivariateUnit4View();
      break;
    case "view-multivariate":
      renderMultivariateUnit5View();
      break;
    case "view-timeseries":
      renderTimeSeriesView();
      break;
    case "view-exports":
      // Static export buttons ready
      break;
  }
}

// =============================================================================
// 6. VIEW RENDERERS
// =============================================================================

/**
 * SECTION A: EXECUTIVE OVERVIEW
 */
function renderOverviewView() {
  const data = AppState.filteredDataset;
  const amtCol = AppState.mapping.total_amount;
  const qtyCol = AppState.mapping.quantity;
  const catCol = AppState.mapping.category;
  const custCol = AppState.mapping.customer_id;
  const discCol = AppState.mapping.discount;

  if (!amtCol || data.length === 0) return;

  const totalRev = data.reduce((sum, r) => sum + (Number(r[amtCol]) || 0), 0);
  const totalOrders = data.length;
  const aov = totalOrders > 0 ? totalRev / totalOrders : 0;
  const totalUnits = qtyCol ? data.reduce((sum, r) => sum + (Number(r[qtyCol]) || 0), 0) : totalOrders;
  const uniqueCusts = custCol ? new Set(data.map(r => r[custCol]).filter(Boolean)).size : 0;

  let avgDisc = 0;
  if (discCol) {
    const discs = data.map(r => Number(r[discCol])).filter(v => !isNaN(v));
    if (discs.length > 0) avgDisc = (discs.reduce((a, b) => a + b, 0) / discs.length) * 100;
  }

  // Find top category
  let topCat = "N/A";
  if (catCol) {
    const catTotals = {};
    data.forEach(r => {
      const c = r[catCol] || "Unknown";
      catTotals[c] = (catTotals[c] || 0) + (Number(r[amtCol]) || 0);
    });
    let max = -1;
    for (const c in catTotals) {
      if (catTotals[c] > max) { max = catTotals[c]; topCat = c; }
    }
  }

  // Update Overview KPI cards
  document.getElementById("kpi-total-revenue").textContent = `$${totalRev.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  document.getElementById("kpi-total-orders").textContent = totalOrders.toLocaleString();
  document.getElementById("kpi-aov").textContent = `$${aov.toFixed(2)}`;
  document.getElementById("kpi-total-units").textContent = totalUnits.toLocaleString();
  document.getElementById("kpi-unique-customers").textContent = uniqueCusts.toLocaleString();
  document.getElementById("kpi-avg-discount").textContent = `${avgDisc.toFixed(1)}%`;
  document.getElementById("kpi-top-category").textContent = topCat;

  // Chart 1: Donut Chart Category Revenue
  if (catCol) {
    const catAgg = {};
    data.forEach(r => {
      const c = r[catCol] || "Unknown";
      catAgg[c] = (catAgg[c] || 0) + (Number(r[amtCol]) || 0);
    });
    const labels = Object.keys(catAgg);
    const values = Object.values(catAgg);

    const donutData = [{
      type: "pie",
      hole: 0.5,
      labels: labels,
      values: values,
      textinfo: "label+percent",
      textposition: "inside",
      marker: { colors: ["#1e88e5", "#0ea5e9", "#10b981", "#f59e0b", "#d81b60", "#8b5cf6", "#64748b"] }
    }];
    const layout = {
      title: "Revenue Share by Product Category",
      height: 350,
      margin: { t: 40, b: 20, l: 20, r: 20 },
      showlegend: true
    };
    Plotly.react("chart-overview-donut", donutData, layout, { responsive: true, displayModeBar: false });
  }

  // Chart 2: Monthly Revenue Trajectory
  renderOverviewMonthlyChart();
}

function renderOverviewMonthlyChart() {
  const data = AppState.filteredDataset;
  const amtCol = AppState.mapping.total_amount;
  if (!amtCol) return;

  const monthMap = {};
  data.forEach(r => {
    const my = r.__monthYear || "Unknown";
    monthMap[my] = (monthMap[my] || 0) + (Number(r[amtCol]) || 0);
  });

  const sortedMonths = Object.keys(monthMap).sort();
  const revs = sortedMonths.map(m => Math.round(monthMap[m]));

  // 3-Period Moving Average
  const ma = [];
  for (let i = 0; i < revs.length; i++) {
    if (i < 2) {
      const sub = revs.slice(0, i + 1);
      ma.push(Math.round(sub.reduce((a, b) => a + b, 0) / sub.length));
    } else {
      const sub = revs.slice(i - 2, i + 1);
      ma.push(Math.round(sub.reduce((a, b) => a + b, 0) / 3));
    }
  }

  const traces = [
    {
      x: sortedMonths,
      y: revs,
      type: "bar",
      name: "Monthly Revenue",
      marker: { color: "#1e88e5", opacity: 0.85 }
    },
    {
      x: sortedMonths,
      y: ma,
      type: "scatter",
      mode: "lines+markers",
      name: "3-Month Moving Average",
      line: { color: "#d81b60", width: 3 }
    }
  ];

  const layout = {
    title: "Monthly Revenue Trajectory & 3-Period Moving Average",
    height: 350,
    margin: { t: 40, b: 40, l: 50, r: 20 },
    xaxis: { title: "Month" },
    yaxis: { title: "Revenue ($)" },
    legend: { orientation: "h", y: 1.15 }
  };
  Plotly.react("chart-overview-monthly", traces, layout, { responsive: true, displayModeBar: false });
}

/**
 * SECTION B: DATA PREVIEW & QUALITY TABLE
 */
function renderDataPreviewTable() {
  const data = AppState.filteredDataset;
  const thead = document.getElementById("preview-table-head");
  const tbody = document.getElementById("preview-table-body");
  if (!thead || !tbody || data.length === 0) return;

  const cols = AppState.columnTypes.all;
  thead.innerHTML = `<tr>${cols.map(c => `<th>${c}</th>`).join("")}</tr>`;

  const previewRows = data.slice(0, 50);
  tbody.innerHTML = previewRows.map(row => {
    return `<tr>${cols.map(c => `<td>${row[c] !== null && row[c] !== undefined ? row[c] : '<span style="color:#cbd5e1">null</span>'}</td>`).join("")}</tr>`;
  }).join("");
}

/**
 * SECTION C: CATEGORY & PRODUCT ANALYTICS
 */
function renderCategoryProductView() {
  const data = AppState.filteredDataset;
  const catCol = AppState.mapping.category;
  const amtCol = AppState.mapping.total_amount;
  const qtyCol = AppState.mapping.quantity;
  const prodCol = AppState.mapping.product_name;

  if (!catCol || !amtCol) {
    document.getElementById("category-warning").style.display = "block";
    return;
  }
  document.getElementById("category-warning").style.display = "none";

  // Category Aggregate
  const catStats = {};
  data.forEach(r => {
    const c = r[catCol] || "Unknown";
    if (!catStats[c]) catStats[c] = { revenue: 0, count: 0, units: 0 };
    catStats[c].revenue += Number(r[amtCol]) || 0;
    catStats[c].count += 1;
    if (qtyCol) catStats[c].units += Number(r[qtyCol]) || 0;
  });

  const catNames = Object.keys(catStats).sort((a, b) => catStats[b].revenue - catStats[a].revenue);
  const catRevs = catNames.map(c => Math.round(catStats[c].revenue));
  const catAovs = catNames.map(c => (catStats[c].revenue / catStats[c].count).toFixed(2));

  // Table
  const tbody = document.getElementById("category-summary-tbody");
  if (tbody) {
    const totalRev = catRevs.reduce((a, b) => a + b, 0);
    tbody.innerHTML = catNames.map(c => {
      const share = totalRev > 0 ? ((catStats[c].revenue / totalRev) * 100).toFixed(1) : 0;
      return `
        <tr>
          <td><strong>${c}</strong></td>
          <td>$${catStats[c].revenue.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
          <td>${catStats[c].count.toLocaleString()}</td>
          <td>$${(catStats[c].revenue / catStats[c].count).toFixed(2)}</td>
          <td>${catStats[c].units ? catStats[c].units.toLocaleString() : '-'}</td>
          <td><span class="badge-unit badge-unit-4">${share}%</span></td>
        </tr>
      `;
    }).join("");
  }

  // Chart: Horizontal Bar Revenue
  const traceBar = [{
    type: "bar",
    orientation: "h",
    y: catNames.slice().reverse(),
    x: catRevs.slice().reverse(),
    marker: { color: "#1e88e5" },
    text: catRevs.slice().reverse().map(v => `$${v.toLocaleString()}`),
    textposition: "outside"
  }];
  Plotly.react("chart-category-bar", traceBar, {
    title: "Total Revenue by Category",
    height: 380,
    margin: { t: 40, b: 30, l: 150, r: 60 }
  }, { responsive: true, displayModeBar: false });

  // Chart: AOV by Category
  const traceAov = [{
    type: "bar",
    x: catNames,
    y: catAovs,
    marker: { color: "#0ea5e9" },
    text: catAovs.map(v => `$${v}`),
    textposition: "outside"
  }];
  Plotly.react("chart-category-aov", traceAov, {
    title: "Average Order Value (AOV) by Category",
    height: 380,
    margin: { t: 40, b: 60, l: 50, r: 20 }
  }, { responsive: true, displayModeBar: false });

  // Top 10 Products
  if (prodCol) {
    const prodStats = {};
    data.forEach(r => {
      const p = r[prodCol] || "Unknown";
      prodStats[p] = (prodStats[p] || 0) + (Number(r[amtCol]) || 0);
    });
    const topProds = Object.keys(prodStats).sort((a, b) => prodStats[b] - prodStats[a]).slice(0, 10);
    const topRevs = topProds.map(p => Math.round(prodStats[p]));

    const traceTop = [{
      type: "bar",
      orientation: "h",
      y: topProds.slice().reverse(),
      x: topRevs.slice().reverse(),
      marker: { color: "#10b981" },
      text: topRevs.slice().reverse().map(v => `$${v.toLocaleString()}`),
      textposition: "outside"
    }];
    Plotly.react("chart-top-products", traceTop, {
      title: "Top 10 Products by Gross Revenue",
      height: 420,
      margin: { t: 40, b: 30, l: 240, r: 60 }
    }, { responsive: true, displayModeBar: false });
  }
}

/**
 * SECTION D: CUSTOMER BEHAVIOUR
 */
function renderCustomerBehaviourView() {
  const data = AppState.filteredDataset;
  const custCol = AppState.mapping.customer_id;
  const amtCol = AppState.mapping.total_amount;

  if (!custCol || !amtCol) {
    document.getElementById("customer-warning").style.display = "block";
    return;
  }
  document.getElementById("customer-warning").style.display = "none";

  const custSpend = {};
  const custFreq = {};
  data.forEach(r => {
    const cid = r[custCol];
    if (cid) {
      custSpend[cid] = (custSpend[cid] || 0) + (Number(r[amtCol]) || 0);
      custFreq[cid] = (custFreq[cid] || 0) + 1;
    }
  });

  const spends = Object.values(custSpend).sort((a, b) => a - b);
  const n = spends.length;
  if (n === 0) return;

  const totalCusts = n;
  const repeatCusts = Object.values(custFreq).filter(f => f > 1).length;
  const repeatRate = ((repeatCusts / totalCusts) * 100).toFixed(1);
  const meanSpend = (spends.reduce((a, b) => a + b, 0) / n).toFixed(2);
  const medianSpend = (n % 2 === 0 ? (spends[n/2 - 1] + spends[n/2]) / 2 : spends[Math.floor(n/2)]).toFixed(2);

  document.getElementById("cust-total-count").textContent = totalCusts.toLocaleString();
  document.getElementById("cust-repeat-rate").textContent = `${repeatRate}%`;
  document.getElementById("cust-mean-spend").textContent = `$${meanSpend}`;
  document.getElementById("cust-median-spend").textContent = `$${medianSpend}`;

  // Spend Distribution Histogram
  const traceHist = [{
    type: "histogram",
    x: spends,
    nbinsx: 30,
    marker: { color: "#1e88e5", line: { color: "white", width: 1 } }
  }];
  Plotly.react("chart-customer-histogram", traceHist, {
    title: "Customer Lifetime Spend Distribution",
    xaxis: { title: "Total Lifetime Spend ($)" },
    yaxis: { title: "Customer Count" },
    height: 360,
    margin: { t: 40, b: 40, l: 50, r: 20 }
  }, { responsive: true, displayModeBar: false });

  // Spending Quartiles Segmentation
  const q1 = spends[Math.floor(n * 0.25)];
  const q2 = spends[Math.floor(n * 0.50)];
  const q3 = spends[Math.floor(n * 0.75)];

  const tiers = { "Bronze (Low)": 0, "Silver (Mid)": 0, "Gold (High)": 0, "Platinum (Top)": 0 };
  spends.forEach(s => {
    if (s <= q1) tiers["Bronze (Low)"]++;
    else if (s <= q2) tiers["Silver (Mid)"]++;
    else if (s <= q3) tiers["Gold (High)"]++;
    else tiers["Platinum (Top)"]++;
  });

  const traceTiers = [{
    type: "pie",
    hole: 0.45,
    labels: Object.keys(tiers),
    values: Object.values(tiers),
    marker: { colors: ["#94a3b8", "#38bdf8", "#fbbf24", "#d81b60"] }
  }];
  Plotly.react("chart-customer-tiers", traceTiers, {
    title: "Customer Segmentation by Spend Quartile",
    height: 360,
    margin: { t: 40, b: 20, l: 20, r: 20 }
  }, { responsive: true, displayModeBar: false });
}

/**
 * SECTION E: PAYMENT ANALYSIS
 */
function renderPaymentAnalysisView() {
  const data = AppState.filteredDataset;
  const payCol = AppState.mapping.payment_method;
  const amtCol = AppState.mapping.total_amount;
  const catCol = AppState.mapping.category;

  if (!payCol || !amtCol) {
    document.getElementById("payment-warning").style.display = "block";
    return;
  }
  document.getElementById("payment-warning").style.display = "none";

  const payStats = {};
  data.forEach(r => {
    const p = r[payCol] || "Unknown";
    if (!payStats[p]) payStats[p] = { revenue: 0, count: 0 };
    payStats[p].revenue += Number(r[amtCol]) || 0;
    payStats[p].count += 1;
  });

  const pays = Object.keys(payStats).sort((a, b) => payStats[b].revenue - payStats[a].revenue);
  const totalRev = Object.values(payStats).reduce((a, b) => a + b.revenue, 0);

  // Table
  const tbody = document.getElementById("payment-summary-tbody");
  if (tbody) {
    tbody.innerHTML = pays.map(p => {
      const share = totalRev > 0 ? ((payStats[p].revenue / totalRev) * 100).toFixed(1) : 0;
      return `
        <tr>
          <td><strong>${p}</strong></td>
          <td>$${payStats[p].revenue.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
          <td>${payStats[p].count.toLocaleString()}</td>
          <td>$${(payStats[p].revenue / payStats[p].count).toFixed(2)}</td>
          <td><span class="badge-unit badge-unit-4">${share}%</span></td>
        </tr>
      `;
    }).join("");
  }

  // Chart Donut
  const tracePayDonut = [{
    type: "pie",
    hole: 0.45,
    labels: pays,
    values: pays.map(p => payStats[p].revenue),
    marker: { colors: ["#1e88e5", "#0ea5e9", "#10b981", "#f59e0b", "#d81b60"] }
  }];
  Plotly.react("chart-payment-donut", tracePayDonut, {
    title: "Revenue Share by Payment Method",
    height: 360,
    margin: { t: 40, b: 20, l: 20, r: 20 }
  }, { responsive: true, displayModeBar: false });

  // Contingency Table: Category vs Payment Method
  if (catCol) {
    renderContingencyTable(catCol, payCol);
  }
}

function renderContingencyTable(rowCol, colCol) {
  const data = AppState.filteredDataset;
  const rowVals = [...new Set(data.map(r => r[rowCol]).filter(Boolean))].sort();
  const colVals = [...new Set(data.map(r => r[colCol]).filter(Boolean))].sort();

  const matrix = {};
  rowVals.forEach(r => {
    matrix[r] = {};
    colVals.forEach(c => matrix[r][c] = 0);
  });

  data.forEach(row => {
    const r = row[rowCol];
    const c = row[colCol];
    if (r && c && matrix[r] && matrix[r][c] !== undefined) {
      matrix[r][c]++;
    }
  });

  // Calculate Margins
  const rowTotals = {};
  const colTotals = {};
  let grandTotal = 0;

  rowVals.forEach(r => {
    rowTotals[r] = 0;
    colVals.forEach(c => {
      rowTotals[r] += matrix[r][c];
      colTotals[c] = (colTotals[c] || 0) + matrix[r][c];
      grandTotal += matrix[r][c];
    });
  });

  // Render Table
  const thead = document.getElementById("contingency-thead");
  const tbody = document.getElementById("contingency-tbody");

  if (thead && tbody) {
    thead.innerHTML = `<tr><th>${rowCol} \\ ${colCol}</th>${colVals.map(c => `<th>${c}</th>`).join("")}<th>Total</th></tr>`;
    tbody.innerHTML = rowVals.map(r => {
      return `<tr>
        <td><strong>${r}</strong></td>
        ${colVals.map(c => `<td>${matrix[r][c]}</td>`).join("")}
        <td><strong>${rowTotals[r]}</strong></td>
      </tr>`;
    }).join("") + `
      <tr style="background:#f1f5f9; font-weight:bold;">
        <td>Total</td>
        ${colVals.map(c => `<td>${colTotals[c]}</td>`).join("")}
        <td>${grandTotal}</td>
      </tr>
    `;
  }

  // Chi-Square Test of Independence
  let chi2 = 0;
  rowVals.forEach(r => {
    colVals.forEach(c => {
      const observed = matrix[r][c];
      const expected = (rowTotals[r] * colTotals[c]) / grandTotal;
      if (expected > 0) {
        chi2 += Math.pow(observed - expected, 2) / expected;
      }
    });
  });

  const dof = (rowVals.length - 1) * (colVals.length - 1);
  const pApprox = approxChiSquarePValue(chi2, dof);

  const chiReportEl = document.getElementById("chi-square-report");
  if (chiReportEl) {
    const isSignificant = pApprox < 0.05;
    chiReportEl.innerHTML = `
      <strong>Pearson's Chi-Square Test ($\chi^2$):</strong><br>
      &bull; $\chi^2$ Statistic: <code>${chi2.toFixed(3)}</code> | Degrees of Freedom: <code>${dof}</code> | $p$-value: <code>${pApprox.toExponential(3)}</code><br>
      &bull; <strong>Deduction:</strong> ${isSignificant ?
        `Statistically significant dependency exists between ${rowCol} and ${colCol} (p < 0.05).` :
        `No statistically significant dependency detected between ${rowCol} and ${colCol} (p >= 0.05). Consumer payment choices operate independently of product categories.`}
    `;
  }
}

function approxChiSquarePValue(x, k) {
  if (x <= 0 || k < 1) return 1.0;
  // Wilson-Hilferty transformation approximation for chi-square CDF
  const s = Math.sqrt(2 / (9 * k));
  const z = (Math.pow(x / k, 1/3) - (1 - 2 / (9 * k))) / s;
  // Standard normal upper tail
  return 0.5 * erfc(z / Math.SQRT2);
}

function erfc(x) {
  // Complementary error function
  const z = Math.abs(x);
  const t = 1.0 / (1.0 + 0.5 * z);
  const r = t * Math.exp(-z * z - 1.26551223 + t * (1.00002368 + t * (0.37409196 + t * (0.09678418 + t * (-0.18628806 + t * (0.27886807 + t * (-1.13520398 + t * (1.48851587 + t * (-0.82215223 + t * 0.17087277)))))))));
  return x >= 0 ? r : 2.0 - r;
}

/**
 * SECTION F: UNIT 4 - BIVARIATE & TUKEY'S RESISTANT LINE
 */
function renderBivariateUnit4View() {
  const data = AppState.filteredDataset;
  const numCols = AppState.columnTypes.numerical;

  if (numCols.length < 2) return;

  const selX = document.getElementById("bivariate-x-select");
  const selY = document.getElementById("bivariate-y-select");

  if (selX && selY && selX.children.length === 0) {
    selX.innerHTML = numCols.map(c => `<option value="${c}">${c}</option>`).join("");
    selY.innerHTML = numCols.map(c => `<option value="${c}">${c}</option>`).join("");

    const defX = AppState.mapping.quantity || numCols[0];
    const defY = AppState.mapping.total_amount || numCols[numCols.length - 1];
    selX.value = defX;
    selY.value = defY;

    selX.addEventListener("change", updateBivariateCharts);
    selY.addEventListener("change", updateBivariateCharts);
  }

  updateBivariateCharts();
}

function updateBivariateCharts() {
  const data = AppState.filteredDataset;
  const selX = document.getElementById("bivariate-x-select");
  const selY = document.getElementById("bivariate-y-select");
  if (!selX || !selY) return;

  const xCol = selX.value;
  const yCol = selY.value;

  const cleanPairs = data.map(r => ({ x: Number(r[xCol]), y: Number(r[yCol]) }))
    .filter(p => !isNaN(p.x) && !isNaN(p.y));

  if (cleanPairs.length < 6) return;

  // 1. Calculate OLS Regression
  const n = cleanPairs.length;
  let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0, sumY2 = 0;
  cleanPairs.forEach(p => {
    sumX += p.x; sumY += p.y;
    sumXY += p.x * p.y;
    sumX2 += p.x * p.x; sumY2 += p.y * p.y;
  });
  const olsSlope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
  const olsIntercept = (sumY - olsSlope * sumX) / n;
  const rNum = (n * sumXY - sumX * sumY);
  const rDenom = Math.sqrt((n * sumX2 - sumX * sumX) * (n * sumY2 - sumY * sumY));
  const rVal = rDenom > 0 ? rNum / rDenom : 0;
  const r2 = Math.pow(rVal, 2);

  // 2. Calculate Tukey's 3-Group Resistant Line
  const sorted = cleanPairs.slice().sort((a, b) => a.x - b.x);
  const q = Math.floor(n / 3);
  const rRem = n % 3;
  let nL = q, nM = q, nR = q;
  if (rRem === 1) nM = q + 1;
  else if (rRem === 2) { nL = q + 1; nR = q + 1; }

  const groupL = sorted.slice(0, nL);
  const groupM = sorted.slice(nL, nL + nM);
  const groupR = sorted.slice(nL + nM);

  function getMedian(arr, key) {
    const vals = arr.map(item => item[key]).sort((a, b) => a - b);
    const m = Math.floor(vals.length / 2);
    return vals.length % 2 === 0 ? (vals[m - 1] + vals[m]) / 2 : vals[m];
  }

  const xL = getMedian(groupL, "x"), yL = getMedian(groupL, "y");
  const xM = getMedian(groupM, "x"), yM = getMedian(groupM, "y");
  const xR = getMedian(groupR, "x"), yR = getMedian(groupR, "y");

  const resSlope = xR !== xL ? (yR - yL) / (xR - xL) : 0;
  const resIntercept = (1 / 3) * ((yL - resSlope * xL) + (yM - resSlope * xM) + (yR - resSlope * xR));

  // Render KPIs
  document.getElementById("ols-equation").textContent = `y = ${olsIntercept.toFixed(2)} + ${olsSlope.toFixed(2)}x (R²=${r2.toFixed(3)})`;
  document.getElementById("resistant-equation").textContent = `y = ${resIntercept.toFixed(2)} + ${resSlope.toFixed(2)}x`;
  document.getElementById("tukey-medians-text").textContent = `L: (${xL.toFixed(1)}, ${yL.toFixed(1)}) | M: (${xM.toFixed(1)}, ${yM.toFixed(1)}) | R: (${xR.toFixed(1)}, ${yR.toFixed(1)})`;

  // Plotly Scatter + Both Lines
  const sampleData = cleanPairs.slice(0, 800);
  const minX = Math.min(...cleanPairs.map(p => p.x));
  const maxX = Math.max(...cleanPairs.map(p => p.x));

  const xLine = [minX, maxX];
  const yLineOls = [olsIntercept + olsSlope * minX, olsIntercept + olsSlope * maxX];
  const yLineRes = [resIntercept + resSlope * minX, resIntercept + resSlope * maxX];

  const traces = [
    {
      x: sampleData.map(p => p.x),
      y: sampleData.map(p => p.y),
      mode: "markers",
      type: "scatter",
      name: "Observed Data",
      marker: { color: "#94a3b8", opacity: 0.5, size: 6 }
    },
    {
      x: [xL, xM, xR],
      y: [yL, yM, yR],
      mode: "markers",
      type: "scatter",
      name: "Tukey 3-Group Medians",
      marker: { color: "#d81b60", size: 14, symbol: "x" }
    },
    {
      x: xLine,
      y: yLineRes,
      mode: "lines",
      name: `Tukey Resistant Line (b=${resSlope.toFixed(2)})`,
      line: { color: "#d81b60", width: 3 }
    },
    {
      x: xLine,
      y: yLineOls,
      mode: "lines",
      name: `OLS Linear Regression (b=${olsSlope.toFixed(2)})`,
      line: { color: "#1e88e5", width: 3, dash: "dash" }
    }
  ];

  Plotly.react("chart-resistant-scatter", traces, {
    title: `Unit 4: Resistant Line vs OLS Regression (${yCol} vs ${xCol})`,
    xaxis: { title: xCol },
    yaxis: { title: yCol },
    height: 480,
    legend: { orientation: "h", y: 1.15 }
  }, { responsive: true, displayModeBar: false });

  // Batch Boxplot
  const catCol = AppState.mapping.category;
  if (catCol) {
    const cats = [...new Set(data.map(r => r[catCol]).filter(Boolean))];
    const boxTraces = cats.map(c => ({
      type: "box",
      name: c,
      y: data.filter(r => r[catCol] === c).map(r => Number(r[yCol])).filter(v => !isNaN(v))
    }));
    Plotly.react("chart-batch-boxplot", boxTraces, {
      title: `Distribution Across Departmental Batches (${yCol} by Category)`,
      height: 420,
      showlegend: false
    }, { responsive: true, displayModeBar: false });
  }
}

/**
 * SECTION G: UNIT 5 - MULTIVARIATE ANALYSIS
 */
function renderMultivariateUnit5View() {
  const data = AppState.filteredDataset;
  const numCols = AppState.columnTypes.numerical;

  // Correlation Matrix
  if (numCols.length >= 2) {
    const matrix = [];
    numCols.forEach(col1 => {
      const row = [];
      numCols.forEach(col2 => {
        row.push(calculatePearsonCorrelation(data, col1, col2));
      });
      matrix.push(row);
    });

    const traceHeatmap = [{
      type: "heatmap",
      z: matrix,
      x: numCols,
      y: numCols,
      colorscale: "RdBu",
      reversescale: true,
      zmin: -1,
      zmax: 1
    }];

    Plotly.react("chart-correlation-heatmap", traceHeatmap, {
      title: "Numerical Attributes Correlation Matrix (Pearson)",
      height: 400,
      margin: { t: 40, b: 60, l: 120, r: 20 }
    }, { responsive: true, displayModeBar: false });
  }

  // Bubble Chart (Multivariate)
  const amtCol = AppState.mapping.total_amount;
  const qtyCol = AppState.mapping.quantity;
  const priceCol = AppState.mapping.unit_price;
  const catCol = AppState.mapping.category;

  if (amtCol && qtyCol && priceCol && catCol) {
    const sample = data.slice(0, 400);
    const traceBubble = [{
      type: "scatter",
      mode: "markers",
      x: sample.map(r => Number(r[priceCol])),
      y: sample.map(r => Number(r[amtCol])),
      text: sample.map(r => `${r[catCol]}: Qty=${r[qtyCol]}`),
      marker: {
        size: sample.map(r => Math.max(6, (Number(r[qtyCol]) || 1) * 5)),
        color: sample.map(r => r[catCol]),
        colorscale: "Viridis",
        opacity: 0.7
      }
    }];

    Plotly.react("chart-multivariate-bubble", traceBubble, {
      title: "Multivariate Interaction: Spend vs Unit Price Sized by Quantity",
      xaxis: { title: "Unit Price ($)" },
      yaxis: { title: "Total Transaction Spend ($)" },
      height: 420,
      margin: { t: 40, b: 40, l: 60, r: 20 }
    }, { responsive: true, displayModeBar: false });
  }
}

function calculatePearsonCorrelation(data, col1, col2) {
  const pairs = data.map(r => ({ x: Number(r[col1]), y: Number(r[col2]) }))
    .filter(p => !isNaN(p.x) && !isNaN(p.y));
  const n = pairs.length;
  if (n < 2) return 0;

  let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0, sumY2 = 0;
  pairs.forEach(p => {
    sumX += p.x; sumY += p.y;
    sumXY += p.x * p.y;
    sumX2 += p.x * p.x; sumY2 += p.y * p.y;
  });
  const denom = Math.sqrt((n * sumX2 - sumX * sumX) * (n * sumY2 - sumY * sumY));
  return denom > 0 ? Math.round(((n * sumXY - sumX * sumY) / denom) * 100) / 100 : 0;
}

/**
 * SECTION H: UNIT 5 - TIME SERIES ANALYSIS
 */
function renderTimeSeriesView() {
  const data = AppState.filteredDataset;
  const amtCol = AppState.mapping.total_amount;
  if (!amtCol) return;

  const validTimeRows = data.filter(r => r.__parsedDate);
  if (validTimeRows.length === 0) return;

  // Granularity selector setup
  const freqRadios = document.querySelectorAll("input[name='ts-freq']");
  freqRadios.forEach(radio => {
    radio.addEventListener("change", (e) => {
      AppState.timeSeriesFreq = e.target.value;
      renderTimeSeriesView();
    });
  });

  const freq = AppState.timeSeriesFreq;
  const agg = {};

  validTimeRows.forEach(r => {
    const dt = r.__parsedDate;
    let key;
    if (freq === "D") {
      key = dt.toISOString().split("T")[0];
    } else if (freq === "W") {
      const year = dt.getFullYear();
      const firstDay = new Date(year, 0, 1);
      const week = Math.ceil((((dt - firstDay) / 86400000) + firstDay.getDay() + 1) / 7);
      key = `${year}-W${String(week).padStart(2, "0")}`;
    } else if (freq === "Q") {
      key = r.__quarter || `${dt.getFullYear()}-Q${Math.floor(dt.getMonth() / 3) + 1}`;
    } else {
      key = r.__monthYear || `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, "0")}`;
    }

    if (!agg[key]) agg[key] = { revenue: 0, count: 0 };
    agg[key].revenue += Number(r[amtCol]) || 0;
    agg[key].count += 1;
  });

  const sortedKeys = Object.keys(agg).sort();
  const revenues = sortedKeys.map(k => Math.round(agg[k].revenue));
  const counts = sortedKeys.map(k => agg[k].count);

  // Moving Average
  const ma = [];
  const windowSize = freq === "D" ? 7 : 3;
  for (let i = 0; i < revenues.length; i++) {
    const start = Math.max(0, i - windowSize + 1);
    const sub = revenues.slice(start, i + 1);
    ma.push(Math.round(sub.reduce((a, b) => a + b, 0) / sub.length));
  }

  // Cumulative
  let cum = 0;
  const cumulative = revenues.map(v => { cum += v; return cum; });

  // Main Resampled Series
  const traces = [
    {
      x: sortedKeys,
      y: revenues,
      mode: "lines+markers",
      name: "Revenue ($)",
      line: { color: "#1e88e5", width: 2.5 },
      marker: { size: 5 }
    },
    {
      x: sortedKeys,
      y: ma,
      mode: "lines",
      name: `${windowSize}-Period Moving Average`,
      line: { color: "#d81b60", width: 2.5, dash: "dash" }
    }
  ];

  Plotly.react("chart-timeseries-main", traces, {
    title: `Time-Series Revenue Analysis (${freq === "D" ? "Daily" : freq === "W" ? "Weekly" : freq === "Q" ? "Quarterly" : "Monthly"} Resampling)`,
    xaxis: { title: "Timeline", rangeslider: { visible: true } },
    yaxis: { title: "Revenue ($)" },
    height: 480,
    legend: { orientation: "h", y: 1.15 }
  }, { responsive: true, displayModeBar: false });

  // Cumulative Area Chart
  const traceCum = [{
    x: sortedKeys,
    y: cumulative,
    type: "scatter",
    fill: "tozeroy",
    name: "Cumulative Revenue",
    line: { color: "#10b981" }
  }];
  Plotly.react("chart-cumulative-area", traceCum, {
    title: "Cumulative Revenue Trajectory",
    height: 350,
    margin: { t: 40, b: 40, l: 60, r: 20 }
  }, { responsive: true, displayModeBar: false });

  // Order Counts Bar Chart
  const traceCount = [{
    x: sortedKeys,
    y: counts,
    type: "bar",
    name: "Orders",
    marker: { color: "#0ea5e9" }
  }];
  Plotly.react("chart-orders-count-bar", traceCount, {
    title: "Transaction Volume by Period",
    height: 350,
    margin: { t: 40, b: 40, l: 50, r: 20 }
  }, { responsive: true, displayModeBar: false });

  // Seasonality: Day of Week
  const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
  const dayTotals = { Monday: 0, Tuesday: 0, Wednesday: 0, Thursday: 0, Friday: 0, Saturday: 0, Sunday: 0 };
  validTimeRows.forEach(r => {
    if (r.__dayOfWeek && dayTotals[r.__dayOfWeek] !== undefined) {
      dayTotals[r.__dayOfWeek] += Number(r[amtCol]) || 0;
    }
  });

  const traceDays = [{
    type: "bar",
    x: days,
    y: days.map(d => Math.round(dayTotals[d])),
    marker: { color: "#8b5cf6" }
  }];
  Plotly.react("chart-seasonality-days", traceDays, {
    title: "Seasonality: Revenue by Day of Week",
    height: 350,
    margin: { t: 40, b: 40, l: 60, r: 20 }
  }, { responsive: true, displayModeBar: false });
}

// =============================================================================
// 7. EXPORT ENGINES (CSV, HTML & PDF PRINT)
// =============================================================================

function exportToCSV(filename, rows) {
  if (!rows || rows.length === 0) {
    alert("No data available to export!");
    return;
  }
  const csv = Papa.unparse(rows);
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function exportCleanedData() {
  exportToCSV("cleaned_ecommerce_transactions.csv", AppState.filteredDataset);
}

function exportCategorySummary() {
  const data = AppState.filteredDataset;
  const catCol = AppState.mapping.category;
  const amtCol = AppState.mapping.total_amount;
  const qtyCol = AppState.mapping.quantity;
  if (!catCol || !amtCol) return;

  const agg = {};
  data.forEach(r => {
    const c = r[catCol] || "Unknown";
    if (!agg[c]) agg[c] = { Category: c, Total_Revenue: 0, Order_Count: 0, Total_Units: 0 };
    agg[c].Total_Revenue += Number(r[amtCol]) || 0;
    agg[c].Order_Count += 1;
    if (qtyCol) agg[c].Total_Units += Number(r[qtyCol]) || 0;
  });

  const rows = Object.values(agg).map(item => ({
    ...item,
    Total_Revenue: item.Total_Revenue.toFixed(2),
    Average_Order_Value: (item.Total_Revenue / item.Order_Count).toFixed(2)
  }));
  exportToCSV("category_sales_summary.csv", rows);
}

function exportMonthlyRevenue() {
  const data = AppState.filteredDataset;
  const amtCol = AppState.mapping.total_amount;
  if (!amtCol) return;

  const agg = {};
  data.forEach(r => {
    const my = r.__monthYear || "Unknown";
    if (!agg[my]) agg[my] = { Month: my, Revenue: 0, Orders: 0 };
    agg[my].Revenue += Number(r[amtCol]) || 0;
    agg[my].Orders += 1;
  });

  const rows = Object.keys(agg).sort().map(m => ({
    Month: m,
    Revenue: agg[m].Revenue.toFixed(2),
    Orders: agg[m].Orders
  }));
  exportToCSV("monthly_revenue_time_series.csv", rows);
}

function printExecutiveReport() {
  window.print();
}
