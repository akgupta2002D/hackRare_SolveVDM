import React, { useMemo, useState } from "react";
import "./resourcepage.css";
import { useNavigate } from "react-router-dom";

const AUDIENCES = {
  CLINICAL: "Clinicians & Researchers",
  PATIENTS: "Patients & Families",
};

function Pill({ tone = "navy", children }) {
  const cls =
    tone === "red"
      ? "virtuousPill virtuousPillRed"
      : tone === "green"
      ? "virtuousPill virtuousPillGreen"
      : "virtuousPill virtuousPillNavy";
  return <span className={cls}>{children}</span>;
}

function Tag({ children }) {
  return <span className="virtuousTag">{children}</span>;
}

function ResourceCard({ item }) {
  return (
    <article className="virtuousResourceCard">
      <div className="virtuousResourceTop">
        <div className="virtuousResourceTitleRow">
          <h3 className="virtuousResourceTitle">{item.title}</h3>
          <div className="virtuousResourceMeta">
            <Tag>{item.type}</Tag>
            {item.year ? <Tag>{item.year}</Tag> : null}
          </div>
        </div>
        <p className="virtuousResourceBlurb">{item.blurb}</p>
      </div>

      <div className="virtuousResourceBottom">
        <div className="virtuousResourceChips">
          {(item.topics || []).map((t) => (
            <span key={t} className="virtuousChip">
              {t}
            </span>
          ))}
        </div>

        <div className="virtuousResourceLinks">
          {(item.links || []).map((l) => (
            <a
              key={l.href}
              className="virtuousLink"
              href={l.href}
              target="_blank"
              rel="noreferrer"
            >
              {l.label}
            </a>
          ))}
        </div>
      </div>
    </article>
  );
}

