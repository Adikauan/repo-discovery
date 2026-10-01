import { Alert, Box, Button, Chip, CircularProgress, Typography } from '@mui/material';
import { TreeNodeRow } from '../../../shared/components/tree/TreeNodeRow';
import type { GitLabScopeNode } from '../types/gitlabScope';

export function ScopeTreeNode({ node, depth, expanded, selected, indeterminate, inherited, loading, error, empty,
  onExpand, onSelect, onRetry, children }: {
  node: GitLabScopeNode; depth: number; expanded: boolean; selected: boolean; indeterminate: boolean;
  inherited: boolean; loading: boolean; error?: string; empty: boolean; onExpand: () => void;
  onSelect: () => void; onRetry: () => void; children?: React.ReactNode;
}) {
  return <Box role="treeitem" aria-level={depth + 1}
    aria-expanded={node.type === 'group' ? expanded : undefined}
    aria-label={`${node.type === 'group' ? 'Group' : 'Repository'} ${node.name}`}>
    <Box sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', columnGap: 1 }}>
      <Box sx={{ flex: '1 1 auto', minWidth: 0 }}><TreeNodeRow label={node.name} depth={depth} kind={node.type}
        expanded={expanded} selected={selected} indeterminate={indeterminate} loading={loading}
        onExpand={onExpand} onSelect={onSelect} /></Box>
      {inherited && <Chip size="small" label="Included by selected group" variant="outlined" color="primary" />}
      {loading && <CircularProgress size={16} aria-label={`Loading ${node.name}`} />}
    </Box>
    {error && <Alert severity="error" sx={{ ml: { xs: 2, sm: 5 }, my: 1 }} action={<Button color="inherit" size="small" onClick={onRetry}>Retry</Button>}>{error}</Alert>}
    {expanded && empty && !loading && !error && <Typography role="status" color="text.secondary" sx={{ pl: { xs: 5, sm: 8 }, py: 1 }}>No visible groups or repositories.</Typography>}
    {expanded && children}
  </Box>;
}
