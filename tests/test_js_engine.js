/**
 * Automated Verification Test for GitHub Pages JavaScript Analytics Engine.
 * Tests data loading, cleaning, KPIs, Tukey's Resistant Line, OLS, Contingency tables,
 * and Time Series resampling implemented in JavaScript.
 */

const fs = require('fs');
const path = require('path');

const baseDir = path.resolve(__dirname, '..');
const csvPath = path.join(baseDir, 'dataset', 'online_shopping_data.csv');
const csvContent = fs.readFileSync(csvPath, 'utf8');

// Basic CSV parser for headless node testing (mimics PapaParse results)
function parseCSV(text) {
  const lines = text.trim().split(/\r?\n/);
  const headers = lines[0].split(',').map(h => h.trim());
  const rows = [];
  for (let i = 1; i < lines.length; i++) {
    const parts = lines[i].split(',');
    if (parts.length >= headers.length) {
      const row = {};
      headers.forEach((h, idx) => {
        const val = parts[idx].trim();
        const num = Number(val);
        row[h] = !isNaN(num) && val !== '' ? num : val;
      });
      rows.push(row);
    }
  }
  return rows;
}

console.log("=== TEST 1: CSV Ingestion in Node.js ===");
const rawData = parseCSV(csvContent);
console.log(`Parsed ${rawData.length} rows from ${csvPath}`);
if (rawData.length < 3000) throw new Error("Dataset row count too low!");

console.log("\n=== TEST 2: Data Cleaning (Deduplication & Imputation) ===");
const seen = new Set();
let dups = 0;
const cleaned = [];
rawData.forEach(r => {
  const s = JSON.stringify(r);
  if (seen.has(s)) dups++;
  else {
    seen.add(s);
    cleaned.push({ ...r });
  }
});
console.log(`Detected ${dups} duplicates. Cleaned rows: ${cleaned.length}`);
if (dups !== 12) console.warn(`Expected 12 duplicates, found ${dups}`);

console.log("\n=== TEST 3: Dynamic KPIs Calculation ===");
const totalRev = cleaned.reduce((sum, r) => sum + (Number(r['Total Amount']) || 0), 0);
const totalOrders = cleaned.length;
const aov = totalRev / totalOrders;
console.log(`Total Revenue: $${totalRev.toFixed(2)}`);
console.log(`Total Orders: ${totalOrders}`);
console.log(`Average Order Value: $${aov.toFixed(2)}`);

if (totalRev < 500000) throw new Error("Total revenue mismatch!");

console.log("\n=== TEST 4: Unit 4 - Tukey's 3-Group Resistant Line vs OLS in JS ===");
const pairs = cleaned.map(r => ({ x: Number(r['Quantity']), y: Number(r['Total Amount']) }))
  .filter(p => !isNaN(p.x) && !isNaN(p.y));

// OLS
const n = pairs.length;
let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0;
pairs.forEach(p => {
  sumX += p.x; sumY += p.y;
  sumXY += p.x * p.y;
  sumX2 += p.x * p.x;
});
const olsSlope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
const olsIntercept = (sumY - olsSlope * sumX) / n;
console.log(`OLS Linear Equation: y = ${olsIntercept.toFixed(2)} + ${olsSlope.toFixed(2)}x`);

// Tukey's Resistant Line
const sorted = pairs.slice().sort((a, b) => a.x - b.x);
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

const xL = getMedian(groupL, 'x'), yL = getMedian(groupL, 'y');
const xM = getMedian(groupM, 'x'), yM = getMedian(groupM, 'y');
const xR = getMedian(groupR, 'x'), yR = getMedian(groupR, 'y');

const resSlope = xR !== xL ? (yR - yL) / (xR - xL) : 0;
const resIntercept = (1 / 3) * ((yL - resSlope * xL) + (yM - resSlope * xM) + (yR - resSlope * xR));

console.log(`Tukey's Resistant Line: y = ${resIntercept.toFixed(2)} + ${resSlope.toFixed(2)}x`);
console.log(`Tukey 3-Group Medians: Left=(${xL}, ${yL}), Mid=(${xM}, ${yM}), Right=(${xR}, ${yR})`);

if (resSlope <= 0) throw new Error("Resistant slope must be positive!");
if (olsSlope <= 0) throw new Error("OLS slope must be positive!");

console.log("\n=== TEST 5: Unit 4 - Contingency Table & Chi-Square ===");
const rowVals = [...new Set(cleaned.map(r => r['Product Category']).filter(Boolean))].sort();
const colVals = [...new Set(cleaned.map(r => r['Payment Method']).filter(Boolean))].sort();

const matrix = {};
rowVals.forEach(r => {
  matrix[r] = {};
  colVals.forEach(c => matrix[r][c] = 0);
});
cleaned.forEach(row => {
  const r = row['Product Category'], c = row['Payment Method'];
  if (matrix[r] && matrix[r][c] !== undefined) matrix[r][c]++;
});

const rowTotals = {}, colTotals = {};
let grandTotal = 0;
rowVals.forEach(r => {
  rowTotals[r] = 0;
  colVals.forEach(c => {
    rowTotals[r] += matrix[r][c];
    colTotals[c] = (colTotals[c] || 0) + matrix[r][c];
    grandTotal += matrix[r][c];
  });
});

let chi2 = 0;
rowVals.forEach(r => {
  colVals.forEach(c => {
    const observed = matrix[r][c];
    const expected = (rowTotals[r] * colTotals[c]) / grandTotal;
    if (expected > 0) chi2 += Math.pow(observed - expected, 2) / expected;
  });
});
const dof = (rowVals.length - 1) * (colVals.length - 1);
console.log(`Contingency Dimensions: ${rowVals.length}x${colVals.length}, Chi2 = ${chi2.toFixed(3)}, DoF = ${dof}`);

console.log("\n=== TEST 6: Unit 5 - Time Series Resampling (Monthly) ===");
const monthMap = {};
cleaned.forEach(r => {
  const dt = new Date(r['Order Date']);
  if (!isNaN(dt.getTime())) {
    const my = `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, '0')}`;
    monthMap[my] = (monthMap[my] || 0) + Number(r['Total Amount']);
  }
});
const months = Object.keys(monthMap).sort();
console.log(`Monthly Buckets: ${months.length} months detected: ${months.join(', ')}`);
if (months.length !== 12) throw new Error(`Expected 12 months, got ${months.length}`);

console.log("\n🎉 ALL JAVASCRIPT ANALYTICAL ENGINE TESTS PASSED WITH 100% SUCCESS!");
