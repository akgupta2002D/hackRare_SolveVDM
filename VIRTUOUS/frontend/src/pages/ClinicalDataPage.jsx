// src/pages/ClinicalDataPage.js
import React from "react";
import styles from "./clinicaldatapage.module.css";

export default function ClinicalDataPage() {
  const handleBack = () => {
    // If you're using react-router, replace with: navigate(-1)
    if (window.history.length > 1) window.history.back();
    else window.location.href = "/";
  };

  return (
    <div className={styles.page}>
      <button className={styles.backBtn} onClick={handleBack} type="button">
        ← Back
      </button>

      <div className={styles.split}>
        {/* LEFT COLUMN */}
        <section className={`${styles.left} card`}>
          <div className={styles.leftInner}>
            <div className={styles.kicker}>Clinical Data</div>

            <h1 className={styles.title}>
              <span className={styles.titleRed}>We urge you</span> to take eye
              floaters seriously.
            </h1>

            <p className={styles.subtext}>
              For some patients, floaters are not a minor nuisance — they can
              meaningfully reduce quality of life. When symptoms are dismissed,
              patients often report feeling unheard and alone, which can compound
              distress and reduce trust in care.
            </p>

            <div className={`${styles.infoBlock} card card--raised`}>
              <h2 className={styles.infoTitle}>Key clinical realities</h2>
              <ul className={styles.facts}>
                <li>
                  <span className={styles.factStrong}>Dismissal hurts:</span>{" "}
                  when a symptom is treated as “nothing,” patients may stop
                  reporting changes that matter clinically.
                </li>
                <li>
                  <span className={styles.factStrong}>Loneliness is common:</span>{" "}
                  floaters are hard to “prove” on routine imaging, and patients
                  may feel isolated by the invisibility.
                </li>
                <li>
                  <span className={styles.factStrong}>Mental load is real:</span>{" "}
                  severe cases are associated with anxiety/depressive symptoms
                  and functional impairment (reading, driving, screens).
                </li>
              </ul>

              <div className={styles.note}>
                Goal: convert subjective descriptions into structured, shareable
                patient-reported data that clinicians can use for insight,
                triage, and research.
              </div>
            </div>
          </div>
        </section>

        {/* RIGHT COLUMN (SplitLanding-like styling) */}
        <section className={styles.right}>
          {/* Top card (like SplitLanding "Our Tools") */}
          <div className={`${styles.topCard} card cardTitle`}>
            <div className={styles.topCardTitle}>Clinical Tools</div>
            <div className={styles.topCardSubtitle}>
              Towards a more accepting and validating clinical and patient stories.
            </div>
          </div>

          {/* Center stack (button + description pairs) */}
          <div className={styles.rightCenter}>
            <div className={styles.actionStack} data-interactive="true">
              <a
                className={`${styles.actionBtn} ${styles.actionPrimary}`}
                href="/sessions"
              >
                Patient Data (how they see the world?)
              </a>
              <p className={styles.toolDescription}>
                View examples and pattern categories from patient-reported floater
                appearances—turning subjective descriptions into consistent
                referenceable visuals.
              </p>

              <a
                className={`${styles.actionBtn} ${styles.actionGhost}`}
                href="/resources"
              >
                🛠️  Resources to understand it better
              </a>
              <p className={styles.toolDescription}>
                Practical guides, FAQs, and clinician-facing notes to help validate
                symptoms, communicate uncertainty, and support patient trust.
              </p>

              <a
                className={`${styles.actionBtn} ${styles.actionOutline}`}
                href="#api-access"
              >
                🛠️  API request to access data
              </a>
              <p className={styles.toolDescription}>
                For research and clinical integration—request structured access to
                datasets and metadata that can support analysis and downstream tools.
              </p>
            </div>
          </div>

          
        </section>
      </div>
    </div>
  );
}