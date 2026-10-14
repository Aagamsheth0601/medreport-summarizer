import { useEffect, useRef, useState } from "react";
import { request, downloadFile } from "./api.js";
import { TABS, Icon, Disclaimer, ErrorNotice, AgentProgress, SourceReport,
         Summary, LabValues, Trace } from "./components.jsx";

// App owns sample selection, job state, and reconnectable polling.
export default function App() {
  const [samples, setSamples] = useState([]);
  const [selectedId, setSelectedId] = useState("mixed-patterns");
  const [loadError, setLoadError] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [run, setRun] = useState(null);
  const [requestError, setRequestError] = useState("");
  const [pollError, setPollError] = useState("");
  const [pollRetry, setPollRetry] = useState(0);
  const [tab, setTab] = useState("Overview");
  const mounted = useRef(true);
  const selected = samples.find((sample) => sample.id === selectedId);
  const result = run?.result;
  const busy = submitting || run?.status === "running";

  async function loadSamples() {
    setLoading(true);
    setLoadError("");
    try {
      const data = await request("/api/samples");
      if (mounted.current) setSamples(data);
    } catch (error) {
      if (mounted.current) setLoadError(error.message);
    } finally {
      if (mounted.current) setLoading(false);
    }
  }

  useEffect(() => {
    mounted.current = true;
    loadSamples();
    return () => {
      mounted.current = false;
    };
  }, []);

  // Poll only after each response returns: requests never overlap. On disconnect,
  // preserve the run ID so reconnecting checks the same job instead of spending again.
  useEffect(() => {
    if (!run?.id || run.status !== "running") return;
    let cancelled = false;
    let timer;
    async function poll() {
      try {
        const current = await request(`/api/runs/${run.id}`);
        if (cancelled) return;
        setRun(current);
        setPollError("");
        if (current.status === "running") timer = setTimeout(poll, 800);
      } catch (error) {
        if (cancelled) return;
        if (error.status === 404)
          setRun((previous) => ({
            ...previous,
            status: "failed",
            error: error.message,
          }));
        else
          setPollError(
            `${error.message} The server may still be processing this run.`,
          );
      }
    }
    poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [run?.id, run?.status, pollRetry]);

  function selectSample(id) {
    if (busy) return;
    setSelectedId(id);
    setRun(null);
    setRequestError("");
    setPollError("");
    setTab("Overview");
  }

  async function startRun() {
    setSubmitting(true);
    setRequestError("");
    setPollError("");
    setRun(null);
    setTab("Overview");
    try {
      const data = await request("/api/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sample_id: selectedId }),
      });
      if (mounted.current)
        setRun({
          id: data.id,
          sample_id: selectedId,
          status: "running",
          stages: {},
          result: null,
        });
    } catch (error) {
      if (mounted.current)
        setRequestError(
          error.message +
            (error.status
              ? ""
              : " If the request reached the server, wait before starting another run."),
        );
    } finally {
      if (mounted.current) setSubmitting(false);
    }
  }

  return (
    <>
      <a className="skip-link" href="#workspace">
        Skip to report workspace
      </a>
      <header className="site-header">
        <a className="brand" href="/" aria-label="MedReport home">
          <span className="brand-mark">
            <Icon name="pulse" size={24} />
          </span>
          <span>
            medreport<span className="brand-dot">.</span>
          </span>
          <span className="brand-divider" />
          <span className="brand-caption">REPORT DECODER</span>
        </a>
        <a
          className="repo-link"
          href="https://github.com/Aagamsheth0601/medreport-summarizer"
          target="_blank"
          rel="noreferrer"
        >
          View the code <Icon name="external" size={15} />
        </a>
      </header>
      <main>
        <section className="hero">
          <div className="hero-copy">
            <div className="eyebrow"><span className="tiny-square" /> BLOOD REPORTS, DECODED.</div>
            <h1>Less jargon.<br/><em>More clarity.</em></h1>
            <p>What happens between a blood report and an explanation you can actually understand? Meet the three AI agents doing the work.</p>
            <a className="hero-cta" href="#workspace">Explore a sample report <Icon name="arrow" /></a>
          </div>
          <div className="decoder-visual" aria-label="Three agents turn source values into a readable explanation">
            <div className="visual-label"><span>INSIDE THE SYSTEM</span><span>01 — 03</span></div>
            <div className="specimen"><span>SYNTHETIC BLOOD REPORT</span><strong>Hb <b>11.2</b> <small>g/dL</small></strong><div className="specimen-line"/><span>Values. Units. Reference ranges.</span></div>
            <div className="decoder-flow"><span>01 / READ</span><span>02 / CONNECT</span><span>03 / EXPLAIN</span></div>
            <div className="decoded-note"><Icon name="text" size={26}/><div><strong>The numbers become a story.</strong><p>With the original evidence one click away.</p></div></div>
            <span className="visual-footnote">ILLUSTRATIVE PROCESS • NO REAL PATIENT DATA</span>
          </div>
        </section>
        <Disclaimer />
        <section className="workspace" id="workspace" tabIndex="-1">
          <div className="workspace-heading">
            <div>
              <span className="eyebrow">THE INTERACTIVE DEMO</span>
              <h2>Pick a report. See it make sense.</h2>
            </div>
            <span className="workspace-caption">
              <span className="live-dot" /> Recorded AI outputs · Synthetic reports
            </span>
          </div>
          {loadError ? (
            <ErrorNotice action={loadSamples}>{loadError}</ErrorNotice>
          ) : loading ? (
            <div className="loading-state" role="status">
              Loading the sample library…
            </div>
          ) : (
            selected && (
              <div className="workspace-grid">
                <aside className="sample-sidebar">
                  <div className="sidebar-heading">
                    <span className="small-number">01</span>
                    <h3>Choose a sample</h3>
                    <span>3 reports</span>
                  </div>
                  <fieldset className="sample-options" disabled={busy}>
                    <legend className="sr-only">
                      Built-in synthetic reports
                    </legend>
                    {samples.map((sample, i) => (
                      <label
                        className={`sample-card ${sample.id === selectedId ? "selected" : ""}`}
                        key={sample.id}
                      >
                        <input
                          type="radio"
                          name="sample"
                          value={sample.id}
                          checked={sample.id === selectedId}
                          onChange={() => selectSample(sample.id)}
                        />
                        <div className="sample-card-top">
                          <span className="sample-number">REPORT 0{i + 1}</span>
                          <span className="selection-dot" />
                        </div>
                        <strong>{sample.title}</strong>
                        <span className="sample-subtitle">
                          {sample.subtitle}
                        </span>
                        <span className="sample-card-bottom">
                          <span>{sample.test_count} measurements</span>
                          <Icon name="arrow" size={17} />
                        </span>
                      </label>
                    ))}
                  </fieldset>
                  <div className="sample-description">
                    <Icon name="info" size={17} />
                    <p>{selected.description}</p>
                  </div>
                  <div className="engineering-note">
                    <span className="eyebrow">DESIGNED WITH INTENTION</span>
                    <p>
                      Each agent has one job. Every handoff is checked. Every
                      result can be inspected.
                    </p>
                    <a href="#architecture">
                      Explore the architecture <Icon name="arrow" size={15} />
                    </a>
                  </div>
                </aside>
                <div className="analysis-workspace">
                  <section className="pipeline-card">
                    <div className="card-heading">
                      <div>
                        <span className="small-number">02</span>
                        <h3>Follow the agents</h3>
                      </div>
                      <button
                        className="run-button"
                        onClick={startRun}
                        disabled={busy}
                      >
                        {busy ? (
                          <>
                            <span className="spinner" />{" "}
                            {submitting
                              ? "Starting analysis…"
                              : "Opening recorded demo…"}
                          </>
                        ) : (
                          <>
                            {result
                              ? "View this demo again"
                              : "Explore this report"}
                            <Icon name="arrow" />
                          </>
                        )}
                      </button>
                    </div>
                    <AgentProgress run={run} />
                    <div className="pipeline-bottom">
                      <span
                        className={`run-status ${run?.status || ""}`}
                        role="status"
                      >
                        {submitting
                          ? "Starting"
                          : run?.status === "completed"
                            ? "Analysis complete"
                            : run?.status === "failed"
                              ? "Analysis stopped"
                              : run?.status === "running"
                                ? "Analysis in progress"
                                : "Ready when you are"}
                      </span>
                      <span>Saved from three real Gemini calls · No live AI requests</span>
                    </div>
                  </section>
                  {requestError && <ErrorNotice>{requestError}</ErrorNotice>}
                  {pollError && (
                    <ErrorNotice
                      action={() => {
                        setPollError("");
                        setPollRetry((v) => v + 1);
                      }}
                      actionLabel="Reconnect to this run"
                    >
                      {pollError}
                    </ErrorNotice>
                  )}
                  {run?.status === "failed" && (
                    <ErrorNotice>
                      {run.error} No completed result is being shown. You can
                      try the sample again.
                    </ErrorNotice>
                  )}
                  <section className="result-card">
                    <div className="result-toolbar">
                      <div
                        className="tabs"
                        role="tablist"
                        aria-label="Report views"
                      >
                        {TABS.map((name, i) => (
                          <button
                            key={name}
                            role="tab"
                            id={`tab-${i}`}
                            aria-controls="result-panel"
                            aria-selected={tab === name}
                            tabIndex={tab === name ? 0 : -1}
                            disabled={!result && name !== "Overview"}
                            onClick={() => setTab(name)}
                            onKeyDown={(event) => {
                              if (
                                result &&
                                [
                                  "ArrowRight",
                                  "ArrowLeft",
                                  "Home",
                                  "End",
                                ].includes(event.key)
                              ) {
                                event.preventDefault();
                                const index =
                                  event.key === "Home"
                                    ? 0
                                    : event.key === "End"
                                      ? 2
                                      : (i +
                                          (event.key === "ArrowRight"
                                            ? 1
                                            : 2)) %
                                        3;
                                setTab(TABS[index]);
                                document.getElementById(`tab-${index}`).focus();
                              }
                            }}
                          >
                            {name}
                            {name === "Lab values" && result && (
                              <span className="tab-count">
                                {result.extraction.tests.length}
                              </span>
                            )}
                          </button>
                        ))}
                      </div>
                      {result && (
                        <button
                          className="download-button"
                          onClick={() =>
                            downloadFile(
                              `${selectedId}-summary.md`,
                              result.summary_markdown,
                              "text/markdown;charset=utf-8",
                            )
                          }
                          aria-label="Download summary"
                        >
                          <Icon name="download" size={17} />
                          <span>Summary</span>
                        </button>
                      )}
                    </div>
                    <div
                      id="result-panel"
                      role="tabpanel"
                      aria-labelledby={`tab-${TABS.indexOf(tab)}`}
                      tabIndex="0"
                    >
                      {!result ? (
                        <div className="before-run">
                          <div className="section-intro">
                            <span className="eyebrow">
                              {busy
                                ? "ANALYSIS UNDERWAY"
                                : "BEFORE THE AGENTS BEGIN"}
                            </span>
                            <h3>
                              {busy
                                ? "The evidence comes first."
                                : "Start with the source."}
                            </h3>
                            <p>
                              {busy
                                ? "Your sample is moving through the pipeline above. The completed explanation will appear here."
                                : "Choose a report, then explore its saved explanation, lab values, and outputs from all three agents. These are recorded runs of the real Python pipeline."}
                            </p>
                          </div>
                          <SourceReport sample={selected} />
                        </div>
                      ) : tab === "Overview" ? (
                        <Summary result={result} />
                      ) : tab === "Lab values" ? (
                        <LabValues result={result} />
                      ) : (
                        <Trace result={result} sample={selected} />
                      )}
                    </div>
                    {result && (
                      <div className="result-footer">
                        <span>Recorded output · {result.model}</span>
                        <button
                          className="text-button"
                          onClick={() =>
                            downloadFile(
                              `${selectedId}-all-stages.json`,
                              JSON.stringify(result, null, 2),
                              "application/json",
                            )
                          }
                        >
                          Download agent outputs (JSON) <Icon name="download" size={14} />
                        </button>
                      </div>
                    )}
                  </section>
                </div>
              </div>
            )
          )}
        </section>
        <section className="architecture" id="architecture">
          <div className="architecture-title">
            <span className="eyebrow">BEYOND A SINGLE PROMPT</span>
            <h2>
              A small system.
              <br />
              {" "}
              <em>Deliberate boundaries.</em>
            </h2>
            <p>
              Built to make the engineering visible, from the original evidence
              to the final explanation.
            </p>
          </div>
          <div className="architecture-features">
            <article>
              <span>01 / SPECIALIZATION</span>
              <h3>One responsibility per agent.</h3>
              <p>
                Three separate LLM calls keep extraction, interpretation, and
                communication inspectable.
              </p>
            </article>
            <article>
              <span>02 / VALIDATION</span>
              <h3>Trust is checked at the handoff.</h3>
              <p>
                Typed schemas, exact source-value checks, and linked findings
                catch missing or altered evidence.
              </p>
            </article>
            <article>
              <span>03 / HONEST LIMITS</span>
              <h3>Failures stay visible.</h3>
              <p>
                Invalid outputs stop the run. Synthetic data and explicit
                limitations keep this an educational demo.
              </p>
            </article>
          </div>
        </section>
      </main>
      <footer className="site-footer">
        <span className="footer-brand">
          <Icon name="pulse" size={18} /> medreport.
        </span>
        <span>Built by Aagam Sheth · An exploration in multi-agent AI</span>
        <a
          href="https://github.com/Aagamsheth0601/medreport-summarizer"
          target="_blank"
          rel="noreferrer"
        >
          Source on GitHub <Icon name="external" size={13} />
        </a>
      </footer>
    </>
  );
}
