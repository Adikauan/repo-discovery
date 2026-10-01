import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { AuthorPoliciesPage } from '../../../features/monitoring-configurations/pages/AuthorPoliciesPage';
import type { AuthorPolicy, AuthorPoliciesResponse } from '../../../features/monitoring-configurations/types/authorPolicies';

const repository = { gitlab_project_id: 42, name: 'API', full_path: 'sequor/backend/api', source: 'group' as const, status: 'policy_required' as const };
const policy = (id: string, branch: string, authors: string[] = []): AuthorPolicy => ({ id, scope_type: 'repository_branch', active: true,
  gitlab_instance_fingerprint: 'a'.repeat(64), gitlab_group_id: null, gitlab_project_id: 42, scope_name: 'API',
  scope_path: repository.full_path, branch, allowed_author_emails: authors });
const state = (policies: AuthorPolicy[] = [], mode: 'legacy' | 'scope_aware' = 'scope_aware'): AuthorPoliciesResponse => ({
  mode, legacy_fallback: { active: mode === 'legacy', allowed_author_emails: ['legacy@example.com'] }, policies,
  repositories: [{ ...repository, status: policies.length ? 'configured' : 'policy_required' }], configuration_revision: 1 });

function setup(response = state()) {
  const requests: { url: string; init?: RequestInit }[] = [];
  const router = createMemoryRouter([
    { path: '/monitoring-configurations/:id/authors', element: <AuthorPoliciesPage /> },
    { path: '/monitoring-configurations/:id/scope', element: <div>Scope screen</div> },
    { path: '/monitoring-configurations/:id/schedule', element: <div>Scheduling screen</div> },
  ], { initialEntries: ['/monitoring-configurations/config-1/authors'] });
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input); requests.push({ url, init });
    if (url.endsWith('/repositories/42/branches')) return new Response(JSON.stringify({ items: [
      { name: 'main', commit_sha: 'a'.repeat(40), default: true }, { name: 'dev-larah', commit_sha: 'b'.repeat(40), default: false }] }), { headers: { 'Content-Type': 'application/json' } });
    if (init?.method === 'PUT') return new Response(JSON.stringify({ id: 'saved-policy', scope_type: 'repository_branch',
      allowed_author_emails: JSON.parse(String(init.body)).allowed_author_emails, configuration_revision: 2 }), { headers: { 'Content-Type': 'application/json' } });
    if (init?.method === 'DELETE') return new Response(null, { status: 204 });
    return new Response(JSON.stringify(response), { headers: { 'Content-Type': 'application/json', ETag: '"1"' } });
  }));
  render(<RouterProvider router={router} />);
  return { requests, router };
}

describe('scope-aware Policy step', () => {
  it('shows a Group-derived repository without a second repository picker and explains branch mining ownership', async () => {
    setup();
    expect((await screen.findAllByText(repository.full_path)).length).toBeGreaterThan(0);
    expect(screen.getByText('Repository · included through selected Group scope')).toBeInTheDocument();
    expect(screen.getByText('Policy required')).toBeInTheDocument();
    expect(screen.getByText(/Policies define which branches are mined and which authors are allowed/)).toBeInTheDocument();
    expect(screen.queryByRole('textbox', { name: /repository id|repository path/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/branches do not apply to groups/i)).not.toBeInTheDocument();
  });

  it('loads GitLab branches on demand and submits the selected branch as the mining Policy', async () => {
    const { requests } = setup();
    await screen.findByText(repository.full_path);
    expect(requests.some(item => item.url.endsWith('/repositories/42/branches'))).toBe(false);
    fireEvent.click(screen.getByRole('button', { name: 'Load GitLab branches' }));
    const selector = await screen.findByRole('combobox', { name: 'Add branch policy' });
    fireEvent.mouseDown(selector);
    fireEvent.click(await screen.findByRole('option', { name: 'dev-larah' }));
    fireEvent.click(screen.getByRole('button', { name: 'Add policy' }));
    fireEvent.change(screen.getByRole('textbox', { name: 'Allowed commit author email' }), { target: { value: 'allowed@example.com' } });
    fireEvent.click(screen.getByRole('button', { name: 'Add author' }));
    fireEvent.click(screen.getByRole('button', { name: 'Save author policies' }));
    await waitFor(() => expect(requests.some(item => item.init?.method === 'PUT')).toBe(true));
    const mutation = requests.find(item => item.init?.method === 'PUT')!;
    expect(mutation.url).toContain('/author-policies/repositories/42/branches');
    expect(JSON.parse(String(mutation.init?.body))).toEqual({ branch: 'dev-larah', allowed_author_emails: ['allowed@example.com'] });
    expect(mutation.url).not.toContain('/groups/');
  });

  it('renders multiple independent branch policies for one repository', async () => {
    const { requests } = setup(state([policy('main-id', 'main', ['a@example.com']), policy('dev-id', 'dev-larah', ['b@example.com'])]));
    expect((await screen.findAllByText(repository.full_path)).length).toBeGreaterThan(0);
    expect(screen.getByText('Mining and author authorization branch: main')).toBeInTheDocument();
    expect(screen.getByText('Mining and author authorization branch: dev-larah')).toBeInTheDocument();
    expect(screen.getByText('a@example.com')).toBeInTheDocument();
    expect(screen.getByText('b@example.com')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Load GitLab branches' }));
    const selector = await screen.findByRole('combobox', { name: 'Add branch policy' });
    fireEvent.mouseDown(selector);
    fireEvent.click(await screen.findByRole('option', { name: 'main (default)' }));
    expect(screen.getByRole('button', { name: 'Add policy' })).toBeDisabled();
    expect(requests.some(item => item.init?.method === 'PUT')).toBe(false);
  });

  it('preserves legacy global authors read-only and never submits them through Policy mutations', async () => {
    const { requests } = setup(state([], 'legacy'));
    expect(await screen.findByText('Legacy global author list (read only)')).toBeInTheDocument();
    expect(screen.getByText(/does not authorize new executions/i)).toBeInTheDocument();
    expect(screen.getByText('legacy@example.com')).toBeInTheDocument();
    expect(screen.queryByRole('textbox', { name: 'Allowed commit authors' })).not.toBeInTheDocument();
    expect(requests.some(item => item.init?.method === 'PUT')).toBe(false);
  });

  it('keeps fixed-bar navigation between Scope, Policy and Scheduling', async () => {
    const { router } = setup();
    await screen.findByText(repository.full_path);
    expect(screen.getByRole('heading', { name: 'Policy' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /previous step: scope/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /next step: scheduling/i }));
    await screen.findByText('Scheduling screen');
    expect(router.state.location.pathname).toContain('/schedule');
  });
});
