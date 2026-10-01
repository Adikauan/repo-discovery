import { screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { renderApp } from '../renderApp';
import { execution, response } from './executions/fixtures';

afterEach(() => vi.unstubAllGlobals());

describe('structural shells', () => {
  it('shows a historical execution without fabricated mining results', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(execution)));
    renderApp('/executions/execution-1');
    expect(await screen.findByRole('heading', { name: 'Execution execution-1' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Overview' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByText(/repository processing completed successfully/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Download report' })).not.toBeInTheDocument();
  });

  it('provides only general information fields in the initial creation flow', () => {
    renderApp('/monitoring-configurations/new');
    expect(screen.getByRole('textbox', { name: 'Name' })).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: 'Description' })).toBeInTheDocument();
    expect(screen.queryByRole('textbox', { name: 'GitLab instance URL' })).not.toBeInTheDocument();
    expect(screen.queryByText('Recurrence')).not.toBeInTheDocument();
    expect(screen.queryByText(/hierarchy preview/i)).not.toBeInTheDocument();
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
  });
});
