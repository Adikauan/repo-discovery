import { useMemo } from 'react';
import { Box, Button, Chip, List, ListItem, ListItemText, Stack, Typography } from '@mui/material';
import { SectionHeader } from '../../../shared/components/layout/SectionHeader';
import type { GitLabScopeDraft, GitLabScopeNode, GitLabScopeRule } from '../types/gitlabScope';
import { UnavailableScopeItem } from './UnavailableScopeItem';

function RuleList({ title, items, kind, onRemove, coveredRepositories = new Set<number>() }:
  { title: string; items: GitLabScopeRule[]; kind: 'groups' | 'repositories';
    onRemove: (kind: 'groups' | 'repositories', item: GitLabScopeRule) => void; coveredRepositories?: Set<number> }) {
  return <Box sx={{ mb: 2 }}>
    <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>{title} ({items.length})</Typography>
    {items.length === 0 ? <Typography variant="body2" color="text.secondary" sx={{ py: 1 }}>None selected.</Typography>
      : <List dense disablePadding>{items.map(item => <ListItem key={item.selection_id || `${kind}-${item.gitlab_id}`}
        divider secondaryAction={<Button size="small" aria-label={`Remove ${kind === 'groups' ? 'group' : 'repository'} ${item.name}`}
          onClick={() => onRemove(kind, item)}>Remove</Button>}>
        <ListItemText primary={item.name} secondary={item.full_path} />
        {kind === 'repositories' && coveredRepositories.has(item.gitlab_id) && <Chip size="small" label="Also covered by a selected group" variant="outlined" />}
      </ListItem>)}</List>}
  </Box>;
}

export function ScopeSelectionSummary({ draft, treeNodes, onRemove, onClear }:
  { draft: GitLabScopeDraft; treeNodes: GitLabScopeNode[];
    onRemove: (kind: 'groups' | 'repositories', item: GitLabScopeRule) => void; onClear: () => void }) {
  const selectedGroups = useMemo(() => draft.groups.filter(item => item.availability === 'available'), [draft.groups]);
  const selectedRepositories = useMemo(() => draft.repositories.filter(item => item.availability === 'available'), [draft.repositories]);
  const unavailable = useMemo(() => [
    ...draft.groups.filter(item => item.availability !== 'available').map(item => ({ kind: 'groups' as const, item })),
    ...draft.repositories.filter(item => item.availability !== 'available').map(item => ({ kind: 'repositories' as const, item })),
  ], [draft]);
  const groupIds = new Set(selectedGroups.map(item => item.gitlab_id));
  const byId = new Map(treeNodes.filter(node => node.type === 'group').map(node => [node.id, node]));
  const coveredRepositories = new Set(draft.repositories.filter(repository => {
    let parent = repository.parent_group_id ?? null;
    const seen = new Set<number>();
    while (parent && !seen.has(parent)) {
      if (groupIds.has(parent)) return true;
      seen.add(parent);
      parent = byId.get(parent)?.parent_group_id ?? null;
    }
    return false;
  }).map(item => item.gitlab_id));

  return <Box component="aside" aria-label="Selected scope" data-testid="selected-scope-summary"
    sx={{ border: 1, borderColor: 'divider', borderRadius: 2, p: 2, minHeight: 390 }}>
    <Stack direction="row" spacing={1} sx={{ justifyContent: 'space-between', alignItems: 'center' }}>
      <SectionHeader title={`Selected scope (${draft.groups.length + draft.repositories.length})`} />
      <Button size="small" color="error" disabled={!draft.groups.length && !draft.repositories.length} onClick={onClear}>Clear all</Button>
    </Stack>
    <RuleList title="Groups" items={selectedGroups} kind="groups" onRemove={onRemove} />
    <RuleList title="Repositories" items={selectedRepositories} kind="repositories" onRemove={onRemove} coveredRepositories={coveredRepositories} />
    <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>Unavailable ({unavailable.length})</Typography>
    {unavailable.length === 0 ? <Typography variant="body2" color="text.secondary" sx={{ py: 1 }}>No unavailable selections.</Typography>
      : <List dense disablePadding>{unavailable.map(({ kind, item }) => <UnavailableScopeItem key={item.selection_id}
        kind={kind} item={item} onRemove={() => onRemove(kind, item)} />)}</List>}
  </Box>;
}
