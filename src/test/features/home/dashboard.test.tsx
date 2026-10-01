import { fireEvent, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { renderApp } from '../../renderApp';
afterEach(() => vi.unstubAllGlobals());

const summary = {
  window: { start: '2026-09-24T00:00:00Z', end: '2026-09-30T12:00:00Z', timezone: 'UTC' },
  metrics: { executionCount: 1, repositoriesProcessed: 2, findingCount: 1, successRatePercent: 100, terminalExecutionCount: 1 },
  statusDistribution: { pending: 0, running: 0, completed: 1, partiallyCompleted: 0, failed: 0 },
  dailyExecutions: Array.from({ length: 7 }, (_, index) => ({ date: `2026-09-${String(index + 24).padStart(2, '0')}`, count: index === 6 ? 1 : 0 })),
  recentExecutions: [{ id: 'exec-001', configurationName: 'Production', status: 'completed', triggerType: 'manual', createdAt: '2026-09-30T11:00:00Z', startedAt: '2026-09-30T11:00:01Z', completedAt: '2026-09-30T11:00:03Z', durationSeconds: 2, findingCount: 1 }],
  findingsByRule: [{ ruleId: 'unauthorized_commit_author', label: 'Unauthorized commit author', count: 1 }],
};
function json(body: unknown, status = 200) { return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }); }

it('renders only summary-backed dashboard values and the implemented finding rule', async () => {
  const fetchMock = vi.fn().mockResolvedValue(json(summary)); vi.stubGlobal('fetch', fetchMock);
  renderApp('/');
  expect(await screen.findByText('Production')).toBeInTheDocument();
  expect(screen.getByText('Unauthorized commit author')).toBeInTheDocument();
  expect(screen.queryByText(/keyword|semantic|table discovery/i)).not.toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledTimes(1);
  expect(String(fetchMock.mock.calls[0][0])).toContain('/dashboard/summary');
});

it('shows honest empty metrics and safely recovers after an API failure', async () => {
  const empty = { ...summary, metrics: { executionCount: 0, repositoriesProcessed: 0, findingCount: 0, successRatePercent: null, terminalExecutionCount: 0 }, recentExecutions: [], findingsByRule: [], statusDistribution: { pending: 0, running: 0, completed: 0, partiallyCompleted: 0, failed: 0 }, dailyExecutions: summary.dailyExecutions.map(day => ({ ...day, count: 0 })) };
  const fetchMock = vi.fn().mockResolvedValueOnce(json({ detail: 'Dashboard unavailable.' }, 500)).mockResolvedValueOnce(json(empty)); vi.stubGlobal('fetch', fetchMock);
  renderApp('/');
  expect(await screen.findByText('Dashboard unavailable.')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Retry' }));
  expect(await screen.findByText('No recent executions')).toBeInTheDocument();
  expect(screen.getByText('No findings detected')).toBeInTheDocument();
  expect(screen.queryByText('0%')).not.toBeInTheDocument();
});

it('shows a safe error when a successful response does not match the dashboard contract', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json({ items: [] })));
  renderApp('/');
  expect(await screen.findByText('Dashboard summary is unavailable.')).toBeInTheDocument();
  expect(screen.queryByText('Unexpected Application Error!')).not.toBeInTheDocument();
});
