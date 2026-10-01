import { useEffect, useMemo, useState } from 'react';
import { Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, IconButton, List, ListItem, ListItemButton, ListItemText, Stack, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Tooltip, Typography } from '@mui/material';
import DifferenceIcon from '@mui/icons-material/Difference';
import { EmptyState } from '../../../shared/components/feedback/EmptyState';
import { LoadingState } from '../../../shared/components/feedback/LoadingState';
import { findingsApi } from '../api/findingsApi';
import type { Finding } from '../types/finding';
import type { FindingDiffFile, FindingDiffResponse } from '../types/findingDiff';
import { ApiError } from '../../../shared/utils/apiClient';
import { parseSplitDiff } from '../utils/splitDiffParser';
import { SplitDiffViewer } from './SplitDiffViewer';

export function ExecutionFindingsSection({ executionId, refreshRevision = 0 }: { executionId: string; refreshRevision?: number }) {
  const [items, setItems] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [retry, setRetry] = useState(0);
  const [activeFinding, setActiveFinding] = useState<Finding | null>(null);
  const [diff, setDiff] = useState<FindingDiffResponse | null>(null);
  const [diffLoading, setDiffLoading] = useState(false);
  const [diffError, setDiffError] = useState<string | null>(null);
  const [diffRetry, setDiffRetry] = useState(0);
  const [selectedFile, setSelectedFile] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError(false);
    findingsApi.listForExecution(executionId, 1, controller.signal).then(result => {
      if (Array.isArray(result.data?.items)) setItems(result.data.items);
      else setError(true);
    })
      .catch(() => { if (!controller.signal.aborted) setError(true); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [executionId, retry, refreshRevision]);
  useEffect(() => {
    if (!activeFinding) return;
    const controller = new AbortController();
    setDiff(null); setDiffError(null); setDiffLoading(true); setSelectedFile(0);
    findingsApi.getCommitDiff(activeFinding.id, controller.signal).then(result => setDiff(result.data))
      .catch(error => { if (!controller.signal.aborted) setDiffError(error instanceof ApiError ? error.problem?.code ?? 'unknown' : 'unknown'); })
      .finally(() => { if (!controller.signal.aborted) setDiffLoading(false); });
    return () => controller.abort();
  }, [activeFinding?.id, diffRetry]);
  const closeDiff = () => { setActiveFinding(null); setDiff(null); setDiffError(null); };
  const diffErrorMessage = diffError === 'commit_not_found'
    ? 'GitLab could not find this commit. The Finding remains available, but its changes cannot be loaded.'
    : 'Unable to load commit changes. Try again.';
  const selected: FindingDiffFile | undefined = diff?.files[selectedFile];
  const parsedDiff = useMemo(() => selected?.textDiffAvailable && !selected.binary && !selected.tooLarge && !selected.collapsed
    ? parseSplitDiff(selected.diff, selected.diffTruncated)
    : null, [selected?.diff, selected?.diffTruncated, selected?.textDiffAvailable, selected?.binary, selected?.tooLarge, selected?.collapsed]);
  return <Stack spacing={2}>
    <Typography component="h2" variant="h2">Findings</Typography>
    {loading ? <LoadingState message="Loading findings…" /> : error ? <Alert severity="error" role="alert" action={<Button color="inherit" onClick={() => setRetry(value => value + 1)}>Retry</Button>}>Unable to load findings for this execution.</Alert> : items.length === 0 ? <EmptyState title="No findings detected" message="No findings were detected for this execution." /> : <TableContainer sx={{ overflowX: 'auto' }}><Table aria-label="Execution findings">
      <TableHead><TableRow><TableCell>Severity</TableCell><TableCell>Rule</TableCell><TableCell>Repository</TableCell><TableCell>Branch</TableCell><TableCell>Author</TableCell><TableCell>Commit</TableCell><TableCell>Summary</TableCell><TableCell>Detected</TableCell><TableCell>Changes</TableCell></TableRow></TableHead>
      <TableBody>{items.map(item => <TableRow key={item.id}><TableCell><Typography component="span">Warning</Typography></TableCell><TableCell>{item.title}</TableCell><TableCell>{item.repositoryFullPath}</TableCell><TableCell>{item.branch ?? <Typography variant="body2" color="text.secondary">Branch unavailable (historical context not recorded)</Typography>}</TableCell><TableCell>{item.authorEmail ?? (item.authorEmailState === 'missing' ? 'Email missing' : 'Email malformed')}</TableCell><TableCell><Typography component="code" sx={{ overflowWrap: 'anywhere' }}>{item.commitHash}</Typography></TableCell><TableCell>{item.summary}</TableCell><TableCell>{new Date(item.authoredAt ?? item.createdAt).toLocaleString()}</TableCell><TableCell>{item.ruleId === 'unauthorized-commit-author' && item.commitHash ? <Tooltip title="View diff"><IconButton aria-label="View commit diff" onClick={() => setActiveFinding(item)} size="small"><DifferenceIcon /></IconButton></Tooltip> : null}</TableCell></TableRow>)}</TableBody>
    </Table></TableContainer>}
    <Dialog
      open={Boolean(activeFinding)}
      onClose={closeDiff}
      fullWidth
      maxWidth={false}
      aria-labelledby="finding-diff-title"
      scroll="paper"
      slotProps={{ paper: {
        style: {
          width: 'min(95vw, calc(100vw - 32px))', maxWidth: '1800px',
          height: 'min(90vh, calc(100vh - 32px))', maxHeight: 'calc(100vh - 32px)',
        },
        sx: { m: { xs: 1, sm: 2 }, display: 'flex', flexDirection: 'column' },
      } }}
    >
      <DialogTitle id="finding-diff-title">Commit changes</DialogTitle>
      <DialogContent dividers sx={{ flex: '1 1 auto', minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {activeFinding && <Stack spacing={2} sx={{ height: '100%', minHeight: 0, minWidth: 0, overflow: 'hidden' }}>
          <Typography>{activeFinding.repositoryFullPath} · <code style={{ overflowWrap: 'anywhere' }}>{activeFinding.commitHash}</code></Typography>
          <Typography>{activeFinding.authorName ?? 'Author unavailable'} · {activeFinding.authorEmail ?? 'Author email unavailable'} · {activeFinding.authoredAt ? new Date(activeFinding.authoredAt).toLocaleString() : 'Timestamp unavailable'}</Typography>
          {activeFinding.commitMessageSummary && <Typography>{activeFinding.commitMessageSummary}</Typography>}
          {diffLoading && <LoadingState message="Loading commit changes…" />}
          {diffError && <Alert severity="error" role="alert" action={diffError === 'commit_not_found' ? undefined : <Button color="inherit" onClick={() => setDiffRetry(value => value + 1)}>Retry</Button>}>{diffErrorMessage}</Alert>}
          {diff && <>
            {diff.filesCompleteness === 'truncated' && <Alert severity="warning">Additional changed files were omitted.</Alert>}
            {diff.filesCompleteness === 'unknown' && <Alert severity="info">GitLab did not provide enough information to confirm whether all changed files were returned.</Alert>}
            <Stack data-testid="changed-files-and-diff" direction="row" spacing={2} sx={{ flex: '1 1 auto', minHeight: 0, minWidth: 0, overflow: 'hidden' }}>
              <List aria-label="Changed files" dense sx={{ width: 'clamp(210px, 22vw, 280px)', minWidth: '210px', maxWidth: '280px', flex: '0 0 clamp(210px, 22vw, 280px)', maxHeight: '100%', overflowY: 'auto', overflowX: 'hidden', border: 1, borderColor: 'divider' }}>
                {diff.files.map((file, index) => <ListItem key={`${file.oldPath}:${file.newPath}:${index}`} component="li" disablePadding>
                  <ListItemButton selected={selectedFile === index} onClick={() => setSelectedFile(index)} aria-expanded={selectedFile === index}>
                    <ListItemText primary={file.newPath ?? file.oldPath ?? 'Path unavailable'} secondary={`${file.changeType ?? 'Change type unavailable'}${file.binary ? ' · Binary' : ''}${file.diffTruncated || file.collapsed || file.tooLarge ? ' · Diff incomplete' : ''}`} sx={{ overflowWrap: 'anywhere' }} />
                  </ListItemButton>
                </ListItem>)}
              </List>
              <Stack sx={{ minWidth: 0, minHeight: 0, flex: '1 1 auto', overflow: 'hidden' }} spacing={1}>
                {selected && <>
                  <Typography component="h3" variant="h6" sx={{ overflowWrap: 'anywhere' }}>{selected.oldPath && selected.newPath && selected.oldPath !== selected.newPath ? `${selected.oldPath} → ${selected.newPath}` : selected.newPath ?? selected.oldPath ?? 'File path unavailable'}</Typography>
                  {selected.binary && <Alert severity="info">Text diff is unavailable for this binary file.</Alert>}
                  {selected.collapsed && <Alert severity="info">GitLab collapsed this file diff.</Alert>}
                  {selected.tooLarge && <Alert severity="info">GitLab marked this file diff as too large to return.</Alert>}
                  {selected.diffTruncated && <Alert severity="warning">The available text diff was truncated to fit the response limit.</Alert>}
                  {!selected.textDiffAvailable && !selected.binary && !selected.collapsed && !selected.tooLarge && <Typography>No textual diff was returned for this file.</Typography>}
                  {parsedDiff?.success === false && <Alert severity="error" role="alert">The diff could not be displayed because its patch format is invalid.</Alert>}
                  {parsedDiff?.success === true && <SplitDiffViewer hunks={parsedDiff.hunks} />}
                </>}
                {diff.files.length === 0 && <Typography>No changed files were returned.</Typography>}
              </Stack>
            </Stack>
          </>}
        </Stack>}
      </DialogContent>
      <DialogActions><Button onClick={closeDiff}>Close</Button></DialogActions>
    </Dialog>
  </Stack>;
}
