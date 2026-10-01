import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { parseSplitDiff } from '../../../features/executions/utils/splitDiffParser';
import { SplitDiffViewer } from '../../../features/executions/components/SplitDiffViewer';

describe('SplitDiffViewer', () => {
  it('renders labeled sides, independent numbers, hunk and explicit change semantics', () => {
    const parsed = parseSplitDiff('@@ -1,2 +1,2 @@\n context\n-old\n+new');
    if (!parsed.success) throw new Error('test patch should parse');
    render(<SplitDiffViewer hunks={parsed.hunks} />);
    expect(screen.getByRole('region', { name: 'Before (previous version)' })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'After (new version)' })).toBeInTheDocument();
    const replacement = screen.getAllByTestId('split-diff-row').find(row => row.getAttribute('data-row-type') === 'modified');
    expect(replacement).toBeDefined();
    if (!replacement) return;
    expect(replacement).toHaveAttribute('data-row-type', 'modified');
    expect(replacement).toHaveStyle({ display: 'grid' });
    expect(replacement).toHaveStyle({ gridTemplateColumns: '3.5rem minmax(280px, 1fr) 3.5rem minmax(280px, 1fr)' });
    expect(within(replacement).getByTestId('old-content')).toHaveTextContent('old');
    expect(within(replacement).getByTestId('new-content')).toHaveTextContent('new');
    expect(within(replacement).getByTestId('old-content')).toHaveTextContent('-old');
    expect(within(replacement).getByTestId('new-content')).toHaveTextContent('+new');
    expect(within(replacement).getByTestId('old-line-number')).toHaveTextContent('2');
    expect(within(replacement).getByTestId('new-line-number')).toHaveTextContent('2');
    expect(screen.getByRole('group', { name: /Removed line 2/ })).toBeInTheDocument();
    expect(screen.getByRole('group', { name: /Added line 2/ })).toBeInTheDocument();
    expect(screen.getByText('@@ -1,2 +1,2 @@')).toBeInTheDocument();
  });

  it('keeps removed and added only rows paired with an empty opposite-side placeholder', () => {
    const removed = parseSplitDiff('@@ -10,1 +0,0 @@\n-gone');
    const added = parseSplitDiff('@@ -0,0 +10,1 @@\n+fresh');
    if (!removed.success || !added.success) throw new Error('single-sided patches should parse');
    const { rerender } = render(<SplitDiffViewer hunks={removed.hunks} />);
    const removedRow = screen.getByTestId('split-diff-row');
    expect(within(removedRow).getByTestId('old-content')).toHaveTextContent('gone');
    expect(within(removedRow).getByTestId('new-content')).toHaveAttribute('data-empty-placeholder', 'true');
    expect(within(removedRow).getByTestId('new-line-number')).toBeEmptyDOMElement();
    rerender(<SplitDiffViewer hunks={added.hunks} />);
    const addedRow = screen.getByTestId('split-diff-row');
    expect(within(addedRow).getByTestId('old-content')).toHaveAttribute('data-empty-placeholder', 'true');
    expect(within(addedRow).getByTestId('old-line-number')).toBeEmptyDOMElement();
    expect(within(addedRow).getByTestId('new-content')).toHaveTextContent('fresh');
    expect(within(addedRow).getByTestId('new-line-number')).toHaveTextContent('10');
  });

  it.each([
    ['two removals and one addition', '@@ -1,2 +1 @@\n-old-one\n-old-two\n+new-one', ['modified', 'removed']],
    ['one removal and two additions', '@@ -1 +1,2 @@\n-old-one\n+new-one\n+new-two', ['modified', 'added']],
  ] as const)('renders %s with positional empty-side alignment', (_name, patch, expectedTypes) => {
    const parsed = parseSplitDiff(patch);
    if (!parsed.success) throw new Error('replacement patch should parse');
    render(<SplitDiffViewer hunks={parsed.hunks} />);
    const rows = screen.getAllByTestId('split-diff-row');
    expect(rows.map(row => row.getAttribute('data-row-type'))).toEqual(expectedTypes);
    expect(within(rows[0]).getByTestId('old-content')).toHaveTextContent('old-one');
    expect(within(rows[0]).getByTestId('new-content')).toHaveTextContent('new-one');
    if (expectedTypes[1] === 'removed') {
      expect(within(rows[1]).getByTestId('old-content')).toHaveTextContent('old-two');
      expect(within(rows[1]).getByTestId('new-content')).toHaveAttribute('data-empty-placeholder', 'true');
    } else {
      expect(within(rows[1]).getByTestId('old-content')).toHaveAttribute('data-empty-placeholder', 'true');
      expect(within(rows[1]).getByTestId('new-content')).toHaveTextContent('new-two');
    }
  });

  it('keeps each hunk separated while every source record remains one four-cell row', () => {
    const parsed = parseSplitDiff('@@ -1 +1 @@\n-old\n+new\n@@ -10 +10 @@\n-old-two\n+new-two');
    if (!parsed.success) throw new Error('multi-hunk patch should parse');
    render(<SplitDiffViewer hunks={parsed.hunks} />);
    expect(screen.getAllByRole('separator')).toHaveLength(2);
    const rows = screen.getAllByTestId('split-diff-row');
    expect(rows).toHaveLength(2);
    for (const row of rows) {
      expect(row.children).toHaveLength(4);
      expect(within(row).getByTestId('old-line-number')).toBeInTheDocument();
      expect(within(row).getByTestId('new-line-number')).toBeInTheDocument();
    }
  });

  it('keeps long source rows inside a horizontally scrollable monospace viewer', () => {
    const parsed = parseSplitDiff('@@ -1 +1 @@\n-' + 'x'.repeat(300) + '\n+' + 'y'.repeat(300));
    if (!parsed.success) throw new Error('test patch should parse');
    const { container } = render(<SplitDiffViewer hunks={parsed.hunks} />);
    const scrollRegion = screen.getByRole('region', { name: 'Split diff content' });
    expect(scrollRegion).toHaveStyle({ overflow: 'auto' });
    expect(container.querySelectorAll('[data-testid="old-content"], [data-testid="new-content"]')).toHaveLength(2);
  });
});
