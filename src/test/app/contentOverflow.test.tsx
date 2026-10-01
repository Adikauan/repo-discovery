import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { AppBreadcrumbs } from '../../shared/components/navigation/AppBreadcrumbs';
import { formatDisplayIdentifier } from '../../shared/utils/displayText';

describe('long content safeguards', () => {
  it.each([undefined, '', '%', '%E0%A4%A', '%ZZ'])('falls back for absent or malformed identifier %s', (identifier) => {
    expect(formatDisplayIdentifier(identifier)).toBe('Unavailable reference');
  });

  it('decodes and sanitizes a display-safe identifier', () => {
    expect(formatDisplayIdentifier('%3Cteam%3E%20alpha')).toBe('team alpha');
  });

  it('falls back for excessive identifiers', () => {
    expect(formatDisplayIdentifier('x'.repeat(121))).toBe('Unavailable reference');
  });

  it('keeps the full breadcrumb label available', () => {
    const label = 'A very long monitoring configuration reference that remains available to assistive technology';
    render(<MemoryRouter><AppBreadcrumbs items={[{ label, path: '/monitoring-configurations' }, { label: 'Details', current: true }]} /></MemoryRouter>);
    expect(screen.getByRole('link', { name: label })).toHaveTextContent(label);
  });
});
