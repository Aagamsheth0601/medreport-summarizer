// Presentational components: receive data through props; never call the API.

const AGENTS = [
  {
    name: "Extractor",
    verb: "Read the evidence",
    description:
      "Turns the report into validated values, units, and reference ranges.",
    icon: "scan",
  },
  {
    name: "Interpreter",
    verb: "Connect the findings",
    description:
      "Groups tests and links every out-of-range finding to its evidence.",
    icon: "nodes",
  },
  {
    name: "Communicator",
    verb: "Make it understandable",
    description:
      "Writes a plain-language explanation while preserving the limitations.",
    icon: "text",
  },
];
export const TABS = ["Overview", "Lab values", "Agent trace"];
const STATUS_LABELS = {
  normal: "Within range",
  low: "Low",
  high: "High",
  unknown: "No range",
};

export function Icon({ name, size = 20, ...props }) {
  const paths = {
    pulse: <path d="M2 12h5l3-8 4 16 3-8h5" />,
    arrow: <path d="M4 12h15m-6-6 6 6-6 6" />,
    check: <path d="m5 12 4 4L19 6" />,
    file: (
      <>
        <path d="M14 2H5v20h14V7zM14 2v6h5" />
        <path d="M8 12h8M8 16h6" />
      </>
    ),
    scan: (
      <>
        <path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5M3 12h18" />
        <path d="M8 8h8M8 16h8" />
      </>
    ),
    nodes: (
      <>
        <circle cx="5" cy="5" r="3" />
        <circle cx="19" cy="12" r="3" />
        <circle cx="5" cy="19" r="3" />
        <path d="m8 6 8 5M8 18l8-5" />
      </>
    ),
    text: (
      <>
        <rect x="3" y="3" width="18" height="18" rx="3" />
        <path d="M7 8h10M7 12h10M7 16h6" />
      </>
    ),
    download: (
      <>
        <path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5" />
      </>
    ),
    external: (
      <>
        <path d="M14 3h7v7m0-7-11 11M10 3H3v18h18v-7" />
      </>
    ),
    info: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 11v6M12 7v1" />
      </>
    ),
    close: <path d="m6 6 12 12M6 18 18 6" />,
  };
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      {paths[name] || paths.file}
    </svg>
  );
}

export function Disclaimer() {
  return (
    <aside className="disclaimer" aria-label="Portfolio disclaimer">
      <span className="notice-icon">
        <Icon name="info" size={19} />
      </span>
      <div>
        <strong>Portfolio demo · For informational purposes only</strong>
        <p>
          Built-in synthetic reports only. AI can make mistakes. This is not a
          medical tool—do not use it for diagnosis, treatment, or care
          decisions. Consult a qualified doctor about your own results.
        </p>
      </div>
      <span className="synthetic-stamp">NO REAL PATIENT DATA</span>
    </aside>
  );
}

export function ErrorNotice({ children, action, actionLabel }) {
  return (
    <div className="error-notice" role="alert">
      <Icon name="info" />
      <div>
        <strong>We couldn’t finish that step</strong>
        <p>{children}</p>
        {action && (
          <button className="text-button" onClick={action}>
            {actionLabel || "Try again"} <Icon name="arrow" size={15} />
          </button>
        )}
      </div>
    </div>
  );
}

