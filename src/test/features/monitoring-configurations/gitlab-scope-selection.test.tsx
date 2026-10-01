import { act, fireEvent, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { renderApp } from '../../renderApp';
import { gitlabScopeHierarchy } from './gitlabScopeFixtures';

const emptyScope = { groups: [], repositories: [], stale: false };
const json = (body: unknown, etag = '"0"') => new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json', ETag: etag } });

it('browses a nested group, selects a repository, reviews it, and saves through visible controls', async () => {
  const user = userEvent.setup();
  const calls: Array<{ url: string; init?: RequestInit }> = [];
  let savedScope = emptyScope;
  let savedEtag = '"0"';
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input); calls.push({ url, init });
    if (url.endsWith('/gitlab-scope/root')) return json({ nodes: [gitlabScopeHierarchy[0], gitlabScopeHierarchy[3]] });
    if (url.endsWith('/groups/10/children')) return json({ nodes: [gitlabScopeHierarchy[1]] });
    if (url.endsWith('/groups/11/children')) return json({ nodes: [gitlabScopeHierarchy[2]] });
    if (url.endsWith('/gitlab-scope') && init?.method === 'PUT') {
      const body = JSON.parse(String(init.body));
      savedScope = {
        groups: body.groups.map((rule: { gitlab_id: number }) => ({ selection_id: 'selected-engineering', gitlab_id: rule.gitlab_id, name: 'Engineering', full_path: 'engineering', availability: 'available' })),
        repositories: body.repositories.map((rule: { gitlab_id: number }) => ({ selection_id: 'selected-api', gitlab_id: rule.gitlab_id, name: 'API', full_path: 'engineering/platform/api', parent_group_id: 11, availability: 'available' })), stale: false,
      };
      savedEtag = `"${Number(savedEtag.replaceAll('"', '')) + 1}"`;
      return json(savedScope, savedEtag);
    }
    if (url.endsWith('/gitlab-scope')) return json(savedScope, savedEtag);
    if (url.endsWith('/monitoring-configurations')) return json({ items: [] });
    throw new Error(`Unexpected request: ${url}`);
  });

  const { router } = renderApp('/monitoring-configurations/config-1/scope');
  await screen.findByRole('tree', { name: 'GitLab hierarchy' });
  await user.click(screen.getByRole('checkbox', { name: 'Select Engineering' }));
  await user.click(screen.getByRole('button', { name: 'Expand Engineering' }));
  await user.click(await screen.findByRole('button', { name: 'Expand Platform' }));
  await user.click(await screen.findByRole('checkbox', { name: 'Select API' }));
  expect(await screen.findByText('Repositories (1)')).toBeVisible();
  expect(screen.getByText('Also covered by a selected group')).toBeVisible();
  expect(screen.getByText('API', { selector: 'p' })).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Save scope' }));
  expect(await screen.findByText('GitLab scope saved successfully.')).toBeVisible();
  const save = calls.find(call => call.init?.method === 'PUT');
  expect(save?.init?.headers).toMatchObject({ 'If-Match': '"0"' });
  expect(JSON.parse(String(save?.init?.body))).toEqual({ groups: [{ gitlab_id: 10 }], repositories: [{ gitlab_id: 12 }] });
  expect(screen.getByRole('button', { name: /next step: policy/i })).toBeEnabled();
  expect(calls.every(call => !call.url.includes('/target-branches'))).toBe(true);

  await act(async () => { await router.navigate('/monitoring-configurations'); });
  await screen.findByText('No Monitoring Configurations yet');
  await act(async () => { await router.navigate('/monitoring-configurations/config-1/scope'); });
  await screen.findByRole('tree', { name: 'GitLab hierarchy' });
  expect(screen.getByText('Groups (1)')).toBeVisible();
  expect(screen.getByText('Repositories (1)')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Clear all' }));
  await user.click(screen.getByRole('button', { name: 'Save scope' }));
  expect(await screen.findByText('GitLab scope saved successfully.')).toBeVisible();
  expect(screen.getByText('Groups (0)')).toBeVisible();
  expect(screen.getByText('Repositories (0)')).toBeVisible();
  expect(savedScope).toMatchObject({ groups: [], repositories: [] });
});

it('selects an unloaded group as a dynamic rule without fetching its descendants', async () => {
  const user = userEvent.setup();
  const calls: string[] = [];
  vi.spyOn(globalThis, 'fetch').mockImplementation(async input => {
    const url = String(input); calls.push(url);
    return url.endsWith('/gitlab-scope/root') ? json({ nodes: [gitlabScopeHierarchy[0]] }) : json(emptyScope);
  });
  renderApp('/monitoring-configurations/config-1/scope');
  await user.click(await screen.findByRole('checkbox', { name: 'Select Engineering' }));
  expect(await screen.findByText('Groups (1)')).toBeVisible();
  expect(calls.some(url => url.includes('/children'))).toBe(false);
});

it('keeps selection while filtering and collapsing, and exposes the dirty navigation guard', async () => {
  const user = userEvent.setup();
  const childRequests: string[] = [];
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    const url = String(input);
    if (url.endsWith('/gitlab-scope/root')) return json({ nodes: [gitlabScopeHierarchy[0]] });
    if (url.includes('/groups/') && url.endsWith('/children')) childRequests.push(url);
    if (url.endsWith('/groups/10/children')) return json({ nodes: [gitlabScopeHierarchy[1]] });
    if (url.endsWith('/groups/11/children')) return json({ nodes: [gitlabScopeHierarchy[2]] });
    return json(emptyScope);
  });
  const { router } = renderApp('/monitoring-configurations/config-1/scope');
  await user.click(await screen.findByRole('button', { name: 'Expand Engineering' }));
  await user.click(await screen.findByRole('button', { name: 'Expand Platform' }));
  await user.click(await screen.findByRole('checkbox', { name: 'Select API' }));
  fireEvent.change(screen.getByRole('textbox', { name: 'Search hierarchy' }), { target: { value: 'no-match' } });
  expect(screen.queryByRole('checkbox', { name: 'Select API' })).not.toBeInTheDocument();
  expect(screen.getByText('Repositories (1)')).toBeVisible();
  fireEvent.change(screen.getByRole('textbox', { name: 'Search hierarchy' }), { target: { value: '' } });
  await user.click(screen.getByRole('button', { name: 'Collapse Engineering' }));
  expect(screen.getByText('Repositories (1)')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Expand Engineering' }));
  expect(childRequests).toHaveLength(2);
  await user.click(screen.getByRole('link', { name: 'Home' }));
  expect(await screen.findByRole('dialog', { name: 'Discard unsaved scope changes?' })).toBeVisible();
  await waitFor(() => expect(router.state.location.pathname).toBe('/monitoring-configurations/config-1/scope'));
});
