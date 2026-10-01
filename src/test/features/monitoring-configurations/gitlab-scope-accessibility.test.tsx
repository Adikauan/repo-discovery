import { act, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { renderApp } from '../../renderApp';

const json = (body: unknown) => new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json', ETag: '"0"' } });

it('exposes tree navigation and partial-selection states to keyboard and assistive technology', async () => {
  const user = userEvent.setup();
  vi.spyOn(globalThis, 'fetch').mockImplementation(async input => {
    const url = String(input);
    if (url.endsWith('/gitlab-scope/root')) return json({ nodes: [{ id: 10, type: 'group', name: 'Parent', full_path: 'parent', expandable: true }] });
    if (url.endsWith('/groups/10/children')) return json({ nodes: [{ id: 11, type: 'repository', name: 'Child Repo', full_path: 'parent/child', parent_group_id: 10, expandable: false }] });
    if (url.endsWith('/gitlab-scope')) return json({ groups: [], repositories: [{ selection_id: 'repo', gitlab_id: 11, name: 'Child Repo', full_path: 'parent/child', parent_group_id: 10, availability: 'available' }], stale: false });
    throw new Error(`Unexpected request ${url}`);
  });
  renderApp('/monitoring-configurations/accessibility/scope');
  const tree = await screen.findByRole('tree', { name: 'GitLab hierarchy' });
  expect(within(tree).getByRole('treeitem', { name: 'Group Parent' })).toHaveAttribute('aria-level', '1');
  const expand = within(tree).getByRole('button', { name: 'Expand Parent' });
  act(() => expand.focus());
  await user.keyboard('{Enter}');
  const parentCheckbox = await within(tree).findByRole('checkbox', { name: 'Select Parent' });
  expect(parentCheckbox).toHaveAttribute('data-indeterminate', 'true');
  expect(parentCheckbox).toHaveAttribute('aria-checked', 'mixed');
  expect(within(tree).getByRole('button', { name: 'Collapse Parent' })).toHaveAttribute('aria-expanded', 'true');
  expect(within(tree).getByRole('checkbox', { name: 'Deselect Child Repo' })).toBeChecked();
});
