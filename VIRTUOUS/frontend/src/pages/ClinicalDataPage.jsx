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
      <header className={styles.topBar}>
        <button className={styles.backBtn} onClick={handleBack} type="button">
          ← Back
        </button>
      </header>

      <main className={styles.layout}>
        {/* ROW 1: Clinician message */}
        <section className={`${styles.row} ${styles.messageRow}`}>
          <div className={styles.messageCard}>
            <div className={styles.kicker}>Clinical Data</div>

            <h1 className={styles.title}>
            <span className={styles.titleRed}>We urge you</span> to take eye floaters seriously.
            </h1>

            <p className={styles.subtext}>
              For some patients, floaters are not a minor nuisance — they can meaningfully
              reduce quality of life. When symptoms are dismissed, patients often report
              feeling unheard and alone, which can compound distress and reduce trust in care.
            </p>

            <ul className={styles.facts}>
              <li>
                <span className={styles.factStrong}>Dismissal hurts:</span> when a symptom is
                treated as “nothing,” patients may stop reporting changes that matter clinically.
              </li>
              <li>
                <span className={styles.factStrong}>Loneliness is common:</span> floaters are
                hard to “prove” on routine imaging, and patients may feel isolated by the invisibility.
              </li>
              <li>
                <span className={styles.factStrong}>Mental load is real:</span> severe cases are
                associated with anxiety/depressive symptoms and functional impairment (reading, driving, screens).
              </li>
            </ul>

            <div className={styles.note}>
              Goal: convert subjective descriptions into structured, shareable patient-reported data
              that clinicians can use for insight, triage, and research.
            </div>
          </div>
        </section>

        {/* ROW 2: 3 column buttons */}
        <section className={`${styles.row} ${styles.actionsRow}`}>
          <div className={styles.actionsGrid}>
            <a className={`${styles.actionBtn} ${styles.actionPrimary}`} href="#patient-data">
              Patient Data (how they see the world?)
              <span className={styles.actionSub}>View examples + pattern categories</span>
            </a>

            <a className={`${styles.actionBtn} ${styles.actionGhost}`} href="#resources">
              Resources to understand it better
              <span className={styles.actionSub}>Guides, FAQs, clinician notes</span>
            </a>

            <a className={`${styles.actionBtn} ${styles.actionOutline}`} href="#api-access">
              API request to access data
              <span className={styles.actionSub}>Research + clinical integration</span>
            </a>
          </div>
        </section>
      </main>
    </div>
  );
}