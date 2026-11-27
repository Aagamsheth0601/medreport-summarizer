import { useEffect, useRef, useState } from "react";
import { downloadFile, liveRunsEnabled, requestLive, requestRecorded } from "./api.js";
import { TABS, Icon, Disclaimer, ErrorNotice, AgentProgress, SourceReport,
         Summary, LabValues, Trace } from "./components.jsx";

// App owns sample selection, job state, and reconnectable polling.
export default function App() {
  const [mode, setMode] = useState("recorded");
  const [samples, setSamples] = useState([]);
  const [selectedId, setSelectedId] = useState("mixed-patterns");
  const [loadError, setLoadError] = useState("");
  const [loadAttempt, setLoadAttempt] = useState(0);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [run, setRun] = useState(null);
  const [requestError, setRequestError] = useState("");
  const [pollError, setPollError] = useState("");
  const [pollRetry, setPollRetry] = useState(0);
  const [tab, setTab] = useState("Overview");
  const mounted = useRef(true);
  const isLive = mode === "live";
  const request = isLive ? requestLive : requestRecorded;
  const selected = samples.find((sample) => sample.id === selectedId);
  const result = run?.result;
  const busy = submitting || run?.status === "running";
  const recordedRunLabel = result ? "Reopen report" : "Explore this report";
  const liveProgressLabel = submitting ? "Starting live run…" : "Running live…";

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setLoadError("");
    request("/api/samples")
      .then((data) => {
        if (active) setSamples(data);
      })
      .catch((error) => {
        if (active) setLoadError(error.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [request, loadAttempt]);

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
  }, [request, run?.id, run?.status, pollRetry]);

  function selectSample(id) {
    if (busy) return;
    setSelectedId(id);
    setRun(null);
    setRequestError("");
    setPollError("");
    setTab("Overview");
  }

  function changeMode(nextMode) {
    if (busy || mode === nextMode) return;
    selectSample(selectedId);
    setSamples([]);
    setLoadError("");
    setLoading(true);
    setMode(nextMode);
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
            (isLive && !error.status
              ? " If the request reached the server, wait before starting another run."
              : ""),
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
          <span>MedReport</span>
        </a>
        <nav aria-label="Main navigation">
          <a href="#workspace">Reports</a>
          <a href="#architecture">How it works</a>
          <a
            className="repo-link"
            href="https://github.com/Aagamsheth0601/medreport-summarizer"
            target="_blank"
            rel="noreferrer"
          >
            Source <Icon name="external" size={14} />
          </a>
        </nav>
      </header>
      <main>
        <section className="hero">
          <div className="hero-copy">
            <h1>Read a <em>lab report.</em></h1>
            <p>Pick a sample, check the numbers against their ranges, and see where each explanation came from.</p>
            <a className="hero-cta" href="#workspace">
              Open the reports <Icon name="arrow" size={17} />
            </a>
          </div>
          <figure className="reference-example">
            <figcaption><Icon name="file" size={17} /> From the boundary sample</figcaption>
            <div className="reference-reading">
              <div>
                <strong>Total cholesterol</strong>
                <div>200 <small>mg/dL</small></div>
              </div>
              <span className="reference-limit">Range &lt; 200</span>
            </div>
            <div className="reference-track" aria-hidden="true"><span /></div>
            <p>200 sits exactly at the cutoff. This range excludes it.</p>
          </figure>
        </section>
        <Disclaimer />
        <section className="workspace" id="workspace" tabIndex="-1">
          <div className="workspace-heading">
            <h2>Report workspace</h2>
            {!liveRunsEnabled && (
              <span className="workspace-caption"><span className="mode-dot" /> Recorded demo</span>
            )}
          </div>
          {liveRunsEnabled && (
            <fieldset className="report-mode" disabled={busy}>
              <legend className="sr-only">Report mode</legend>
              <label>
                <input
                  type="radio"
                  name="report-mode"
                  checked={!isLive}
                  onChange={() => changeMode("recorded")}
                />
                Recorded demo
              </label>
              <label>
                <input
                  type="radio"
                  name="report-mode"
                  checked={isLive}
                  onChange={() => changeMode("live")}
                />
                Live Gemini
              </label>
            </fieldset>
          )}
          {loadError ? (
            <ErrorNotice action={() => setLoadAttempt((count) => count + 1)}>{loadError}</ErrorNotice>
          ) : loading ? (
            <div className="loading-state" role="status">
              Loading the sample library…
            </div>
          ) : (
            selected && (
              <div className="workspace-grid">
                <aside className="sample-sidebar">
                  <div className="sidebar-heading">
                    <h3>Samples</h3>
                  </div>
                  <fieldset className="sample-options" disabled={busy}>
                    <legend className="sr-only">
                      Built-in synthetic reports
                    </legend>
                    {samples.map((sample) => (
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
                        <span className="sample-card-title">
                          <strong>{sample.title}</strong>
                          <span className="selection-dot" aria-hidden="true" />
                        </span>
                        <span className="sample-subtitle">
                          {sample.subtitle}
                        </span>
                        <span className="sample-measurements">{sample.test_count} measurements</span>
                      </label>
                    ))}
                  </fieldset>
                  <div className="sample-description">
                    <Icon name="info" size={17} />
                    <p>{selected.description}</p>
                  </div>
                </aside>
                <div className="analysis-workspace">
                  <section className="pipeline-card">
                    <div className="card-heading">
                      <h3>Run progress</h3>
                      <button
                        className="run-button"
                        onClick={startRun}
                        disabled={busy}
                      >
                        {busy ? (
                          <>
                            <span className="spinner" />{" "}
                            {isLive ? liveProgressLabel : "Opening recorded demo…"}
                          </>
                        ) : (
                          <>
                            {isLive ? "Run live" : recordedRunLabel}
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
                                : "Ready"}
                      </span>
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
                            <p>
                              {busy
                                ? "The result will appear here when the run finishes."
                                : isLive
                                  ? "Run the selected sample to see a fresh explanation."
                                  : "Open the selected sample to see its saved explanation."}
                            </p>
                          </div>
                          <SourceReport key={selected.id} sample={selected} />
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
                        <span>{isLive ? "Live output" : "Recorded output"} · {result.model}</span>
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
          <h2>How it works</h2>
          <div className="architecture-features">
            <article>
              <Icon name="scan" />
              <h3>Read the report</h3>
              <p>The Extractor reads the names, values, units, and ranges printed in the report.</p>
            </article>
            <article>
              <Icon name="nodes" />
              <h3>Check the findings</h3>
              <p>Python checks the values against the source. The Interpreter links each finding to the relevant tests.</p>
            </article>
            <article>
              <Icon name="text" />
              <h3>Explain the results</h3>
              <p>The Communicator writes an explanation for each finding. A failed check stops the run.</p>
            </article>
          </div>
        </section>
      </main>
      <footer className="site-footer">
        <span className="footer-brand">
          <Icon name="pulse" size={18} /> MedReport
        </span>
        <span>Built by Aagam Sheth</span>
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
