import { useState } from 'react';
import {
  getProcessFormulaContract, previewProcessFormulas,
} from '@/api/processFormulaReview';
import type {
  ProcessFormulaContract, ProcessFormulaReport, ProcessMeasure,
} from '@/api/processFormulaReview';

type Draft = Record<string, { value: string; source_ref: string }>;

export default function ProcessFormulaReviewPanel({
  projectSlug, onReport,
}: {
  projectSlug: string;
  onReport: (report: ProcessFormulaReport | null) => void;
}) {
  const [runIdText, setRunIdText] = useState('');
  const [contract, setContract] = useState<ProcessFormulaContract | null>(null);
  const [draft, setDraft] = useState<Draft>({});
  const [report, setReport] = useState<ProcessFormulaReport | null>(null);
  const [selectedFormula, setSelectedFormula] = useState<string>('');
  const [message, setMessage] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function loadProcess() {
    const id = Number(runIdText);
    setContract(null);
    setDraft({});
    setReport(null);
    onReport(null);
    if (!/^[1-9][0-9]{0,11}$/.test(runIdText) || !Number.isSafeInteger(id)) {
      setMessage('Enter a valid positive process-analysis ID.');
      return;
    }
    setMessage(null);
    setPending(true);
    try {
      const data = await getProcessFormulaContract(projectSlug, id);
      setContract(data);
      setSelectedFormula(data.formulas[0]?.key ?? '');
    } catch {
      setMessage('Process is unavailable or access is not authorised.');
    } finally {
      setPending(false);
    }
  }

  async function calculate() {
    if (pending || !contract?.can_preview_calculate) return;
    setMessage(null);
    setReport(null);
    onReport(null);
    const measurements: Record<string, ProcessMeasure> = {};
    let incomplete = false;
    for (const parameter of contract.parameters) {
      const record = draft[parameter.key] ?? { value: '', source_ref: '' };
      const value = record.value.trim();
      const source = record.source_ref.trim();
      if (!value && !source) continue; // Missing is explicitly reported by server.
      if (!value || !source) {
        incomplete = true;
        break;
      }
      measurements[parameter.key] = {
        value, unit: parameter.unit, source_ref: source,
      };
    }
    if (incomplete) {
      setMessage('Complete both value and source ID for each started parameter.');
      return;
    }
    setPending(true);
    try {
      const result = await previewProcessFormulas(
        projectSlug, contract.process_analysis_id, measurements,
      );
      setReport(result);
      onReport(result);
    } catch {
      setMessage('Process formula preview rejected. Check the values and access permissions.');
    } finally {
      setPending(false);
    }
  }

  const selected = contract?.formulas.find((f) => f.key === selectedFormula);
  const needed = new Set(selected?.required_inputs.map((i) => i.key) ?? []);

  return (
    <section className="formula-flow__process" aria-labelledby="process-formula-title">
      <h2 id="process-formula-title">Run all 20 KPIs for an existing process</h2>
      <p>This review reads the process identity and reporting month from EcoIQ
        history. The original CSV measurements are not stored. Enter exact,
        source-labelled measurements; unknown values remain missing, never zero.</p>
      <div className="formula-flow__process-picker">
        <label htmlFor="process-run-id">Saved process analysis ID</label>
        <input id="process-run-id" type="text" inputMode="numeric" value={runIdText}
          onChange={(e) => { setRunIdText(e.target.value); setContract(null); setReport(null); onReport(null); }}
          placeholder="e.g. 12" />
        <button type="button" onClick={() => { void loadProcess(); }} disabled={pending}>
          Load process
        </button>
      </div>
      {message && <p role="alert">{message}</p>}
      {contract && (
        <div className="formula-flow__process-details">
          <p><strong>{contract.process_name}</strong> · {contract.case_id} ·
            {contract.domain} · {contract.period}</p>
          <p>All formulas are assessed in registry order. Only formulas with
            complete supplied parameters can be calculated. No automatic
            applicability exclusions, publication or AI inference.</p>
          <label htmlFor="process-selected-formula">Inspect required inputs for KPI</label>
          <select id="process-selected-formula" value={selectedFormula}
            onChange={(e) => setSelectedFormula(e.target.value)}>
            {contract.formulas.map((f) => (
              <option key={f.key} value={f.key}>{f.title}</option>
            ))}
          </select>
          <p>
            Selected KPI requires: {selected?.required_inputs.map((i) => i.key).join(', ') || '—'}.
            Shared parameters are entered once and reused where units match.
          </p>
          <details>
            <summary>Enter measurements ({contract.parameters.length} available parameters)</summary>
            <div className="formula-flow__parameter-grid">
              {contract.parameters.map((parameter) => {
                const current = draft[parameter.key] ?? { value: '', source_ref: '' };
                return (
                  <div key={parameter.key} className="formula-flow__field">
                    <label htmlFor={`process-measure-${parameter.key}`}>
                      {parameter.key} ({parameter.unit}) {needed.has(parameter.key) ? '• selected KPI' : ''}
                    </label>
                    <input id={`process-measure-${parameter.key}`} type="text"
                      inputMode="decimal" value={current.value}
                      placeholder="Exact decimal"
                      onChange={(e) => {
                        const value = e.target.value;
                        setDraft((s) => ({ ...s, [parameter.key]: { ...current, value } }));
                        setReport(null); onReport(null);
                      }} />
                    <label htmlFor={`process-source-${parameter.key}`}>Source identifier</label>
                    <input id={`process-source-${parameter.key}`} type="text"
                      maxLength={120} value={current.source_ref}
                      onChange={(e) => {
                        const source_ref = e.target.value;
                        setDraft((s) => ({ ...s, [parameter.key]: { ...current, source_ref } }));
                        setReport(null); onReport(null);
                      }} />
                    <small>Used by: {parameter.used_by.join(', ')}</small>
                  </div>
                );
              })}
            </div>
          </details>
          <button type="button" onClick={() => { void calculate(); }}
            disabled={pending || !contract.can_preview_calculate}>
            {pending ? 'Evaluating…' : 'Evaluate all 20 KPI candidates'}
          </button>
          {!contract.can_preview_calculate && (
            <p role="note">Viewing is permitted; calculation requires ANALYSE access.</p>
          )}
          {report && (
            <div role="status" aria-live="polite">
              <h3>20-KPI process coverage — unverified draft</h3>
              <p>Reported results: {report.counts.reported_not_verified};
                missing measurements: {report.counts.needs_measurements};
                blocked: {report.counts.blocked}.</p>
              <ol className="formula-flow__results">
                {report.results.map((r) => (
                  <li key={r.formula_key}>
                    <strong>{r.sequence}. {r.formula_key}</strong>
                    <span>{r.value_decimal ?? '—'} {r.unit}</span>
                    <small>{r.status}</small>
                    {r.missing_inputs.length > 0 && (
                      <small>Missing: {r.missing_inputs.join(', ')}</small>
                    )}
                  </li>
                ))}
              </ol>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
