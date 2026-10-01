import { screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { renderApp } from '../renderApp';
import { mockOtherRequests } from '../features/executions/fixtures';

afterEach(() => vi.unstubAllGlobals());

describe('nested canonical routes', () => {
  it.each([
    ['/monitoring-configurations/new', 'New Monitoring Configuration', 'Monitoring Configurations'],
    ['/monitoring-configurations/demo', 'Monitoring Configuration', 'Monitoring Configurations'],
    ['/monitoring-configurations/demo/executions', 'Configuration Executions', 'Monitoring Configurations'],
    ['/executions/demo', 'Execution execution-1', 'Executions'],
  ])('orients %s', async (path, title, section) => {
    vi.stubGlobal('fetch', vi.fn().mockImplementation((url: string) => Promise.resolve(mockOtherRequests(url))));
    renderApp(path);
    expect(await screen.findByRole('heading', { level: 1, name: title })).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: section }).some(link => link.getAttribute('aria-current') === 'page')).toBe(true);
  });
});
