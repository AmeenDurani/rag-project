// Hand-rolled grouped bar chart, built to the dataviz skill's mark specs:
// thin capped bars, 4px rounded top / square baseline, a 2px surface gap
// between adjacent bars, direct value labels (mandatory once a chart carries
// 3-4 series), a hover/focus tooltip per bar, and a table-view toggle as the
// WCAG-clean twin of the chart. No charting library - full control over
// those specs was worth more than a dependency here.

const SVG_NS = "http://www.w3.org/2000/svg";

function el(tag, attrs, parent) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs || {})) node.setAttribute(k, v);
  if (parent) parent.appendChild(node);
  return node;
}

function roundedTopBarPath(x, yTop, width, height, radius) {
  if (height <= 0) return "";
  const r = Math.min(radius, width / 2, height);
  const yBottom = yTop + height;
  return [
    `M${x},${yBottom}`,
    `L${x},${yTop + r}`,
    `Q${x},${yTop} ${x + r},${yTop}`,
    `L${x + width - r},${yTop}`,
    `Q${x + width},${yTop} ${x + width},${yTop + r}`,
    `L${x + width},${yBottom}`,
    "Z",
  ].join(" ");
}

function fmtPercent(v) {
  return `${(v * 100).toFixed(1)}%`;
}

function fmtDecimal(v) {
  return v.toFixed(3);
}

/**
 * config:
 *   containerId, title, subtitle, categories: string[],
 *   series: [{ name, color, values: number[], format?: (v) => string }],
 *   valueDomainMax (default 1.0)
 */
