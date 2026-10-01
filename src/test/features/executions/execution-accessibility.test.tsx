import axe from 'axe-core';
import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import { renderApp } from '../../renderApp';
import { mockOtherRequests, response } from './fixtures';
import { SplitDiffViewer } from '../../../features/executions/components/SplitDiffViewer';
import { parseSplitDiff } from '../../../features/executions/utils/splitDiffParser';
afterEach(() => vi.unstubAllGlobals());

it.each(['/executions','/executions/execution-1','/monitoring-configurations/config-1/executions','/monitoring-configurations/config-1'])('has accessible execution controls at %s', async path => {
  vi.stubGlobal('fetch', vi.fn().mockImplementation((url: string) => Promise.resolve(mockOtherRequests(url))));
  renderApp(path);
  if (path === '/executions/execution-1') await screen.findByRole('heading', { name: 'Execution execution-1' });
  else if (path.endsWith('config-1')) await screen.findByRole('button', { name: 'Run manual execution' });
  else await screen.findByRole('table', { name: 'Execution history' });
  const result = await axe.run(document.body, {
    runOnly: { type: 'tag', values: ['wcag2a','wcag2aa','wcag21aa','wcag22aa'] },
    rules: { 'color-contrast': { enabled: false } },
  });
  expect(result.violations).toEqual([]);
});

it('provides semantic accessible dashboard tabs, metrics, status, and keyboard operation', async () => {
  vi.stubGlobal('fetch', vi.fn().mockImplementation((url: string) => Promise.resolve(mockOtherRequests(url))));
  renderApp('/executions/execution-1');
  await screen.findByRole('heading', { name: 'Execution execution-1' });
  const tablist = screen.getByRole('tablist', { name: 'Execution sections' });
  expect(tablist).toBeInTheDocument();
  expect(screen.getByRole('tab', { name: 'Overview' })).toHaveAttribute('aria-selected', 'true');
  expect(screen.getByRole('tab', { name: 'Repositories' })).toHaveAttribute('aria-controls');
  expect(screen.getByRole('tabpanel', { name: 'Overview' })).toBeInTheDocument();
  expect(screen.getAllByText('Completed').length).toBeGreaterThan(0);
  expect(screen.getByText('Repositories', { selector: 'p' })).toBeInTheDocument();
  const user = userEvent.setup();
  act(() => screen.getByRole('tab', { name: 'Overview' }).focus());
  await user.keyboard('{ArrowRight}');
  expect(screen.getByRole('tab', { name: 'Repositories' })).toHaveFocus();
  await user.keyboard('{Enter}');
  expect(screen.getByRole('tab', { name: 'Repositories' })).toHaveAttribute('aria-selected', 'true');
  const result = await axe.run(document.body, { runOnly: { type: 'tag', values: ['wcag2a','wcag2aa','wcag21aa','wcag22aa'] }, rules: { 'color-contrast': { enabled: false } } });
  expect(result.violations).toEqual([]);
});

it('reaches manual action by keyboard and announces conflict', async () => {
  const user = userEvent.setup();
  vi.stubGlobal('fetch', vi.fn().mockImplementation((url: string, init?: RequestInit) => Promise.resolve(init?.method === 'POST' ? response({ detail: 'Execution active.' }, 409) : mockOtherRequests(url))));
  renderApp('/monitoring-configurations/config-1');
  const button = await screen.findByRole('button', { name: 'Run manual execution' });
  for (let i = 0; i < 40 && document.activeElement !== button; i++) await user.tab();
  expect(button).toHaveFocus();
  await user.keyboard('{Enter}');
  expect((await screen.findByText(/An execution is already active or another/i)).closest('[role="alert"]')).toBeInTheDocument();
});

it('exposes split diff sides and explicit change semantics accessibly', async () => {
  const parsed = parseSplitDiff('@@ -2 +2 @@\n-old\n+new');
  if (!parsed.success) throw new Error('fixture patch should parse');
  const { container } = render(<SplitDiffViewer hunks={parsed.hunks} />);
  expect(await screen.findByRole('region', { name: 'Before (previous version)' })).toBeInTheDocument();
  expect(screen.getByRole('region', { name: 'After (new version)' })).toBeInTheDocument();
  expect(screen.getByRole('group', { name: /Removed line 2/ })).toBeInTheDocument();
  expect(screen.getByRole('group', { name: /Added line 2/ })).toBeInTheDocument();
  const result = await axe.run(container, { runOnly: { type: 'tag', values: ['wcag2a','wcag2aa','wcag21aa','wcag22aa'] }, rules: { 'color-contrast': { enabled: false } } });
  expect(result.violations).toEqual([]);
});
