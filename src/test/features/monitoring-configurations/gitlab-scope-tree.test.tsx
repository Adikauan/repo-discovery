import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { renderApp } from '../../renderApp';
import { makeScopeNode } from './gitlabScopeFixtures';

const scope = { groups: [], repositories: [], stale: false };
const json = (body: unknown) => new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json', ETag: '"0"' } });

it('keeps a 1,000-entity hierarchy lazy: root is interactive first and expansion fetches one branch only', async () => {
  const user = userEvent.setup();
  const calls: string[] = [];
  // Ten roots, ten direct children per root, and ten repositories below each subgroup: 1,010 entities.
  const roots = Array.from({ length: 10 }, (_, index) => makeScopeNode({ id: 100 + index, name: `Group ${index + 1}`, full_path: `group-${index + 1}` }));
  const directChildren = new Map<number, ReturnType<typeof makeScopeNode>[]>();
  const nestedChildren = new Map<number, ReturnType<typeof makeScopeNode>[]>();
  for (const root of roots) {
    const subgroups = Array.from({ length: 9 }, (_, index) => makeScopeNode({ id: root.id * 10 + index,
      name: `Subgroup ${index + 1}`, full_path: `${root.full_path}/subgroup-${index + 1}`, parent_group_id: root.id }));
    const directRepository = makeScopeNode({ id: root.id * 100, type: 'repository', name: 'Direct repository',
      full_path: `${root.full_path}/direct`, parent_group_id: root.id });
    directChildren.set(root.id, [...subgroups, directRepository]);
    for (const subgroup of subgroups) nestedChildren.set(subgroup.id,
      Array.from({ length: 10 }, (_, index) => makeScopeNode({ id: subgroup.id * 100 + index, type: 'repository',
        name: `Project ${index + 1}`, full_path: `${subgroup.full_path}/project-${index + 1}`, parent_group_id: subgroup.id })));
  }
  const representedEntityCount = roots.length + [...directChildren.values()].flat().length + [...nestedChildren.values()].flat().length;
  expect(representedEntityCount).toBe(1010);
  vi.spyOn(globalThis, 'fetch').mockImplementation(async input => {
    const url = String(input); calls.push(url);
    if (url.endsWith('/gitlab-scope/root')) return json({ nodes: roots });
    const requestedGroup = Number(url.match(/\/groups\/(\d+)\/children/)?.[1]);
    if (directChildren.has(requestedGroup)) return json({ nodes: directChildren.get(requestedGroup) });
    if (nestedChildren.has(requestedGroup)) return json({ nodes: nestedChildren.get(requestedGroup) });
    return json(scope);
  });

  renderApp('/monitoring-configurations/large/scope');
  await screen.findByRole('tree', { name: 'GitLab hierarchy' });
  expect(screen.getByRole('button', { name: 'Expand Group 2' })).toBeEnabled();
  expect(calls.filter(url => url.endsWith('/gitlab-scope/root'))).toHaveLength(1);
  expect(calls.some(url => url.includes('/children'))).toBe(false);
  await user.click(screen.getByRole('button', { name: 'Expand Group 1' }));
  await screen.findByRole('button', { name: 'Expand Subgroup 1' });
  await waitFor(() => expect(calls.filter(url => url.includes('/children'))).toEqual([
    'http://localhost:8000/api/v1/monitoring-configurations/large/gitlab-scope/groups/100/children',
  ]));
  expect(calls.some(url => url.includes('/groups/101/children'))).toBe(false);
  expect(calls.some(url => url.includes('/groups/1000/children'))).toBe(false);
});

it('retains selected scope when a loaded branch is filtered out and then restored', async () => {
  const user = userEvent.setup();
  vi.spyOn(globalThis, 'fetch').mockImplementation(async input => {
    const url = String(input);
    if (url.endsWith('/gitlab-scope/root')) return json({ nodes: [makeScopeNode({ id: 10, name: 'Team' })] });
    if (url.endsWith('/groups/10/children')) return json({ nodes: [makeScopeNode({ id: 11, type: 'repository', name: 'Repo', parent_group_id: 10 })] });
    return json(scope);
  });
  renderApp('/monitoring-configurations/filter/scope');
  await user.click(await screen.findByRole('button', { name: 'Expand Team' }));
  await user.click(await screen.findByRole('checkbox', { name: 'Select Repo' }));
  await user.type(screen.getByRole('textbox', { name: 'Search hierarchy' }), 'missing');
  expect(screen.queryByRole('checkbox', { name: 'Select Repo' })).not.toBeInTheDocument();
  expect(screen.getByText('Repositories (1)')).toBeVisible();
  await user.clear(screen.getByRole('textbox', { name: 'Search hierarchy' }));
  expect(await screen.findByRole('checkbox', { name: 'Deselect Repo' })).toBeChecked();
});

it('retries a failed branch, reports its empty state, and preserves the selected group', async () => {
  const user = userEvent.setup();
  let childAttempts = 0;
  vi.spyOn(globalThis, 'fetch').mockImplementation(async input => {
    const url = String(input);
    if (url.endsWith('/gitlab-scope/root')) return json({ nodes: [makeScopeNode({ id: 10, name: 'Empty Team' })] });
    if (url.endsWith('/groups/10/children')) {
      childAttempts += 1;
      return childAttempts === 1
        ? new Response(JSON.stringify({ detail: 'GitLab provider is unavailable.' }), { status: 503, headers: { 'Content-Type': 'application/json' } })
        : json({ nodes: [] });
    }
    return json(scope);
  });
  renderApp('/monitoring-configurations/retry/scope');
  await user.click(await screen.findByRole('checkbox', { name: 'Select Empty Team' }));
  await user.click(screen.getByRole('button', { name: 'Expand Empty Team' }));
  expect(await screen.findByText('GitLab provider is unavailable.')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Retry' }));
  expect(await screen.findByText('No visible groups or repositories.')).toBeVisible();
  expect(screen.getByText('Groups (1)')).toBeVisible();
  expect(childAttempts).toBe(2);
});
