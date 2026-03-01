import React, { useMemo, useState } from "react";
import "./floatersapidocs.css";
import { useNavigate } from "react-router-dom";

function Pill({ tone = "navy", children }) {
  const cls =
    tone === "red"
      ? "docsPill docsPillRed"
      : tone === "green"
      ? "docsPill docsPillGreen"
      : "docsPill docsPillNavy";
  return <span className={cls}>{children}</span>;
}

function Tag({ children }) {
  return <span className="docsTag">{children}</span>;
}

function CodeCard({ title, children }) {
  return (
    <div className="docsCode card card--raised">
      {title ? <div className="docsCodeTitle">{title}</div> : null}
      <pre className="docsPre">
        <code>{children}</code>
      </pre>
    </div>
  );
}

function Section({ id, title, subtitle, right }) {
  return (
    <section id={id} className="docsBlock card">
      <div className="docsBlockHeader">
        <div>
          <h2 className="docsH2">{title}</h2>
          {subtitle ? <p className="docsSub">{subtitle}</p> : null}
        </div>
        {right ? <div className="docsHeaderRight">{right}</div> : null}
      </div>
    </section>
  );
}

export default function FloatersDataDocs() {
  const navigate = useNavigate();
  const [q, setQ] = useState("");

  const toc = useMemo(
    () => [
      { id: "overview", label: "Overview" },
      { id: "what-you-get", label: "What you get" },
      { id: "data-models", label: "Data models" },
      { id: "classification", label: "Classification & labels" },
      { id: "derived", label: "Derived features" },
      { id: "rendering", label: "Rendering & image outputs" },
      { id: "workflows", label: "Clinical & research workflows" },
      { id: "examples", label: "Example records" },
      { id: "figures", label: "Figures" },
    ],
    []
  );

  const jump = (id) => {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const searchable = useMemo(() => {
    // Used only for filtering “Cards list” sections; for a mock docs page, keep it simple.
    const cards = [
      {
        title: "Drawing (vector)",
        type: "Core object",
        tags: ["strokes", "eye", "metadata"],
        body:
          "Patient/clinician input as stroke vectors + canvas geometry. Source of truth for replay and re-render.",
      },
      {
        title: "Rendered images",
        type: "Outputs",
        tags: ["png", "svg", "heatmap"],
        body:
          "Deterministic PNG/SVG from stroke data + optional heatmap outputs for density visualization.",
      },
      {
        title: "Classification",
        type: "Outputs",
        tags: ["labels", "confidence", "modelVersion"],
        body:
          "Standardized label set with confidence and model version for auditability and longitudinal studies.",
      },
      {
        title: "Derived features",
        type: "Quantitative",
        tags: ["coverage", "opacity", "count"],
        body:
          "Computed metrics enabling correlation with patient-reported outcomes and objective measures.",
      },
      {
        title: "Study/Cohort config",
        type: "Governance",
        tags: ["labelSet", "featureFlags"],
        body:
          "Defines what labels/features are enabled for a cohort and how comparisons stay consistent over time.",
      },
    ];

    const needle = q.trim().toLowerCase();
    if (!needle) return cards;

    return cards.filter((c) => {
      const hay = `${c.title} ${c.type} ${c.tags.join(" ")} ${c.body}`.toLowerCase();
      return hay.includes(needle);
    });
  }, [q]);

  return (
    <div className="docsPage">
      <div className="container docsContainer">
        {/* Header */}
        <header className="docsHeader card cardTitle">
          <div className="docsTopRow">
            <button className="virtuousNavBtn" onClick={() => navigate(-1)}>
              ← Back
            </button>

            <div className="docsPillRow">
              <Pill tone="navy">Documentation</Pill>
              <Pill tone="green">Clinician + Research</Pill>
              <Pill tone="red">VDM-focused</Pill>
            </div>
          </div>

          <h1 className="docsTitle">Floaters Data Page</h1>
          <p className="docsIntro">
            A structured, clinician-and-researcher oriented dataset view for{" "}
            <strong>eye floater drawings</strong>, <strong>rendered images</strong>,{" "}
            <strong>standardized classifications</strong>, and <strong>derived quantitative features</strong>.
            Designed to make subjective symptoms usable for clinical insight and study-scale research.
          </p>

          <div className="docsQuick">
            <div className="docsQuickItem">
              <div className="docsQuickLabel">Primary objects</div>
              <div className="docsMono">Drawing • RenderSet • Classification • Features</div>
            </div>
            <div className="docsQuickItem">
              <div className="docsQuickLabel">Primary use</div>
              <div className="docsMono">Registries • Trials • Clinical documentation</div>
            </div>
            <div className="docsQuickItem">
              <div className="docsQuickLabel">Linking key</div>
              <div className="docsMono">drawingId</div>
            </div>
          </div>
        </header>

        {/* Layout: sticky TOC + content */}
        <div className="docsLayout">
          <aside className="docsSide card card--raised">
            <div className="docsSideTitle">On this page</div>
            {toc.map((t) => (
              <button key={t.id} className="docsSideBtn" onClick={() => jump(t.id)}>
                {t.label}
              </button>
            ))}

            <div className="docsSideDivider" />

            <div className="docsSideTitle">Search concepts</div>
            <input
              className="docsInput"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search: renders, labels, features…"
            />
            <div className="docsHint">
              This search filters the “What you get” cards below.
            </div>
          </aside>

          <main className="docsMain">
            {/* OVERVIEW */}
            <section id="overview" className="docsBlock card">
              <div className="docsBlockHeader">
                <div>
                  <h2 className="docsH2">Overview</h2>
                  <p className="docsSub">
                    The Floaters Data Page bridges patient-reported visuals with clinician-ready structure:
                    repeatable renders, consistent labels, and numeric features you can analyze.
                  </p>
                </div>
                <div className="docsHeaderRight">
                  <div className="docsMiniBadges">
                    <Tag>Single drawing → many outputs</Tag>
                    <Tag>Audit-friendly</Tag>
                    <Tag>Study-scale</Tag>
                  </div>
                </div>
              </div>

              <div className="docsGrid2">
                <div className="docsMini card card--raised modal--info">
                  <div className="docsMiniTitle">For clinicians</div>
                  <p className="docsP">
                    Convert “invisible” symptoms into a record you can review longitudinally:
                    the drawing, the render, and the classification snapshot.
                  </p>
                </div>

                <div className="docsMini card card--raised modal--success">
                  <div className="docsMiniTitle">For researchers</div>
                  <p className="docsP">
                    Standardize subjective reports into a dataset: consistent label sets + derived features
                    that can be correlated with PROMs and functional measures.
                  </p>
                </div>
              </div>
            </section>

            {/* WHAT YOU GET */}
            <section id="what-you-get" className="docsBlock card">
              <div className="docsBlockHeader">
                <div>
                  <h2 className="docsH2">What you get</h2>
                  <p className="docsSub">
                    Core objects and outputs that appear on the Floaters Data Page.
                  </p>
                </div>
              </div>

              <div className="docsCardList">
                {searchable.map((c) => (
                  <div key={c.title} className="docsConcept card card--raised">
                    <div className="docsConceptTop">
                      <div className="docsConceptTitleRow">
                        <div className="docsConceptTitle">{c.title}</div>
                        <div className="docsConceptMeta">
                          <Tag>{c.type}</Tag>
                        </div>
                      </div>
                      <div className="docsConceptBody">{c.body}</div>
                    </div>
                    <div className="docsConceptTags">
                      {c.tags.map((t) => (
                        <span key={t} className="docsChip">
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </section>

            {/* DATA MODELS */}
            <section id="data-models" className="docsBlock card">
              <div className="docsBlockHeader">
                <div>
                  <h2 className="docsH2">Data models</h2>
                  <p className="docsSub">
                    The page is built around a normalized schema. One drawing can be re-rendered,
                    re-labeled, and re-featured over time.
                  </p>
                </div>
              </div>

              <div className="docsGrid2">
                <div className="docsMini card card--raised">
                  <div className="docsMiniTitle">Drawing</div>
                  <p className="docsP">
                    Vector strokes + canvas geometry + metadata (eye, source, timestamps).
                    This is the “source of truth.”
                  </p>
                  <CodeCard title="Drawing object (mock)">
{`{
  "drawingId": "drw_01HZ...",
  "createdAt": "2026-03-01T14:02:11Z",
  "eye": "OD",
  "source": "patient_emulator",
  "studyId": "cohort_012",
  "canvas": { "width": 1024, "height": 1024, "units": "px" },
  "strokes": [
    { "tool": "blob", "points": [[312,420],[318,426]], "radius": 8, "opacity": 0.35 }
  ]
}`}
                  </CodeCard>
                </div>

                <div className="docsMini card card--raised">
                  <div className="docsMiniTitle">RenderSet</div>
                  <p className="docsP">
                    Deterministic visual outputs derived from the drawing:
                    PNG for quick review, SVG for scalability, heatmaps for density summaries.
                  </p>
                  <CodeCard title="RenderSet object (mock)">
{`{
  "drawingId": "drw_01HZ...",
  "renderSetId": "rnd_91a3",
  "assets": {
    "png": "…/render.png",
    "svg": "…/render.svg",
    "heatmap": "…/heatmap.png"
  },
  "renderProfile": "vf-render-1.0"
}`}
                  </CodeCard>
                </div>
              </div>
            </section>

            {/* CLASSIFICATION */}
            <section id="classification" className="docsBlock card">
              <div className="docsBlockHeader">
                <div>
                  <h2 className="docsH2">Classification & labels</h2>
                  <p className="docsSub">
                    Standard labels make drawings searchable, comparable across cohorts, and usable in studies.
                  </p>
                </div>
                <div className="docsHeaderRight">
                  <div className="docsMiniBadges">
                    <Tag>label</Tag>
                    <Tag>confidence</Tag>
                    <Tag>modelVersion</Tag>
                  </div>
                </div>
              </div>

              <div className="docsGrid2">
                <div className="docsMini card card--raised">
                  <div className="docsMiniTitle">Classification record</div>
                  <p className="docsP">
                    A label assignment is always tied to a specific model version.
                    This keeps longitudinal data audit-friendly.
                  </p>
                  <CodeCard title="Classification (mock)">
{`{
  "classificationId": "clf_01HZ...",
  "drawingId": "drw_01HZ...",
  "labels": [
    { "name": "weiss_ring", "confidence": 0.86 },
    { "name": "diffuse_debris", "confidence": 0.22 }
  ],
  "modelVersion": "vf-clf-2.1",
  "createdAt": "2026-03-01T14:02:13Z"
}`}
                  </CodeCard>
                </div>

                <div className="docsMini card card--raised modal--info">
                  <div className="docsMiniTitle">Label set example</div>
                  <ul className="docsList">
                    <li><span className="docsInlineMono">weiss_ring</span> — ring-like opacity, often post-PVD phenotype</li>
                    <li><span className="docsInlineMono">strings</span> — filamentous patterns / strands</li>
                    <li><span className="docsInlineMono">diffuse_debris</span> — scattered small opacities</li>
                    <li><span className="docsInlineMono">central_opacity</span> — central dense region affecting fixation</li>
                  </ul>
                  <p className="docsP docsMuted" style={{ marginTop: 10 }}>
                    (Mock taxonomy) Align this with your research program’s definitions and inter-rater protocols.
                  </p>
                </div>
              </div>
            </section>

            {/* DERIVED FEATURES */}
            <section id="derived" className="docsBlock card">
              <div className="docsBlockHeader">
                <div>
                  <h2 className="docsH2">Derived features</h2>
                  <p className="docsSub">
                    Quantitative summaries computed from strokes/renders so teams can analyze and correlate.
                  </p>
                </div>
              </div>

              <div className="docsGrid2">
                <div className="docsMini card card--raised">
                  <div className="docsMiniTitle">Feature record</div>
                  <CodeCard title="Features (mock)">
{`{
  "drawingId": "drw_01HZ...",
  "featuresVersion": "vf-feat-1.4",
  "count": 14,
  "coveragePct": 6.2,
  "meanOpacity": 0.31,
  "motionComplexity": 0.44,
  "centralityScore": 0.67
}`}
                  </CodeCard>
                </div>

                <div className="docsMini card card--raised modal--success">
                  <div className="docsMiniTitle">How teams use features</div>
                  <ul className="docsList">
                    <li>Correlate <span className="docsInlineMono">coveragePct</span> with PROM severity</li>
                    <li>Stratify cohorts by <span className="docsInlineMono">centralityScore</span> for functional impact</li>
                    <li>Track change over time (pre/post intervention or longitudinal adaptation)</li>
                  </ul>
                </div>
              </div>
            </section>

            {/* RENDERING */}
            <section id="rendering" className="docsBlock card">
              <div className="docsBlockHeader">
                <div>
                  <h2 className="docsH2">Rendering & image outputs</h2>
                  <p className="docsSub">
                    The page displays deterministic image outputs derived from the same drawing object.
                  </p>
                </div>
              </div>

              <div className="docsGrid2">
                <div className="docsMini card card--raised">
                  <div className="docsMiniTitle">Render types</div>
                  <ul className="docsList">
                    <li><strong>PNG</strong>: quick clinical review</li>
                    <li><strong>SVG</strong>: scalable, annotation-friendly</li>
                    <li><strong>Heatmap</strong>: density summary for cohorts</li>
                  </ul>
                  <p className="docsP docsMuted" style={{ marginTop: 10 }}>
                    (Mock) Rendering should be stable across versions—always store a renderProfile/version.
                  </p>
                </div>

                <div className="docsMini card card--raised modal--info">
                  <div className="docsMiniTitle">Interpretation tips</div>
                  <ul className="docsList">
                    <li>Use heatmaps to compare cohorts without exposing raw strokes</li>
                    <li>Use SVG for clinician annotation and case discussions</li>
                    <li>Keep drawing + render linked by <span className="docsInlineMono">drawingId</span></li>
                  </ul>
                </div>
              </div>
            </section>

            {/* WORKFLOWS */}
            <section id="workflows" className="docsBlock card">
              <div className="docsBlockHeader">
                <div>
                  <h2 className="docsH2">Clinical & research workflows</h2>
                  <p className="docsSub">
                    Common ways teams use the Floaters Data Page in practice.
                  </p>
                </div>
              </div>

              <div className="docsGrid2">
                <div className="docsMini card card--raised modal--success">
                  <div className="docsMiniTitle">Clinic workflow (mock)</div>
                  <ol className="docsList">
                    <li>Patient creates drawing in Emulator</li>
                    <li>Clinician reviews PNG/SVG alongside symptoms</li>
                    <li>Record classification + features snapshot</li>
                    <li>Follow-up drawing to track change over time</li>
                  </ol>
                </div>

                <div className="docsMini card card--raised modal--info">
                  <div className="docsMiniTitle">Research workflow (mock)</div>
                  <ol className="docsList">
                    <li>Define cohort/study label set</li>
                    <li>Collect drawings + PROMs</li>
                    <li>Run standardized classification + feature extraction</li>
                    <li>Analyze: labels/features ↔ PROMs/functional measures</li>
                  </ol>
                </div>
              </div>
            </section>

            {/* EXAMPLES */}
            <section id="examples" className="docsBlock card">
              <div className="docsBlockHeader">
                <div>
                  <h2 className="docsH2">Example records</h2>
                  <p className="docsSub">
                    A single “bundle” showing how drawing → render → classification → features link together.
                  </p>
                </div>
              </div>

              <div className="docsGrid2">
                <CodeCard title="Bundle (mock)">
{`{
  "drawing": { "drawingId":"drw_01HZ...", "eye":"OD", "studyId":"cohort_012", "strokes":[...] },
  "renderSet": { "renderSetId":"rnd_91a3", "drawingId":"drw_01HZ...", "assets":{ "png":"...", "svg":"...", "heatmap":"..." } },
  "classification": { "classificationId":"clf_01HZ...", "drawingId":"drw_01HZ...", "labels":[{"name":"weiss_ring","confidence":0.86}], "modelVersion":"vf-clf-2.1" },
  "features": { "drawingId":"drw_01HZ...", "featuresVersion":"vf-feat-1.4", "coveragePct":6.2, "meanOpacity":0.31 }
}`}
                </CodeCard>

                <div className="docsMini card card--raised">
                  <div className="docsMiniTitle">Design principles</div>
                  <ul className="docsList">
                    <li>Every derived object references <span className="docsInlineMono">drawingId</span></li>
                    <li>Every model output includes <span className="docsInlineMono">modelVersion</span></li>
                    <li>Every feature output includes <span className="docsInlineMono">featuresVersion</span></li>
                    <li>Every render includes <span className="docsInlineMono">renderProfile</span></li>
                  </ul>
                </div>
              </div>
            </section>

            {/* FIGURES */}
            <section id="figures" className="docsBlock card">
              <div className="docsBlockHeader">
                <div>
                  <h2 className="docsH2">Figures (renderable)</h2>
                  <p className="docsSub">
                    Stable diagrams for orientation. You can later replace with your own floater render examples.
                  </p>
                </div>
              </div>

              <div className="docsFigureGrid">
                <figure className="docsFigure card card--raised">
                  <img
                    className="docsFigureImg"
                    src="https://upload.wikimedia.org/wikipedia/commons/thumb/c/c2/Schematic_diagram_of_the_human_eye_en.svg/1280px-Schematic_diagram_of_the_human_eye_en.svg.png"
                    alt="Human eye schematic"
                    loading="lazy"
                  />
                  <figcaption className="docsFigureCaption">
                    <div className="docsFigureTitle">Human eye schematic</div>
                    <div className="docsFigureText">
                      Orientation: vitreous sits between lens and retina.
                    </div>
                    <a
                      className="docsLink"
                      href="https://upload.wikimedia.org/wikipedia/commons/thumb/c/c2/Schematic_diagram_of_the_human_eye_en.svg/1280px-Schematic_diagram_of_the_human_eye_en.svg.png"
                      target="_blank"
                      rel="noreferrer"
                    >
                      Open image source
                    </a>
                  </figcaption>
                </figure>

                <figure className="docsFigure card card--raised">
                  <img
                    className="docsFigureImg"
                    src="https://upload.wikimedia.org/wikipedia/commons/thumb/8/8d/Eye_diagram_no_text.svg/1280px-Eye_diagram_no_text.svg.png"
                    alt="Eye diagram no text"
                    loading="lazy"
                  />
                  <figcaption className="docsFigureCaption">
                    <div className="docsFigureTitle">Eye diagram (no text)</div>
                    <div className="docsFigureText">
                      Clean diagram for overlays, training, or clinician annotation.
                    </div>
                    <a
                      className="docsLink"
                      href="https://upload.wikimedia.org/wikipedia/commons/thumb/8/8d/Eye_diagram_no_text.svg/1280px-Eye_diagram_no_text.svg.png"
                      target="_blank"
                      rel="noreferrer"
                    >
                      Open image source
                    </a>
                  </figcaption>
                </figure>
              </div>
            </section>

            <footer className="docsFooter">
              <button
                className="virtuousBtn"
                onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
              >
                Back to top
              </button>
            </footer>
          </main>
        </div>
      </div>
    </div>
  );
}