export function AgentProgress({ run }) {
  return (
    <div className="agent-track" aria-label="Agent progress" aria-live="polite">
      {AGENTS.map((agent, i) => {
        const state = run?.stages?.[agent.name] || "waiting";
        const label = {
          waiting: "Waiting",
          started: "Working",
          completed: "Complete",
          failed: "Stopped",
        }[state];
        return (
          <div className={`agent-step ${state}`} key={agent.name}>
            <div className="step-head">
              <span className="step-icon">
                <Icon name={state === "completed" ? "check" : agent.icon} />
              </span>
              <span className="step-number">0{i + 1}</span>
            </div>
            <strong>{agent.name}</strong>
            <span className="step-purpose">{agent.verb}</span>
            <span className="step-state">
              <span />
              {label}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export function SourceReport({ sample }) {
  const rows = sample.source
    .trim()
    .split("\n")
    .slice(3)
    .map((line) => line.split("|").map((cell) => cell.trim()));
  return (
    <div className="report-sheet">
      <div className="report-heading">
        <div>
          <span className="eyebrow">SOURCE DOCUMENT</span>
          <h3>Synthetic blood report</h3>
        </div>
        <span className="document-icon">
          <Icon name="file" size={29} />
        </span>
      </div>
      <div className="report-meta">
        <span>
          Sample <strong>{sample.id}</strong>
        </span>
        <span>
          <strong>{sample.test_count}</strong> measurements
        </span>
      </div>
      <div
        className="table-scroll"
        tabIndex="0"
        role="region"
        aria-label="Source report table"
        aria-describedby="source-scroll-hint"
      >
        <table>
          <thead>
            <tr>
              <th>Test</th>
              <th>Result</th>
              <th>Unit</th>
              <th>Reference range</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row[0]}>
                {row.map((cell, i) => (
                  <td key={i} className={i === 1 ? "numeric" : ""}>
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="report-footnote">
        Fictional values and illustrative ranges. No patient identifiers.
      </p>
      <p id="source-scroll-hint" className="table-hint">Scroll the table sideways to see every column.</p>
    </div>
  );
}

export function Summary({ result }) {
  const explanation = result.explanation;
  const tests = result.extraction.tests;
  const counts = ["normal", "low", "high", "unknown"].map((status) => ({
    status,
    count: tests.filter((t) => t.status === status).length,
  }));
  return (
    <div className="summary-content">
      <div className="result-intro">
        <span className="eyebrow">THE PLAIN-LANGUAGE VIEW</span>
        <h3>What this sample tells us</h3>
        <p>{explanation.quick_summary}</p>
      </div>
      <div className="result-counts" aria-label="Test status counts">
        {counts
          .filter((c) => c.count > 0)
          .map(({ status, count }) => (
            <div key={status}>
              <span className={`count-value ${status}`}>
                {count.toString().padStart(2, "0")}
              </span>
              <span>{STATUS_LABELS[status]}</span>
            </div>
          ))}
      </div>
      <div className="section-label">
        <span>Patterns & explanations</span>
        <span>{explanation.findings_explained.length} findings</span>
      </div>
      {explanation.findings_explained.length ? (
        explanation.findings_explained.map((text, i) => (
          <article className="finding" key={i}>
            <span className="finding-index">
              {String(i + 1).padStart(2, "0")}
            </span>
            <div>
              <h4>{result.analysis.findings[i].finding}</h4>
              <p>{text}</p>
              <div className="test-tags">
                {result.analysis.findings[i].related_tests.map((name) => (
                  <span key={name}>{name}</span>
                ))}
              </div>
            </div>
          </article>
        ))
      ) : (
        <p className="empty-findings">
          No out-of-range pattern was identified in this synthetic sample.
        </p>
      )}
      <section className="within-box">
        <Icon name="check" />
        <div>
          <h4>Within the supplied ranges</h4>
          <p>{explanation.within_range}</p>
        </div>
      </section>
      <section className="limits-box">
        <h4>What this explanation cannot tell you</h4>
        <p>{explanation.limitations}</p>
      </section>
    </div>
  );
}

export function LabValues({ result }) {
  return (
    <div className="values-content">
      <div className="section-intro">
        <span className="eyebrow">THE EVIDENCE</span>
        <h3>Every value, accounted for.</h3>
        <p>
          Extracted by the first agent and checked against the synthetic source.
          “Within range” describes a value, not someone’s health.
        </p>
      </div>
      <div
        className="table-scroll"
        tabIndex="0"
        role="region"
        aria-label="Extracted lab values"
        aria-describedby="values-scroll-hint"
      >
        <table>
          <thead>
            <tr>
              <th>Test</th>
              <th>Result</th>
              <th>Reference</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {result.extraction.tests.map((test) => (
              <tr key={test.test_name}>
                <td>{test.test_name}</td>
                <td>
                  <strong className="numeric">{test.value}</strong>
                  <span className="unit">{test.unit}</span>
                </td>
                <td>{test.reference_text}</td>
                <td>
                  <span className={`status-chip ${test.status}`}>
                    {STATUS_LABELS[test.status]}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p id="values-scroll-hint" className="table-hint">Scroll the table sideways to see every column.</p>
      {result.extraction.warnings.length > 0 && (
        <div className="limits-box">
          <h4>Extraction notes</h4>
          {result.extraction.warnings.map((w) => (
            <p key={w}>{w}</p>
          ))}
        </div>
      )}
      <p className="small-note">
        Strict boundaries are preserved: a result of 200 is outside a reference
        range of &lt; 200. Missing ranges remain unknown.
      </p>
    </div>
  );
}

export function Trace({ result, sample }) {
  const outputs = [result.extraction, result.analysis, result.explanation];
  const inputs = [
    sample.source,
    result.extraction,
    { extraction: result.extraction, analysis: result.analysis },
  ];
  return (
    <div className="trace-content">
      <div className="section-intro">
        <span className="eyebrow">UNDER THE HOOD</span>
        <h3>Three agents. A visible handoff.</h3>
        <p>
          Inspect the data sent to each agent and the output it returned. These
          are structured results, not hidden model reasoning.
        </p>
      </div>
      {AGENTS.map((agent, i) => (
        <details className="trace-card" key={agent.name} open={i === 0}>
          <summary>
            <span className="trace-icon">
              <Icon name={agent.icon} />
            </span>
            <span>
              <strong>
                0{i + 1} / {agent.name}
              </strong>
              <small>{agent.description}</small>
            </span>
            <span className="trace-check">
              <Icon name="check" size={16} /> Validated
            </span>
            <span className="expand-sign">+</span>
          </summary>
          <div className="trace-body">
            <div>
              <h4>Input</h4>
              <pre tabIndex="0">
                {typeof inputs[i] === "string"
                  ? inputs[i]
                  : JSON.stringify(inputs[i], null, 2)}
              </pre>
            </div>
            <div>
              <h4>Output</h4>
              <pre tabIndex="0">{JSON.stringify(outputs[i], null, 2)}</pre>
            </div>
          </div>
        </details>
      ))}
      <div className="trace-note">
        <Icon name="info" />
        <p>
          Validation checks structure, evidence, and coverage. It does not prove
          that an AI-generated explanation is medically correct.
        </p>
      </div>
    </div>
  );
}
