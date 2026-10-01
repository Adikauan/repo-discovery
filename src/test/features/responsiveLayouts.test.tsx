import { screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { renderApp } from '../renderApp';
import { execution, response } from './executions/fixtures';

afterEach(() => vi.unstubAllGlobals());
function jsonResponse(body: unknown) { return new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } }); }

describe('responsive structural layouts', () => {
  it.each([375, 768, 1440])('keeps listing structure accessible at %ipx', async width => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ items: [] })));
    renderApp('/monitoring-configurations', width);
    expect(await screen.findByText(/no monitoring configurations yet/i)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Monitoring Configurations' })).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: 'Search configurations' })).toBeInTheDocument();
  });
  it.each([375, 768, 1440])('keeps execution dashboard structure accessible at %ipx', async width => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(execution)));
    renderApp('/executions/execution-1', width);
    expect(await screen.findByRole('heading', { name: 'Execution execution-1' })).toBeInTheDocument();
    expect(screen.getByRole('tablist', { name: 'Execution sections' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Overview' })).toBeInTheDocument();
    expect(screen.getByText('Successful repositories')).toBeInTheDocument();
    expect(screen.getByText(/repository processing completed successfully/i)).toBeInTheDocument();
  });
  it('wraps long execution identifiers and historical scope paths on narrow screens', async () => {
    const longId = `execution-${'id'.repeat(45)}`;
    const longPath = `group/${'historical-scope-'.repeat(12)}`;
    const longExecution = { ...execution, id: longId, snapshot: { ...execution.snapshot, scope: {
      groups: [{ gitlabGroupId: 7, name: longPath, fullPath: longPath }], repositories: [],
    } } };
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(longExecution)));
    renderApp(`/executions/${longId}`, 375);
    const heading = await screen.findByRole('heading', { name: `Execution ${longId}` });
    expect(heading).toHaveStyle({ overflowWrap: 'anywhere' });
    expect(screen.getByText(longPath)).toBeInTheDocument();
  });
});
