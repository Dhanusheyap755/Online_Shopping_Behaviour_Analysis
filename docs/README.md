# GitHub Pages Deployment Guide

## Online Shopping Behaviour & Purchase Trend Analysis (Web Dashboard)

This directory contains the standalone, zero-backend, pure client-side web application version of the **Online Shopping Behaviour & Purchase Trend Analysis** project, engineered specifically for 1-click deployment on **GitHub Pages**.

---

## 🚀 How to Deploy on GitHub Pages

You can deploy this dashboard to GitHub Pages in under 2 minutes:

### Step 1: Push Project to GitHub
Initialize your Git repository and push all files to your GitHub repository (e.g. `main` branch):
```bash
git init
git add .
git commit -m "feat: complete online shopping EDA and GitHub Pages web app"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo-name>.git
git push -u origin main
```

### Step 2: Configure GitHub Pages Settings
1. Navigate to your repository on GitHub.
2. Click on **Settings** (top tab bar).
3. In the left navigation menu, under *Code and automation*, click **Pages**.
4. Under **Build and deployment**:
   - **Source**: Select `Deploy from a branch`.
   - **Branch**: Select `main`.
   - **Folder**: Select `/docs` (or `/ (root)` if you host from a dedicated `gh-pages` branch).
5. Click **Save**.

### Step 3: Access Your Live Website
Within 1–2 minutes, GitHub Pages will deploy your dashboard. Your live URL will be:
```
https://<your-username>.github.io/<your-repo-name>/
```

---

## 💻 Running Locally (Offline)

### Method A: Direct Double-Click
You can double-click `index.html` (or `docs/index.html`) in any modern web browser (Chrome, Edge, Firefox, Safari).
The embedded dataset fallback (`assets/data/default_dataset.js`) ensures the application loads the full 12-month transaction dataset immediately without encountering local file CORS restrictions!

### Method B: Lightweight Local Web Server
```bash
# Using Python
cd docs
python -m http.server 8000

# Open in browser: http://localhost:8000
```

---

## 🛠️ Architecture & Technologies
- **HTML5 & CSS3**: Custom modern light-blue card dashboard with responsive CSS grid and mobile drawer navigation.
- **Vanilla JavaScript**: State-driven reactive calculations without heavy frontend frameworks.
- **Plotly.js (v2.35.2)**: High-performance interactive charts with hover tooltips, zoom, and SVG export.
- **PapaParse (v5.4.1)**: Blazing-fast client-side CSV parsing.
- **SheetJS / XLSX (v0.18.5)**: Client-side Excel spreadsheet ingestion.
- **Zero-Backend Processing**: All calculations (Tukey's Resistant Line, OLS Regression, Chi-Square Independence, Frequency Resampling) execute directly in the browser's JavaScript V8 engine.
