import React, { useMemo, useState } from "react";
import phraseRows from "./symptom_phrase_counts.json";
import scrapeStats from "./reddit_scrape_stats.json";

const CATEGORY_LABELS = {
  symptoms: "Symptoms",
  daily_life_impact: "Daily Life Impact",
  recurring_patterns: "Recurring Patterns",
};

const CATEGORY_COLORS = {
  symptoms: "#2c7be5",
  daily_life_impact: "#00a884",
  recurring_patterns: "#7c3aed",
};

const EXCLUDED_CATEGORIES = new Set(["doctor_feedback"]);

const CLOUD_WIDTH = 760;
const CLOUD_HEIGHT = 320;
const BOX_PAD = 3;

const hashString = (value) => {
  let hash = 2166136261;
  for (let i = 0; i < value.length; i += 1) {
    hash ^= value.charCodeAt(i);
    hash +=
      (hash << 1) + (hash << 4) + (hash << 7) + (hash << 8) + (hash << 24);
  }
  return hash >>> 0;
};

const seededUnit = (seed, salt = 0) => {
  const x = Math.sin((seed + salt) * 12.9898) * 43758.5453;
  return x - Math.floor(x);
};

const intersects = (a, b) => {
  return !(
    a.x + a.w < b.x ||
    b.x + b.w < a.x ||
    a.y + a.h < b.y ||
    b.y + b.h < a.y
  );
};

const inBounds = (box) => {
  return (
    box.x >= 0 &&
    box.y >= 0 &&
    box.x + box.w <= CLOUD_WIDTH &&
    box.y + box.h <= CLOUD_HEIGHT
  );
};

const padBox = (box, pad = BOX_PAD) => ({
  x: box.x - pad,
  y: box.y - pad,
  w: box.w + pad * 2,
  h: box.h + pad * 2,
});

const estimateTextWidth = (text, fontSize) => {
  // Approximate average character width for this UI font stack.
  return Math.max(24, text.length * fontSize * 0.58);
};

