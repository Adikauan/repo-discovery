import axe from 'axe-core';
import { describe, expect, it } from 'vitest';
import { renderApp } from '../renderApp';

const canonicalDestinations = [
  '/',
  '/monitoring-configurations',
  '/monitoring-configurations/new',
  '/monitoring-configurations/demo',
  '/monitoring-configurations/demo/executions',
  '/executions',
  '/executions/demo',
  '/settings',
];

describe('application shell accessibility', () => {
  it.each(canonicalDestinations)('has no automatically detectable critical violations at %s', async (path) => {
    renderApp(path);
    const results = await axe.run(document.body, {
      runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'] },
      // jsdom does not calculate layout or painted colors. Theme contrast is covered by
      // themeContrast.test.ts; browser/manual review remains the acceptance backstop.
      rules: { 'color-contrast': { enabled: false } },
    });
    const critical = results.violations.filter((violation) => violation.impact === 'critical');
    expect(critical).toEqual([]);
  });
});
