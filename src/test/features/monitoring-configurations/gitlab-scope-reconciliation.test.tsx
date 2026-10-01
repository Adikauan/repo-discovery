import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { renderApp } from '../../renderApp';

const json = (body: unknown) => new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json', ETag: '"2"' } });

it('retains stale and unavailable rules in the summary until the user explicitly removes them', async () => {
  const user = userEvent.setup();
  vi.spyOn(globalThis, 'fetch').mockImplementation(async input => {
    const url = String(input);
    if (url.endsWith('/gitlab-scope/root')) return json({ nodes: [] });
    if (url.endsWith('/gitlab-scope')) return json({
      groups: [
        { selection_id: 'stale-group', gitlab_id: 7, name: 'Old Group', full_path: 'old/group', availability: 'stale' },
        { selection_id: 'inaccessible-group', gitlab_id: 8, name: 'Private Group', full_path: 'private/group', availability: 'unavailable' },
      ],
      repositories: [{ selection_id: 'unresolved-repo', gitlab_id: 9, name: 'Legacy Repo', full_path: 'legacy/repo', availability: 'unresolved' }], stale: true,
    });
    return json({ groups: [], repositories: [], stale: false });
  });
  renderApp('/monitoring-configurations/reconcile/scope');
  expect(await screen.findByText('Group: Old Group')).toBeVisible();
  expect(screen.getByText((_, node) => node?.tagName === 'P' && !!node.textContent?.includes('different GitLab instance'))).toBeVisible();
  expect(screen.getByText((_, node) => node?.tagName === 'P' && !!node.textContent?.includes('unavailable to this credential'))).toBeVisible();
  expect(screen.getByText((_, node) => node?.tagName === 'P' && !!node.textContent?.includes('could not be checked'))).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Remove group Old Group' }));
  expect(screen.queryByText('Group: Old Group')).not.toBeInTheDocument();
  expect(screen.getByText('Groups (0)')).toBeVisible();
  expect(screen.getByText('Repositories (0)')).toBeVisible();
  expect(screen.getByText('Unavailable (2)')).toBeVisible();
  expect(localStorage.length).toBe(0);
  expect(sessionStorage.length).toBe(0);
});
