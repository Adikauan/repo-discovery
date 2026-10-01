import { fireEvent, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { renderApp } from '../../renderApp';

const created = {
  id: 'generated-123', name: 'Platform Mining', description: 'First setup',
  gitlab_url: 'https://gitlab.example.com', enabled: false,
  allowed_author_emails: [],
  created_at: '2026-09-28T12:00:00Z', updated_at: '2026-09-28T12:00:00Z', version: '1',
};
function response(body: unknown, status = 200) { return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json', ETag: '"1"' } }); }
afterEach(() => vi.unstubAllGlobals());

describe('Monitoring Configuration creation and listing', () => {
  it('keeps new General values in the draft and does not create before GitLab Connection', async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    renderApp('/monitoring-configurations/new');

    fireEvent.change(screen.getByRole('textbox', { name: 'Name' }), { target: { value: created.name } });
    fireEvent.change(screen.getByRole('textbox', { name: 'Description' }), { target: { value: created.description } });
    expect(screen.queryByRole('textbox', { name: 'GitLab instance URL' })).not.toBeInTheDocument();
    fireEvent.change(screen.getByRole('textbox', { name: 'Name' }), { target: { value: created.name } });
    fireEvent.change(screen.getByRole('textbox', { name: 'Description' }), { target: { value: created.description } });
    await user.click(screen.getByRole('button', { name: /next step: gitlab connection/i }));
    expect(await screen.findByRole('heading', { name: 'GitLab Connection' })).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('shows empty, loading and API error states for the listing', async () => {
    const user = userEvent.setup();
    let resolveList!: (value: Response) => void;
    const pending = new Promise<Response>(resolve => { resolveList = resolve; });
    vi.stubGlobal('fetch', vi.fn().mockReturnValueOnce(pending));
    const view = renderApp('/monitoring-configurations');
    expect(screen.getByRole('status')).toBeInTheDocument();
    resolveList(response({ items: [] }));
    expect(await screen.findByText(/no monitoring configurations yet/i)).toBeInTheDocument();
    view.unmount();
    vi.unstubAllGlobals();
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('network')));
    const { unmount } = renderApp('/monitoring-configurations');
    expect(await screen.findByText(/api is unavailable/i)).toBeInTheDocument();
    unmount();
    void user;
  });

  it('validates required General values before advancing', async () => {
    const user = userEvent.setup();
    vi.stubGlobal('fetch', vi.fn());
    renderApp('/monitoring-configurations/new');
    await user.click(screen.getByRole('button', { name: /next step: gitlab connection/i }));
    expect(await screen.findByText(/enter a configuration name/i)).toBeInTheDocument();
    expect(screen.queryByRole('textbox', { name: 'GitLab instance URL' })).not.toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalled();
  });

  it('trims search and keeps wildcard-like characters literal in requests', async () => {
    const fetchMock = vi.fn().mockResolvedValue(response({ items: [created] }));
    vi.stubGlobal('fetch', fetchMock);
    renderApp('/monitoring-configurations');
    await screen.findByText(created.name);
    const field = screen.getByRole('textbox', { name: /search configurations/i });
    const cases = [
      ['platform', 'platform'], ['PLATFORM', 'PLATFORM'], ['  platform  ', 'platform'],
      ['', null], ['   ', null], ['%', '%'], ['_', '_'], ['*', '*'], ['[x]\\', '[x]\\'],
    ] as const;
    for (const [query, expected] of cases) {
      const previousCalls = fetchMock.mock.calls.length;
      fireEvent.change(field, { target: { value: query } });
      await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(previousCalls + 1));
      const requestedUrl = new URL(fetchMock.mock.calls.at(-1)?.[0] as string);
      expect(requestedUrl.searchParams.get('search')).toBe(expected);
    }
  });

  it('does not expose the GitLab URL field on General', async () => {
    renderApp('/monitoring-configurations/new');
    expect(screen.getByRole('textbox', { name: 'Name' })).toBeInTheDocument();
    expect(screen.queryByRole('textbox', { name: 'GitLab instance URL' })).not.toBeInTheDocument();
  });

  it('aborts a superseded search without displaying an API error', async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn()
      .mockImplementationOnce((_url: string, init: RequestInit) => new Promise((_resolve, reject) => {
        init.signal?.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')));
      }))
      .mockResolvedValue(response({ items: [] }));
    vi.stubGlobal('fetch', fetchMock);
    renderApp('/monitoring-configurations');
    fireEvent.change(screen.getByRole('textbox', { name: /search configurations/i }), { target: { value: 'new query' } });
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect((fetchMock.mock.calls[0][1] as RequestInit).signal?.aborted).toBe(true);
    expect(await screen.findByText(/no matching configurations/i)).toBeInTheDocument();
    expect(screen.queryByText(/api is unavailable/i)).not.toBeInTheDocument();
    void user;
  });
});
