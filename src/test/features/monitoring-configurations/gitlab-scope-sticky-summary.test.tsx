import { screen, within } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { renderApp } from '../../renderApp';

const scope = { groups: [{ selection_id: 'group-rule-1', gitlab_id: 4, name: 'Backend', full_path: 'org/backend',
  parent_group_id: null, availability: 'available' }], repositories: [{ selection_id: 'repo-rule-1', gitlab_id: 22,
  name: 'API', full_path: 'org/backend/api', parent_group_id: 4, availability: 'available' }], stale: false };
const json = (body: unknown) => new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json', ETag: '"2"' } });
afterEach(() => vi.unstubAllGlobals());

it.each([['desktop', 1440], ['narrow', 390]])('keeps the tree, selected summary, and bottom navigation available at %s width', async (_label, width) => {
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith('/gitlab-scope/root')) return json({ nodes: [{ id: 4, type: 'group', name: 'Backend', full_path: 'org/backend', parent_group_id: null }] });
    if (url.endsWith('/gitlab-scope')) return json(scope);
    return json({});
  }));
  renderApp('/monitoring-configurations/cfg-sticky/scope', width);

  const tree = await screen.findByRole('tree', { name: 'GitLab hierarchy' });
  const selected = screen.getByRole('complementary', { name: 'Selected scope' });
  expect(tree).toBeInTheDocument();
  expect(within(selected).getByText('org/backend')).toBeInTheDocument();
  expect(within(selected).getByText('org/backend/api')).toBeInTheDocument();
  expect(screen.getByRole('navigation', { name: 'Configuration wizard navigation' })).toBeInTheDocument();
  expect(selected.parentElement).toHaveAttribute('data-sticky-desktop', 'true');
  expect(selected.parentElement).toHaveAttribute('data-sticky-top-offset', '16');
  const styleRules = [...document.querySelectorAll('style')].map(style => style.textContent ?? '').join('\n');
  expect(styleRules).toMatch(/position:sticky/);
  expect(styleRules).toMatch(/100vh\s*-\s*128px/);
});
