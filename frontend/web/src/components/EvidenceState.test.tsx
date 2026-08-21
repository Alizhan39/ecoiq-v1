import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { EvidenceSummary, RankDisplay, ScoreDisplay } from './EvidenceState';

describe('ScoreDisplay', () => {
  it('shows a published score', () => {
    render(
      <ScoreDisplay
        company={{ score_status: 'PUBLISHED', ecoiq_score: 76.4 }}
      />,
    );

    expect(screen.getByText('76.4')).toBeInTheDocument();
  });

  it('shows a genuine zero rather than treating it as missing', () => {
    render(
      <ScoreDisplay company={{ score_status: 'PUBLISHED', ecoiq_score: 0 }} />,
    );

    expect(screen.getByText('0.0')).toBeInTheDocument();
    expect(screen.queryByText(/pending/i)).not.toBeInTheDocument();
  });

  it('shows an evidence-pending state instead of a placeholder number', () => {
    render(
      <ScoreDisplay
        company={{ score_status: 'INSUFFICIENT_EVIDENCE', ecoiq_score: null }}
        note="Not enough verified evidence."
      />,
    );

    expect(screen.getByText(/Evidence assessment pending/i)).toBeInTheDocument();
    expect(screen.getByText('Not enough verified evidence.')).toBeInTheDocument();
    expect(screen.queryByText('0')).not.toBeInTheDocument();
    expect(screen.queryByText('0.0')).not.toBeInTheDocument();
  });
});

describe('EvidenceSummary', () => {
  it('renders coverage and confidence separately', () => {
    render(<EvidenceSummary coverage={78} confidence="HIGH" />);

    expect(screen.getByText('78%')).toBeInTheDocument();
    expect(screen.getByText('High')).toBeInTheDocument();
  });

  it('renders zero coverage as a real measurement', () => {
    render(<EvidenceSummary coverage={0} confidence="INSUFFICIENT_EVIDENCE" />);

    expect(screen.getByText('0%')).toBeInTheDocument();
  });

  it('never renders confidence as a percentage', () => {
    const { container } = render(
      <EvidenceSummary coverage={40} confidence="MEDIUM" />,
    );

    expect(container.textContent).toContain('Medium');
    expect(container.textContent).not.toContain('Medium%');
  });
});

describe('RankDisplay', () => {
  it('shows a rank when there is one', () => {
    render(<RankDisplay rank={12} />);
    expect(screen.getByText('#12')).toBeInTheDocument();
  });

  it('shows an em dash rather than inventing a rank', () => {
    render(<RankDisplay rank={null} />);

    expect(screen.getByText('—')).toBeInTheDocument();
    expect(screen.queryByText('#0')).not.toBeInTheDocument();
  });
});