export function renderGroupedBarChart(config) {
  const {
    containerId,
    title,
    subtitle,
    categories,
    series,
    valueDomainMax = 1.0,
  } = config;

  const root = document.getElementById(containerId);
  if (!root) return;

  const width = 640;
  const height = 300;
  const marginTop = 16;
  const marginBottom = 30;
  const marginLeft = 8;
  const marginRight = 8;
  const plotW = width - marginLeft - marginRight;
  const plotH = height - marginTop - marginBottom;
  const barW = 22;
  const barGap = 2;
  const groupCount = categories.length;
  const seriesCount = series.length;
  const groupW = seriesCount * barW + (seriesCount - 1) * barGap;
  const groupGap = (plotW - groupCount * groupW) / (groupCount + 1);

  // --- figure chrome: legend ---
  const figcaption = document.createElement("figcaption");
  figcaption.innerHTML = "";
  const titleEl = document.createElement("div");
  titleEl.className = "chart-title";
  titleEl.textContent = title;
  const subtitleEl = document.createElement("div");
  subtitleEl.className = "chart-subtitle";
  subtitleEl.textContent = subtitle;
  figcaption.appendChild(titleEl);
  figcaption.appendChild(subtitleEl);
  root.appendChild(figcaption);

  const legend = document.createElement("div");
  legend.className = "chart-legend";
  series.forEach((s) => {
    const key = document.createElement("span");
    key.className = "key";
    const sw = document.createElement("span");
    sw.className = "swatch";
    sw.style.background = s.color;
    const label = document.createElement("span");
    label.textContent = s.name;
    key.appendChild(sw);
    key.appendChild(label);
    legend.appendChild(key);
  });
  root.appendChild(legend);

  const wrap = document.createElement("div");
  wrap.className = "chart-wrap";
  root.appendChild(wrap);

  const svg = el("svg", {
    class: "chart-svg",
    viewBox: `0 0 ${width} ${height}`,
    role: "img",
    "aria-label": `${title}. ${subtitle}`,
  });
  wrap.appendChild(svg);

  const tooltip = document.createElement("div");
  tooltip.className = "chart-tooltip";
  wrap.appendChild(tooltip);

  // gridlines at 0/25/50/75/100%
  for (let step = 0; step <= 4; step++) {
    const frac = step / 4;
    const y = marginTop + plotH * (1 - frac);
    el(
      "line",
      {
        x1: marginLeft,
        x2: width - marginRight,
        y1: y,
        y2: y,
        stroke: step === 0 ? "var(--baseline-line)" : "var(--gridline)",
        "stroke-width": 1,
      },
      svg
    );
  }

  function showTooltip(barNode, category, s, value) {
    const barRect = barNode.getBoundingClientRect();
    const wrapRect = wrap.getBoundingClientRect();
    tooltip.style.left = `${barRect.left - wrapRect.left + barRect.width / 2}px`;
    tooltip.style.top = `${barRect.top - wrapRect.top}px`;
    tooltip.textContent = "";
    const valueSpan = document.createElement("span");
    valueSpan.className = "tt-value";
    valueSpan.textContent = (s.format || fmtPercent)(value);
    const seriesSpan = document.createElement("span");
    seriesSpan.className = "tt-series";
    seriesSpan.textContent = `${s.name} — ${category}`;
    tooltip.appendChild(valueSpan);
    tooltip.appendChild(seriesSpan);
    tooltip.style.opacity = "1";
  }

  function hideTooltip() {
    tooltip.style.opacity = "0";
  }

  categories.forEach((category, gi) => {
    const groupX = marginLeft + groupGap * (gi + 1) + groupW * gi;

    // Compute all bar geometry for this group first, so adjacent bars that
    // round to the same label (e.g. two metrics both at 100.0%, or both at
    // 94.4%) can be detected before drawing any label.
    const bars = series.map((s, si) => {
      const value = s.values[gi];
      const barH = plotH * Math.max(0, Math.min(1, value / valueDomainMax));
      const x = groupX + si * (barW + barGap);
      const yTop = marginTop + (plotH - barH);
      const labelText = (s.format || fmtPercent)(value);
      return { s, si, value, x, yTop, barH, labelText };
    });

    bars.forEach(({ s, value, x, yTop, barH, labelText }) => {
      const bar = el(
        "path",
        {
          d: roundedTopBarPath(x, yTop, barW, barH, 4),
          fill: s.color,
          tabindex: "0",
          role: "img",
          "aria-label": `${s.name}, ${category}: ${labelText}`,
        },
        svg
      );
      bar.style.cursor = "pointer";
      bar.addEventListener("pointerenter", () => showTooltip(bar, category, s, value));
      bar.addEventListener("pointerleave", hideTooltip);
      bar.addEventListener("focus", () => showTooltip(bar, category, s, value));
      bar.addEventListener("blur", hideTooltip);
    });

    // A run of consecutive bars with the identical rendered label (they're
    // also then the identical height, since label is a function of value)
    // gets exactly ONE shared label centered over the run, instead of N
    // stacked copies competing for the same headroom above the chart - see
    // marks-and-anatomy.md's rule against stacking colliding end-labels.
    let i = 0;
    while (i < bars.length) {
      let j = i;
      while (j + 1 < bars.length && bars[j + 1].labelText === bars[i].labelText) j++;
      const runStart = bars[i];
      const runEnd = bars[j];
      const midX = (runStart.x + runEnd.x + barW) / 2;
      const label = el(
        "text",
        {
          x: midX,
          y: runStart.yTop - 6,
          "text-anchor": "middle",
          class: "bar-value-label",
        },
        svg
      );
      label.textContent = runStart.labelText;
      i = j + 1;
    }

    const groupLabel = el(
      "text",
      {
        x: groupX + groupW / 2,
        y: height - 8,
        "text-anchor": "middle",
        class: "bar-group-label",
      },
      svg
    );
    groupLabel.textContent = category;
  });

  // --- table-view toggle: the WCAG-clean twin of the chart ---
  const toggleBtn = document.createElement("button");
  toggleBtn.type = "button";
  toggleBtn.className = "table-toggle";
  toggleBtn.textContent = "View as table";
  root.appendChild(toggleBtn);

  const dataTable = document.createElement("table");
  dataTable.className = "chart-data-table";
  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  const cornerTh = document.createElement("th");
  cornerTh.textContent = "Iteration";
  headRow.appendChild(cornerTh);
  series.forEach((s) => {
    const th = document.createElement("th");
    th.textContent = s.name;
    headRow.appendChild(th);
  });
  thead.appendChild(headRow);
  dataTable.appendChild(thead);

  const tbody = document.createElement("tbody");
  categories.forEach((category, gi) => {
    const row = document.createElement("tr");
    const th = document.createElement("th");
    th.scope = "row";
    th.style.fontWeight = "400";
    th.textContent = category;
    row.appendChild(th);
    series.forEach((s) => {
      const td = document.createElement("td");
      td.textContent = (s.format || fmtPercent)(s.values[gi]);
      row.appendChild(td);
    });
    tbody.appendChild(row);
  });
  dataTable.appendChild(tbody);
  root.appendChild(dataTable);

  toggleBtn.addEventListener("click", () => {
    const shown = dataTable.classList.toggle("shown");
    toggleBtn.textContent = shown ? "Hide table" : "View as table";
  });
}

export { fmtPercent, fmtDecimal };
