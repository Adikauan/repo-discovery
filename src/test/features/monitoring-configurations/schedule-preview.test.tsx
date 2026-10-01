import { render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import { NextOccurrencePreview } from '../../../features/monitoring-configurations/components/NextOccurrencePreview';

const occurrence = { instant: '2026-10-01T12:00:00Z', timezone: 'UTC', localDateTime: '2026-10-01T12:00:00' };

it('announces loading, successful timezone-aware preview, and disabled/no-schedule states safely', () => {
  const { rerender } = render(<NextOccurrencePreview occurrence={null} loading hasSchedule={false} enabled />);
  expect(screen.getByRole('status')).toHaveTextContent('Calculating next scheduled occurrence');

  rerender(<NextOccurrencePreview occurrence={occurrence} loading={false} hasSchedule={false} enabled />);
  expect(screen.getByRole('status')).toHaveTextContent('Next scheduled occurrence (preview)');
  expect(screen.getByRole('status')).toHaveTextContent('(UTC)');
  expect(screen.getByRole('status')).toHaveTextContent('not a guaranteed execution');

  rerender(<NextOccurrencePreview occurrence={null} loading={false} hasSchedule enabled />);
  expect(screen.getByRole('status')).toHaveTextContent('Preview the current draft');
  rerender(<NextOccurrencePreview occurrence={null} loading={false} hasSchedule enabled={false} />);
  expect(screen.getByRole('status')).toHaveTextContent('No next scheduled occurrence is available');

  rerender(<NextOccurrencePreview occurrence={null} loading={false} hasSchedule={false} enabled />);
  expect(screen.queryByRole('status')).not.toBeInTheDocument();
});
