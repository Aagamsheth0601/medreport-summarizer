// Public portfolio: load recorded real outputs, never request a live model.
let demoPromise;
export async function request(path, options = {}) {
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

export function downloadFile(filename, contents, type) {
  const url = URL.createObjectURL(new Blob([contents], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