export default function VirtuousResourcesPage() {
  const navigate = useNavigate();
  const [audience, setAudience] = useState(AUDIENCES.CLINICAL);
  const [query, setQuery] = useState("");

  const library = useMemo(
    () => [
      // Essentials only
      {
        title: "Clinical Management of Vision-Degrading Myodesopsia (VDM)",
        type: "Clinical review / management",
        year: "2025",
        blurb:
          "Clinician-facing framework emphasizing objective measurement + functional endpoints; useful for building care pathways and research protocols.",
        topics: ["VDM", "Clinical pathways", "Endpoints"],
        audience: AUDIENCES.CLINICAL,
        links: [
          {
            label: "Full text",
            href: "https://www.ophthalmologyretina.org/article/S2468-6530(25)00221-0/fulltext",
          },
        ],
      },
      {
        title: "Vitreous Floaters Functional Questionnaire (VFFQ-23)",
        type: "PROM development",
        year: "2024",
        blurb:
          "Floater-specific PROM; links patient function to objective measures (useful for trials and registries).",
        topics: ["PROM", "VFFQ-23", "Standardization"],
        audience: AUDIENCES.CLINICAL,
        links: [
          {
            label: "JAMA Ophthalmology",
            href: "https://jamanetwork.com/journals/jamaophthalmology/fullarticle/2839367",
          },
        ],
      },
      {
        title: "Nd:YAG vitreolysis vs sham for symptomatic Weiss ring floaters",
        type: "Randomized clinical trial",
        year: "2017",
        blurb:
          "Masked, sham-controlled RCT; foundational evidence for vitreolysis in a specific phenotype (Weiss ring).",
        topics: ["YAG", "RCT", "Weiss ring"],
        audience: AUDIENCES.CLINICAL,
        links: [
          {
            label: "JAMA Ophthalmology",
            href: "https://jamanetwork.com/journals/jamaophthalmology/fullarticle/2643488",
          },
        ],
      },
      {
        title: "PPV for primary symptomatic floaters: systematic review + meta-analysis",
        type: "Systematic review / meta-analysis",
        year: "2022",
        blurb:
          "Synthesizes PPV outcomes and complications; anchors clinician counseling and selection discussions.",
        topics: ["Vitrectomy", "Safety", "Meta-analysis"],
        audience: AUDIENCES.CLINICAL,
        links: [
          {
            label: "Springer (Ophthalmology and Therapy)",
            href: "https://link.springer.com/article/10.1007/s40123-022-00578-9",
          },
        ],
      },
      {
        title: "Psychological implications of vitreous opacities: systematic review",
        type: "Systematic review",
        year: "2022",
        blurb:
          "Summarizes evidence linking symptomatic vitreous opacities to depression/anxiety and broader wellbeing—important for youth support plans.",
        topics: ["Mental health", "QoL", "Youth"],
        audience: AUDIENCES.CLINICAL,
        links: [
          {
            label: "ScienceDirect",
            href: "https://www.sciencedirect.com/science/article/pii/S0022399922000149",
          },
        ],
      },
      {
        title: "AAO: Floaters & Flashes (urgent warning signs)",
        type: "Patient guidance (safety)",
        year: "",
        blurb:
          "Clear red-flag symptoms and what to do; good for family-facing triage education.",
        topics: ["Safety", "Triage", "Patient education"],
        audience: AUDIENCES.PATIENTS,
        links: [
          {
            label: "AAO page",
            href: "https://www.aao.org/eye-health/diseases/what-are-floaters-flashes",
          },
        ],
      },
      {
        title: "NEI: Retinal detachment (when urgent care is needed)",
        type: "Patient guidance (safety)",
        year: "",
        blurb:
          "Public-health oriented overview of detachment and urgent symptoms; family-friendly reference.",
        topics: ["Safety", "Urgent symptoms"],
        audience: AUDIENCES.PATIENTS,
        links: [
          {
            label: "NEI page",
            href: "https://www.nei.nih.gov/eye-health-information/eye-conditions-and-diseases/retinal-detachment",
          },
        ],
      },
    ],
    []
  );

  const filteredLibrary = useMemo(() => {
    const q = query.trim().toLowerCase();

    const audienceFiltered =
      audience === AUDIENCES.CLINICAL
        ? library
        : library.filter((r) => r.audience === AUDIENCES.PATIENTS);

    if (!q) return audienceFiltered;

    return audienceFiltered.filter((r) => {
      const hay = `${r.title} ${r.blurb} ${(r.topics || []).join(" ")}`.toLowerCase();
      return hay.includes(q);
    });
  }, [library, query, audience]);

  const figures = [
    // Wikimedia-hosted, stable rendering
    {
      title: "Human eye schematic (orientation)",
      caption:
        "Where the vitreous sits (between lens and retina). Useful for patient/family understanding.",
      src: "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c2/Schematic_diagram_of_the_human_eye_en.svg/1280px-Schematic_diagram_of_the_human_eye_en.svg.png",
    },
    {
      title: "Eye diagram (no text)",
      caption:
        "Clean diagram for clinician-facing orientation or overlay annotations in your own figure set.",
      src: "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8d/Eye_diagram_no_text.svg/1280px-Eye_diagram_no_text.svg.png",
    },
  ];

  return (
    <div className="virtuousSinglePage">
      <div className="container virtuousSingleContainer">
        {/* Header */}
        <header className="virtuousHeader card cardTitle">
          <div className="virtuousHeaderTopRow">
            <button className="virtuousNavBtn" onClick={() => navigate(-1)}>
              ← Back
            </button>

            <div className="virtuousAudienceToggle" role="tablist" aria-label="Audience toggle">
              <button
                className={`virtuousToggle ${
                  audience === AUDIENCES.CLINICAL ? "virtuousToggleActive blue_border" : ""
                }`}
                onClick={() => setAudience(AUDIENCES.CLINICAL)}
              >
                Clinicians & Researchers
              </button>
              <button
                className={`virtuousToggle ${
                  audience === AUDIENCES.PATIENTS ? "virtuousToggleActive red_border" : ""
                }`}
                onClick={() => setAudience(AUDIENCES.PATIENTS)}
              >
                Patients & Families
              </button>
            </div>
          </div>

          <div className="virtuousHeaderTitle">Scientific Resource Hub</div>
          <div className="virtuousHeaderSubtitle">
            Vision-degrading eye floaters (VDM / myodesopsia) — curated evidence and measurement tools,
            designed to support neglected youth and enable clinician-researcher progress.
          </div>

          <div className="virtuousPillRow" style={{ marginTop: 14 }}>
            <Pill tone="navy">Acknowledge</Pill>
            <Pill tone="red">Believe</Pill>
            <Pill tone="green">Community</Pill>
          </div>
        </header>

        {/* Safety callout */}
        <section className="virtuousBlock card card--raised modal--danger">
          <div className="virtuousCalloutTitle">Urgent symptoms (seek urgent eye care if new/sudden)</div>
          <ul className="virtuousList">
            <li>Sudden increase in floaters</li>
            <li>Flashes of light</li>
            <li>Shadow in side vision</li>
            <li>Gray “curtain” over part of vision</li>
          </ul>
          <div className="virtuousInlineLinks" style={{ marginTop: 12 }}>
            <a
              className="virtuousLink"
              href="https://www.aao.org/eye-health/diseases/what-are-floaters-flashes"
              target="_blank"
              rel="noreferrer"
            >
              AAO: Floaters & Flashes
            </a>
            <a
              className="virtuousLink"
              href="https://www.nei.nih.gov/eye-health-information/eye-conditions-and-diseases/retinal-detachment"
              target="_blank"
              rel="noreferrer"
            >
              NEI: Retinal Detachment
            </a>
          </div>
        </section>

        {/* Clinician/researcher overview (still readable for families) */}
        <section className="virtuousBlock">
          <div className="virtuousBlockHeader">
            <h2 className="virtuousH2">What VDM is (and why youth get overlooked)</h2>
            <div className="virtuousPillRow">
              <Pill tone="navy">Measurement</Pill>
              <Pill tone="green">Endpoints</Pill>
            </div>
          </div>

          <p className="virtuousP">
            Many people notice floaters, but a subset experience <strong>vision-degrading myodesopsia (VDM)</strong>:
            persistent symptoms with measurable functional impact (often contrast sensitivity) and major quality-of-life
            burden. Youth may be dismissed because high-contrast acuity can remain normal while day-to-day vision is
            disrupted (screens, bright surfaces, reading, driving).
          </p>

          {audience === AUDIENCES.CLINICAL ? (
            <div className="virtuousMiniCard card card--raised modal--info" style={{ marginTop: 14 }}>
              <div className="virtuousCalloutTitle">Recommended “minimum battery” (research clinics)</div>
              <ul className="virtuousList">
                <li>Objective vitreous metric (structure)</li>
                <li>Contrast sensitivity / functional vision measure</li>
                <li>Floater-specific PROM (e.g., VFFQ-23)</li>
              </ul>
            </div>
          ) : (
            <div className="virtuousMiniCard card card--raised modal--success" style={{ marginTop: 14 }}>
              <div className="virtuousCalloutTitle">What families can do (practical support)</div>
              <ul className="virtuousList">
                <li>Validate symptoms; don’t minimize.</li>
                <li>Track triggers (screens, bright walls, sunlight) and how school/work is affected.</li>
                <li>Bring written examples to appointments.</li>
                <li>Watch for anxiety/depression and seek support early.</li>
              </ul>
            </div>
          )}
        </section>

        {/* Research library */}
        <section className="virtuousBlock">
          <div className="virtuousBlockHeader">
            <h2 className="virtuousH2">Essential resources</h2>
          </div>

          <div className="virtuousSearchRow">
            <input
              className="virtuousInput"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={
                audience === AUDIENCES.CLINICAL
                  ? "Search: VFFQ-23, vitrectomy, YAG, endpoints, management…"
                  : "Search: urgent, flashes, curtain, safety…"
              }
            />
          </div>

          <div className="virtuousResourceGrid">
            {filteredLibrary.map((item) => (
              <ResourceCard key={item.title} item={item} />
            ))}
          </div>
        </section>

        {/* Figures */}
        <section className="virtuousBlock">
          <div className="virtuousBlockHeader">
            <h2 className="virtuousH2">Figures (renderable)</h2>
          </div>

          <p className="virtuousP">
            These are stable, Wikimedia-hosted diagrams. For journal figures, prefer your own generated diagrams or images
            you have explicit reuse permission for.
          </p>

          <div className="virtuousFigureGrid">
            {figures.map((f) => (
              <figure key={f.title} className="virtuousFigure card card--raised">
                <img className="virtuousFigureImg" src={f.src} alt={f.title} loading="lazy" />
                <figcaption className="virtuousFigureCaption">
                  <div className="virtuousFigureTitle">{f.title}</div>
                  <div className="virtuousFigureText">{f.caption}</div>
                  <a
                    className="virtuousLink"
                    href={f.src}
                    target="_blank"
                    rel="noreferrer"
                    style={{ display: "inline-block", marginTop: 10 }}
                  >
                    Open image source
                  </a>
                </figcaption>
              </figure>
            ))}
          </div>
        </section>

        {/* Footer */}
        <footer className="virtuousFooter">
          <button
            className="virtuousBtn"
            onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
          >
            Back to top
          </button>
        </footer>
      </div>
    </div>
  );
}