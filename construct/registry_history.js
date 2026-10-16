// Run in the ClinicalTrials.gov browser console; select the local panel roster.
// Only registry identifiers are sent to ClinicalTrials.gov. The roster stays local.
(async () => {
  if (location.origin !== "https://clinicaltrials.gov") {
    throw new Error("Open ClinicalTrials.gov before running this capture script");
  }
  const picker = document.createElement("input");
  picker.type = "file";
  picker.accept = ".json";
  const file = new Promise((resolve) => {
    picker.onchange = () => resolve(picker.files[0]);
  });
  picker.click();
  const roster = JSON.parse(await (await file).text());
  if (!Array.isArray(roster) || !roster.length || roster.some(r => !/^NCT\d{8}$/.test(r.nct))) {
    throw new Error("Expected a nonempty panel roster with registry identifiers");
  }
  const captures = {};
  const get = async (url) => {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`Registry request failed: HTTP ${response.status}`);
    return response.json();
  };
  for (const nct of [...new Set(roster.map(r => r.nct))]) {
    const base = `/api/int/studies/${nct}`;
    const overview = await get(`${base}?history=true`);
    const changes = overview.history.changes;
    if (!Array.isArray(changes) || !changes.length) throw new Error("Missing version index");
    const versions = [];
    for (const change of [...changes].sort((a, b) => a.version - b.version)) {
      const record = await get(`${base}/history/${change.version}`);
      if (record.studyVersion !== change.version || !record.study?.protocolSection) {
        throw new Error("Registry version schema mismatch");
      }
      versions.push(record);
    }
    captures[nct] = {retrieved_at: new Date().toISOString(), overview, versions};
  }
  const url = URL.createObjectURL(new Blob([JSON.stringify(captures)], {type: "application/json"}));
  const download = document.createElement("a");
  download.href = url;
  download.download = "registry_history.json";
  download.click();
  URL.revokeObjectURL(url);
  console.log("Registry histories captured:", Object.keys(captures).length);
})();
