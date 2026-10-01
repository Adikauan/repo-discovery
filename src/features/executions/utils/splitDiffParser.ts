export type SplitDiffRowType = 'context' | 'added' | 'removed' | 'modified' | 'metadata';

export type SplitDiffRow = {
  type: SplitDiffRowType;
  oldLineNumber: number | null;
  oldContent: string | null;
  newLineNumber: number | null;
  newContent: string | null;
  metadataText: string | null;
};

export type SplitDiffHunk = { header: string; rows: SplitDiffRow[] };
export type SplitDiffParseResult =
  | { success: true; hunks: SplitDiffHunk[] }
  | { success: false; error: 'malformed_patch' };

const malformed: SplitDiffParseResult = { success: false, error: 'malformed_patch' };

function alignChanges(rows: SplitDiffRow[]): SplitDiffRow[] {
  const output: SplitDiffRow[] = [];
  let index = 0;
  while (index < rows.length) {
    const current = rows[index];
    if (current.type !== 'removed') {
      output.push(current);
      index += 1;
      continue;
    }

    let endRemoved = index;
    while (endRemoved < rows.length && rows[endRemoved].type === 'removed') endRemoved += 1;
    let endAdded = endRemoved;
    while (endAdded < rows.length && rows[endAdded].type === 'added') endAdded += 1;
    const removed = rows.slice(index, endRemoved);
    const added = rows.slice(endRemoved, endAdded);
    if (added.length === 0) {
      output.push(...removed);
    } else {
      const count = Math.max(removed.length, added.length);
      for (let offset = 0; offset < count; offset += 1) {
        const oldRow = removed[offset];
        const newRow = added[offset];
        output.push({
          type: oldRow && newRow ? 'modified' : oldRow ? 'removed' : 'added',
          oldLineNumber: oldRow?.oldLineNumber ?? null,
          oldContent: oldRow?.oldContent ?? null,
          newLineNumber: newRow?.newLineNumber ?? null,
          newContent: newRow?.newContent ?? null,
          metadataText: null,
        });
      }
    }
    index = endAdded;
  }
  return output;
}

/** Parse the bounded unified patch returned by Feature 011 into a split-view model. */
export function parseSplitDiff(diff: string | null | undefined, diffTruncated = false): SplitDiffParseResult {
  if (!diff) return { success: true, hunks: [] };
  const lines = diff.split('\n').map(line => line.endsWith('\r') ? line.slice(0, -1) : line);
  const hunks: SplitDiffHunk[] = [];
  let current: SplitDiffHunk | null = null;
  let oldExpected = 0;
  let newExpected = 0;
  let oldSeen = 0;
  let newSeen = 0;
  let oldLine = 0;
  let newLine = 0;

  const finishHunk = (atEnd: boolean): boolean => {
    if (!current) return true;
    const short = oldSeen < oldExpected || newSeen < newExpected;
    if (oldSeen > oldExpected || newSeen > newExpected) return false;
    if (short && !(atEnd && diffTruncated)) return false;
    current.rows = alignChanges(current.rows);
    current = null;
    return true;
  };

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    if (index === lines.length - 1 && line === '') continue;
    if (line.startsWith('@@')) {
      if (!finishHunk(false)) return malformed;
      const match = /^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(?:.*)?$/.exec(line);
      if (!match) return malformed;
      oldLine = Number(match[1]);
      oldExpected = match[2] === undefined ? 1 : Number(match[2]);
      newLine = Number(match[3]);
      newExpected = match[4] === undefined ? 1 : Number(match[4]);
      if (![oldLine, oldExpected, newLine, newExpected].every(Number.isSafeInteger)) return malformed;
      oldSeen = 0;
      newSeen = 0;
      current = { header: line, rows: [] };
      hunks.push(current);
      continue;
    }

    if (!current) {
      // File markers and other preamble are not source lines.
      if (line.startsWith('--- ') || line.startsWith('+++ ') || line === '' || line.startsWith('diff --git ') || line.startsWith('index ')) continue;
      if (line.startsWith('\\')) continue;
      return malformed;
    }

    if (line.startsWith('\\')) {
      current.rows.push({ type: 'metadata', oldLineNumber: null, oldContent: null, newLineNumber: null, newContent: null, metadataText: line });
      continue;
    }
    const prefix = line[0];
    const content = line.slice(1);
    if (prefix === ' ') {
      oldSeen += 1;
      newSeen += 1;
      current.rows.push({ type: 'context', oldLineNumber: oldLine++, oldContent: content, newLineNumber: newLine++, newContent: content, metadataText: null });
    } else if (prefix === '-') {
      oldSeen += 1;
      current.rows.push({ type: 'removed', oldLineNumber: oldLine++, oldContent: content, newLineNumber: null, newContent: null, metadataText: null });
    } else if (prefix === '+') {
      newSeen += 1;
      current.rows.push({ type: 'added', oldLineNumber: null, oldContent: null, newLineNumber: newLine++, newContent: content, metadataText: null });
    } else {
      return malformed;
    }
    if (oldSeen > oldExpected || newSeen > newExpected) return malformed;
  }

  if (!finishHunk(true)) return malformed;
  return { success: true, hunks };
}
