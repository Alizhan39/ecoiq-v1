import { useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import ReactFlow, { Background, Controls, type Node } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { getFormulaFlow, previewFormulaSequence } from '@/api/formulaFlow';
import type {
  FormulaCandidate, FormulaObservations, FormulaResult, FormulaRun,
} from '@/api/formulaFlow';
import { useApi } from '@/hooks/useApi';
import { ErrorState, Loading } from '@/components/States';
import './FormulaFlow.css';

type FieldState = Record<string, Record<string, { value: string; source_ref: string }>>;

function buildObservations(
  formulas: FormulaCandidate[], fields: FieldState,
): { observations: FormulaObservations; partial: boolean; count: number } {
  const observations: FormulaObservations = {};
  let partial = false;
  let count = 0;
  for (const formula of formulas) {
    const rows = formula.required_inputs.map((item) => fields[formula.key]?.[item.key]
      ?? { value: '', source_ref: '' });
    const started = rows.some((row) => row.value.trim() || row.source_ref.trim());
    if (!started) continue;
    if (rows.some((row) => !row.value.trim() || !row.source_ref.trim())) {
      partial = true;
      continue;
    }
    observations[formula.key] = {};
    formula.required_inputs.forEach((input, index) => {
      const row = rows[index];
      if (row) {
        observations[formula.key]![input.key] = {
          value: row.value.trim(), source_ref: row.source_ref.trim(),
        };
      }
    });
    count += 1;
  }
  return { observations, partial, count };
}

export default function FormulaFlow() {
  const { projectSlug } = useParams<{ projectSlug: string }>();
  const state = useApi((signal) => getFormulaFlow(projectSlug ?? '', signal), [projectSlug]);
  const [selected, setSelected] = useState<string | null>(null);
  const [period, setPeriod] = useState('');
  const [fields, setFields] = useState<FieldState>({});
  const [run, setRun] = useState<FormulaRun | null>(null);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const formulas = state.status === 'ready' ? state.data.formulas : [];
  const chosen = formulas.find((f) => f.key === selected) ?? formulas[0];
  const results = useMemo(() => new Map<string, FormulaResult>(
    (run?.results ?? []).map((item) => [item.formula_key, item]),
  ), [run]);
  const graphNodes: Node[] = useMemo(() => {
    if (state.status !== 'ready') return [];
    return state.data.nodes.map((node) => ({
      ...node,
      data: { ...node.data, label: `${node.data.ordinal}. ${node.data.label}` },
      className: [
        'formula-flow__node',
        node.id === chosen?.key ? 'formula-flow__node--selected' : '',
        results.get(node.id)?.status === 'REPORTED_NOT_VERIFIED' ? 'formula-flow__node--calculated' : '',
      ].filter(Boolean).join(' '),
    }));
  }, [state, chosen?.key, results]);

  function updateField(formulaKey: string, inputKey: string,
                       property: 'value' | 'source_ref', value: string) {
    setRun(null);
    setMessage(null);
    setFields((current) => {
      const row = current[formulaKey]?.[inputKey] ?? { value: '', source_ref: '' };
      return {
        ...current,
        [formulaKey]: {
          ...current[formulaKey],
          [inputKey]: { ...row, [property]: value },
        },
      };
    });
  }

  async function calculate() {
    if (state.status !== 'ready' || pending || !projectSlug) return;
    setMessage(null);
    setRun(null);
    const prepared = buildObservations(formulas, fields);
    if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(period)) {
      setMessage('Enter a reporting month in YYYY-MM format.');
      return;
    }
    if (prepared.partial) {
      setMessage('Complete both the value and source ID for every started formula input.');
      return;
    }
    if (prepared.count === 0) {
      setMessage('Enter measurements and source IDs for at least one formula.');
      return;
    }
    setPending(true);
    try {
      const response = await previewFormulaSequence(projectSlug, period, prepared.observations);
      setRun(response);
    } catch {
      setMessage('The server rejected the calculation. Check values, permissions and sources.');
    } finally {
      setPending(false);
    }
  }

  if (state.status === 'loading') return <Loading label="Loading private formula catalogue" />;
  if (state.status === 'error') return <ErrorState error={state.error} />;
  if (!chosen) return <p role="status">There are no candidate formulas to display.</p>;

  return (
    <div className="formula-flow">
      <header className="prose">
        <p><a href={`/business-os/formulas/${encodeURIComponent(projectSlug ?? '')}/`}>← Formula Studio</a></p>
        <h1>Business Plan 2.0 · KPI Formula Flow</h1>
        <p>Twenty provisional formulas, in the versioned EcoIQ registry order. This
          diagram is a visual review tool, not an AI agent or executable workflow.</p>
        <p role="note" className="formula-flow__warning">
          All outputs are drafts. Source identifiers are supplied by the user and
          are <strong>not independently verified</strong>. No formulas are published,
          approved or sent to an external AI model.
        </p>
      </header>
      <section aria-labelledby="formula-graph-heading">
        <h2 id="formula-graph-heading">Sequential KPI diagram</h2>
        <div className="formula-flow__canvas" aria-label="Read-only KPI flow diagram">
          <ReactFlow
            nodes={graphNodes}
            edges={state.data.edges}
            onNodeClick={(_event, node) => setSelected(node.id)}
            nodesDraggable={false}
            nodesConnectable={false}
            edgesReconnectable={false}
            fitView
            colorMode="system"
          >
            <Background />
            <Controls showInteractive={false} />
          </ReactFlow>
        </div>
        <details className="formula-flow__order">
          <summary>Accessible step-by-step list (all 20 formulas)</summary>
          <ol>
            {formulas.map((formula) => (
              <li key={formula.key}>
                <button type="button" onClick={() => setSelected(formula.key)}
                  aria-current={chosen.key === formula.key ? 'step' : undefined}>
                  {formula.title}
                </button>
                <span className="formula-flow__status">
                  {results.get(formula.key)?.status ?? 'NOT_RUN'}
                </span>
              </li>
            ))}
          </ol>
        </details>
      </section>
      <section className="formula-flow__editor" aria-labelledby="formula-inputs-heading">
        <div>
          <h2 id="formula-inputs-heading">{chosen.title}</h2>
          <p><code>{chosen.expression}</code></p>
          <p>Output unit: <strong>{chosen.output_unit}</strong>. {chosen.interpretation_limit}</p>
          <p className="formula-flow__status">{chosen.validation_status}</p>
          <div className="formula-flow__input-grid">
            {chosen.required_inputs.map((input) => (
              <div key={input.key} className="formula-flow__field">
                <label htmlFor={`formula-value-${input.key}`}>
                  {input.key} ({input.unit})
                </label>
                <input id={`formula-value-${input.key}`} type="text" inputMode="decimal"
                  placeholder="Exact non-negative decimal"
                  value={fields[chosen.key]?.[input.key]?.value ?? ''}
                  onChange={(event) => updateField(chosen.key, input.key, 'value', event.target.value)} />
                <label htmlFor={`formula-source-${input.key}`}>Source ID (unverified)</label>
                <input id={`formula-source-${input.key}`} type="text" maxLength={120}
                  value={fields[chosen.key]?.[input.key]?.source_ref ?? ''}
                  onChange={(event) => updateField(chosen.key, input.key, 'source_ref', event.target.value)} />
              </div>
            ))}
          </div>
          <p className="formula-flow__help">Select additional nodes to prepare multiple
            formulas. The server calculates all supplied formulas in fixed registry order,
            and explicitly labels unsupplied formulas.</p>
        </div>
        <div className="formula-flow__actions">
          <label htmlFor="formula-period">Reporting period (YYYY-MM)</label>
          <input id="formula-period" type="month" value={period}
            onChange={(event) => { setPeriod(event.target.value); setRun(null); }} />
          <button type="button" onClick={() => { void calculate(); }} disabled={pending}>
            {pending ? 'Calculating…' : 'Run deterministic preview in sequence'}
          </button>
          {message && <p role="alert">{message}</p>}
          {run && (
            <div role="status" aria-live="polite">
              <h3>Server-side preview · {run.period}</h3>
              <p>Sequential steps: {run.results.length}. No AI call or publication.</p>
              <ol className="formula-flow__results">
                {run.results.map((result) => (
                  <li key={result.formula_key}>
                    <strong>{result.sequence}. {result.formula_key}</strong>
                    <span>{result.value_decimal ?? '—'} {result.unit}</span>
                    <small>{result.status}</small>
                  </li>
                ))}
              </ol>
            </div>
          )}
        </div>
      </section>
      <p className="formula-flow__footer">
        <Link to="/trust">Evidence policy</Link> · Only reviewed evidence can
        support verified conclusions. No religious verdicts are generated.
      </p>
    </div>
  );
}
