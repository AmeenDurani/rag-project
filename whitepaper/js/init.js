import { renderGroupedBarChart, fmtDecimal } from "./charts.js";

// Real numbers from eval/results/{baseline,small_chunks,token_aware}*.json -
// not paraphrased. See the "Chunking iteration story" section for the
// methodology and the per-question evidence behind these aggregates.
//
// Colors are literal hex, matching css/style.css's --series-N tokens exactly
// - SVG presentation attributes (fill="...") don't reliably resolve CSS
// custom properties the way an inline `style` declaration would, so this
// avoids a cross-browser gamble rather than "fixing" it after the fact.
const SERIES_1 = "#2a78d6"; // blue
const SERIES_2 = "#eb6834"; // orange
const SERIES_3 = "#1baf7a"; // aqua
const SERIES_4 = "#eda100"; // yellow

const ITERATIONS = ["Baseline", "Smaller chunks", "Token-aware"];

renderGroupedBarChart({
  containerId: "chart-retrieval",
  title: "Retrieval quality across three chunking iterations",
  subtitle:
    "18 answerable questions, NASA SE Handbook corpus. Baseline: word-based 500/50. Smaller chunks: word-based 150/15. Token-aware: 400/40 tokens.",
  categories: ITERATIONS,
  series: [
    { name: "Recall@1", color: SERIES_1, values: [0.7778, 0.7778, 0.7222] },
    { name: "Recall@3", color: SERIES_2, values: [0.9444, 0.9444, 0.8889] },
    { name: "Recall@5", color: SERIES_3, values: [1.0, 0.9444, 0.9444] },
    { name: "MRR", color: SERIES_4, values: [0.8630, 0.8611, 0.8009], format: fmtDecimal },
  ],
});

renderGroupedBarChart({
  containerId: "chart-quality",
  title: "Answer quality across the same three iterations",
  subtitle:
    "22 questions (18 answerable + 4 out-of-scope), LLM-as-judge (Claude Sonnet 5, thinking disabled).",
  categories: ITERATIONS,
  series: [
    { name: "Faithfulness", color: SERIES_1, values: [1.0, 1.0, 1.0] },
    { name: "Relevance", color: SERIES_2, values: [1.0, 1.0, 1.0] },
    { name: "Scope accuracy", color: SERIES_3, values: [1.0, 0.9545, 0.8636] },
  ],
});
