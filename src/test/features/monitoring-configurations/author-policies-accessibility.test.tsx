import axe from 'axe-core';
import { screen } from '@testing-library/react';
import { vi, expect, it } from 'vitest';
import { renderApp } from '../../renderApp';

const scope = { groups: [{ selection_id: 'group', gitlab_id: 12, name: 'Backend', full_path: 'team/backend', availability: 'available' }],
  repositories: [{ selection_id: 'repo', gitlab_id: 42, name: 'API', full_path: 'team/backend/api', parent_group_id: 12, availability: 'available' }], stale: false };
const repositoryPolicy = { id: 'policy-repo', scope_type: 'repository_branch', active: true, gitlab_instance_fingerprint: 'a'.repeat(64),
  gitlab_group_id: null, gitlab_project_id: 42, scope_name: 'API', scope_path: 'team/backend/api', branch: 'main',
  allowed_author_emails: ['alice@example.com'] };

it('keeps the scope-aware Policy editor accessible with labelled fields, actions, and policy context', async () => {
  vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL) => {
    const url = String(input);
    const body = url.endsWith('/gitlab-scope') ? scope : { mode: 'scope_aware', configuration_revision: 1,
      policies: [repositoryPolicy], repositories: [{ gitlab_project_id: 42, name: 'API', full_path: 'team/backend/api', source: 'group', status: 'configured' }],
      legacy_fallback: { active: false, allowed_author_emails: [] } };
    return Promise.resolve(new Response(JSON.stringify(body), { headers: { 'Content-Type': 'application/json' } }));
  }));
  renderApp('/monitoring-configurations/accessibility/authors');
  expect(await screen.findByRole('textbox', { name: 'Allowed commit author email' })).toBeInTheDocument();
  const results = await axe.run(document.body, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa'] },
    rules: { 'color-contrast': { enabled: false } } });
  expect(results.violations.filter(item => item.impact === 'critical')).toEqual([]);
});
