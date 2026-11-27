// This milestone enables live requests in an explicitly opted-in dev session.
export const liveRunsEnabled = import.meta.env.DEV && import.meta.env.VITE_ENABLE_LIVE_RUNS === "true";

let demoPromise;
export async function requestRecorded(path, options = {}) {
  try {
    if (!demoPromise) demoPromise = fetch('/demo.json').then(response => {
      if (!response.ok) throw new Error('Demo unavailable');
      return response.json();
    }).catch(error => { demoPromise = null; throw error; });
    const demo = await demoPromise;
    if (path === '/api/samples') return demo.samples;
    if (path === '/api/runs') {
      const { sample_id } = JSON.parse(options.body);
      if (!demo.results[sample_id]) throw new Error('Unknown sample');
      return { id: sample_id };
    }
    const id = path.split('/').pop();
    if (!demo.results[id]) throw new Error('Unknown sample');
    return { id, sample_id: id, status: 'completed',
      stages: { Extractor: 'completed', Interpreter: 'completed', Communicator: 'completed' },
      result: demo.results[id] };
  } catch {
    throw new Error('The recorded demo could not load. Check your connection and try again.');
  }
}

export async function requestLive(path, options = {}) {
  let response;
  try {
    response = await fetch(path, { ...options, cache: "no-store" });
  } catch {
    throw new Error("Could not reach the live API. Check that FastAPI is running.");
  }

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const message = typeof payload?.detail === "string"
      ? payload.detail
      : `The live API request failed (HTTP ${response.status}). Check that FastAPI is running.`;
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }
  if (payload === null) throw new Error("The live API returned an unreadable response.");
  return payload;
}

export function downloadFile(filename, contents, type) {
  const url = URL.createObjectURL(new Blob([contents], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