const SymptomWordGraph = () => {
  const [activeCategory, setActiveCategory] = useState("all");

  const categories = useMemo(() => {
    return ["all", ...Object.keys(CATEGORY_LABELS)];
  }, []);

  const visibleRows = useMemo(() => {
    return phraseRows.filter((row) => !EXCLUDED_CATEGORIES.has(row.category));
  }, []);

  const filteredRows = useMemo(() => {
    if (activeCategory === "all") return visibleRows;
    return visibleRows.filter((row) => row.category === activeCategory);
  }, [activeCategory, visibleRows]);

  const maxCount = useMemo(() => {
    return filteredRows.reduce((max, row) => Math.max(max, row.count), 1);
  }, [filteredRows]);

  const packedRows = useMemo(() => {
    const sorted = [...filteredRows]
      .sort((a, b) => b.count - a.count)
      .map((row, idx) => {
        const ratio = row.count / maxCount;
        const fontSize = Math.round(12 + ratio * 34);
        const seed = hashString(`${activeCategory}-${row.category}-${row.phrase}`);
        const vertical = seededUnit(seed, 7) > 0.93;
        const rotation = vertical ? (seededUnit(seed, 8) > 0.5 ? 90 : -90) : 0;
        const baseW = estimateTextWidth(row.phrase, fontSize);
        const baseH = fontSize * 1.08;
        const w = vertical ? baseH : baseW;
        const h = vertical ? baseW : baseH;
        return { row, fontSize, rotation, w, h, ratio, seed, idx };
      });

    const placedBoxes = [];
    const placedWords = [];
    const anchors = [
      { x: CLOUD_WIDTH * 0.5, y: CLOUD_HEIGHT * 0.48 },
      { x: CLOUD_WIDTH * 0.3, y: CLOUD_HEIGHT * 0.35 },
      { x: CLOUD_WIDTH * 0.7, y: CLOUD_HEIGHT * 0.35 },
      { x: CLOUD_WIDTH * 0.3, y: CLOUD_HEIGHT * 0.67 },
      { x: CLOUD_WIDTH * 0.7, y: CLOUD_HEIGHT * 0.67 },
    ];

    for (const item of sorted) {
      let placed = null;
      const spiralTurns = 2200;
      const jitter = seededUnit(item.seed, 10) * Math.PI * 2;
      const anchor = anchors[item.seed % anchors.length];
      const startRadius = Math.min(70, 8 + item.idx * 2.4);
      const angleStep = 2.399963229728653; // Golden angle.
      const radiusStep = 1.55;

      for (let i = 0; i < spiralTurns; i += 1) {
        const angle = i * angleStep + jitter;
        const radius = startRadius + i * radiusStep;
        const x = anchor.x + Math.cos(angle) * radius;
        const y = anchor.y + Math.sin(angle) * radius;
        const box = {
          x: x - item.w / 2,
          y: y - item.h / 2,
          w: item.w,
          h: item.h,
        };
        const padded = padBox(box);
        if (!inBounds(padded)) continue;
        if (placedBoxes.some((other) => intersects(padded, other))) continue;
        placed = { ...item, x, y };
        placedBoxes.push(padded);
        break;
      }

      // Fallback random sampling with strict collision checks.
      if (!placed) {
        for (let j = 0; j < 1200 && !placed; j += 1) {
          const x = item.w / 2 + seededUnit(item.seed, 100 + j) * (CLOUD_WIDTH - item.w);
          const y = item.h / 2 + seededUnit(item.seed, 400 + j) * (CLOUD_HEIGHT - item.h);
          const box = padBox({
            x: x - item.w / 2,
            y: y - item.h / 2,
            w: item.w,
            h: item.h,
          });
          if (!inBounds(box)) continue;
          if (placedBoxes.some((other) => intersects(box, other))) continue;
          placed = { ...item, x, y };
          placedBoxes.push(box);
        }
      }

      if (placed) {
        placedWords.push(placed);
      }
    }

    return placedWords;
  }, [activeCategory, filteredRows]);

  return (
    <div className="symptomGraphWrap card card--raised">
      <div className="symptomGraphHead">
        <h2 className="emulatorInfoTitle">Community Phrase Graph</h2>
        <p className="symptomGraphSub">
          Terms from Reddit floater posts, sized by mention count. (
          {scrapeStats.posts} posts, {scrapeStats.comments} comments scraped)
        </p>
        <p className="symptomGraphNote">
          *Reddit only allows roughly 1,000 comments to be scraped per run via
          the current access method.
        </p>
      </div>

      <div className="symptomFilterRow">
        {categories.map((category) => {
          const isActive = activeCategory === category;
          const color =
            category === "all"
              ? "var(--muted)"
              : CATEGORY_COLORS[category] || "var(--muted)";
          const label = category === "all" ? "All" : CATEGORY_LABELS[category];
          return (
            <button
              key={category}
              type="button"
              className={`symptomFilterBtn ${isActive ? "isActive" : ""}`}
              onClick={() => setActiveCategory(category)}
              style={{ "--cat-color": color }}
            >
              {label}
            </button>
          );
        })}
      </div>

      <div className="wordCloud">
        <svg
          className="wordCloudSvg"
          viewBox={`0 0 ${CLOUD_WIDTH} ${CLOUD_HEIGHT}`}
          role="img"
          aria-label="Word cloud of floater-related phrases"
        >
          {packedRows.map(({ row, fontSize, rotation, x, y, ratio }) => (
            <text
              key={`${row.category}-${row.phrase}`}
              x={x}
              y={y}
              textAnchor="middle"
              dominantBaseline="middle"
              transform={rotation ? `rotate(${rotation} ${x} ${y})` : undefined}
              className="wordCloudItem"
              style={{
                fontSize: `${fontSize}px`,
                fill: CATEGORY_COLORS[row.category] || "var(--text)",
                opacity: 0.52 + ratio * 0.48,
              }}
            >
              <title>{`${CATEGORY_LABELS[row.category]}: ${row.count}`}</title>
              {row.phrase}
            </text>
          ))}
        </svg>
      </div>
    </div>
  );
};

export default SymptomWordGraph;
