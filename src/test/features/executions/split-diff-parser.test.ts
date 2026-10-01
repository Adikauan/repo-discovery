import { describe, expect, it } from 'vitest';
import { parseSplitDiff } from '../../../features/executions/utils/splitDiffParser';

describe('parseSplitDiff', () => {
  it('numbers context, removed, and added lines independently and pairs replacements', () => {
    const result = parseSplitDiff('@@ -4,2 +8,2 @@\n same\n-old\n+new');
    expect(result.success).toBe(true);
    if (!result.success) return;
    expect(result.hunks[0].rows).toEqual([
      { type: 'context', oldLineNumber: 4, oldContent: 'same', newLineNumber: 8, newContent: 'same', metadataText: null },
      { type: 'modified', oldLineNumber: 5, oldContent: 'old', newLineNumber: 9, newContent: 'new', metadataText: null },
    ]);
  });

  it('aligns unequal replacement blocks by position', () => {
    const result = parseSplitDiff('@@ -1,3 +1,2 @@\n-a\n-b\n+c\n d');
    expect(result.success).toBe(true);
    if (!result.success) return;
    expect(result.hunks[0].rows.slice(0, 2).map(row => [row.type, row.oldContent, row.newContent])).toEqual([
      ['modified', 'a', 'c'], ['removed', 'b', null],
    ]);
    const extraAdded = parseSplitDiff('@@ -1 +1,2 @@\n-old\n+new\n+extra');
    expect(extraAdded.success && extraAdded.hunks[0].rows.map(row => [row.type, row.oldContent, row.newContent, row.newLineNumber])).toEqual([
      ['modified', 'old', 'new', 1], ['added', null, 'extra', 2],
    ]);
    const paired = parseSplitDiff('@@ -1,2 +1,2 @@\n-old-a\n-old-b\n+new-a\n+new-b');
    expect(paired.success && paired.hunks[0].rows.map(row => row.type)).toEqual(['modified', 'modified']);
  });

  it('parses multiple hunks, omitted counts, metadata, and no-newline marker', () => {
    const result = parseSplitDiff('--- a/file\n+++ b/file\n@@ -2 +5 @@\n-old\n+new\n\\ No newline at end of file\n@@ -20,2 +30,2 @@\n x\n-y\n+z');
    expect(result.success).toBe(true);
    if (!result.success) return;
    expect(result.hunks).toHaveLength(2);
    expect(result.hunks[0].rows[0].oldLineNumber).toBe(2);
    expect(result.hunks[0].rows[0].newLineNumber).toBe(5);
    expect(result.hunks[0].rows[1]).toMatchObject({ type: 'metadata', metadataText: '\\ No newline at end of file', oldLineNumber: null, newLineNumber: null });
    expect(result.hunks[1].rows[0]).toMatchObject({ type: 'context', oldLineNumber: 20, newLineNumber: 30 });
  });

  it('preserves whitespace and handles added/deleted files and empty input', () => {
    const added = parseSplitDiff('@@ -0,0 +1,2 @@\n+  indented\n+');
    expect(added.success && added.hunks[0].rows.map(row => [row.oldLineNumber, row.newLineNumber, row.newContent])).toEqual([[null, 1, '  indented'], [null, 2, '']]);
    const deleted = parseSplitDiff('@@ -1,1 +0,0 @@\n-gone');
    expect(deleted.success && deleted.hunks[0].rows[0]).toMatchObject({ oldLineNumber: 1, newLineNumber: null, oldContent: 'gone' });
    expect(parseSplitDiff('').success).toBe(true);
  });

  it('treats file marker prefixes as source content inside a hunk', () => {
    const result = parseSplitDiff('@@ -1 +0,0 @@\n--- a/path');
    expect(result.success && result.hunks[0].rows[0]).toMatchObject({ type: 'removed', oldContent: '-- a/path', oldLineNumber: 1 });
  });

  it('accepts a short final hunk only when the provider marks the diff truncated', () => {
    const patch = '@@ -3,4 +7,4 @@\n one\n-two';
    expect(parseSplitDiff(patch).success).toBe(false);
    const result = parseSplitDiff(patch, true);
    expect(result.success && result.hunks[0].rows.map(row => row.oldLineNumber)).toEqual([3, 4]);
  });

  it('returns a safe error for malformed headers and count overflow', () => {
    expect(parseSplitDiff('@@ malformed @@\n x').success).toBe(false);
    expect(parseSplitDiff('@@ -1 +1 @@\n x\n y').success).toBe(false);
  });
});
