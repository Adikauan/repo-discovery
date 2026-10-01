import { useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { Alert, Box, Button, Stack, Typography } from '@mui/material';
import { EmptyState } from '../../../shared/components/feedback/EmptyState';
import { ErrorState } from '../../../shared/components/feedback/ErrorState';
import { LoadingState } from '../../../shared/components/feedback/LoadingState';
import { TreePanel } from '../../../shared/components/tree/TreePanel';
import type { GitLabScopeDraft, GitLabScopeNode } from '../types/gitlabScope';
import { ScopeTreeNode } from './ScopeTreeNode';

export function RepositoryTree({ rootNodes, childrenByGroup, expanded, loaded, loadingNodes, nodeErrors, draft,
  rootLoading, rootError, onRetryRoot, onLoadChildren, onToggleExpanded, onToggleSelection }:
  { rootNodes: GitLabScopeNode[]; childrenByGroup: Record<number, GitLabScopeNode[]>; expanded: Set<number>;
    loaded: Set<number>; loadingNodes: Set<number>; nodeErrors: Record<number, string>; draft: GitLabScopeDraft;
    rootLoading: boolean; rootError: string; onRetryRoot: () => void; onLoadChildren: (id: number) => void;
    onToggleExpanded: (id: number) => void; onToggleSelection: (node: GitLabScopeNode) => void }) {
  const allNodes = useMemo(() => {
    const result = new Map<number, GitLabScopeNode>();
    const visit = (nodes: GitLabScopeNode[]) => nodes.forEach(node => {
      if (node.type === 'group') result.set(node.id, node);
      if (childrenByGroup[node.id]) visit(childrenByGroup[node.id]);
    });
    visit(rootNodes);
    return result;
  }, [rootNodes, childrenByGroup]);
  const [searchQuery, setSearchQuery] = useState('');
  const selectedGroups = useMemo(() => new Set(draft.groups.filter(rule => rule.availability !== 'stale').map(rule => rule.gitlab_id)), [draft.groups]);
  const selectedRepositories = useMemo(() => new Set(draft.repositories.filter(rule => rule.availability !== 'stale').map(rule => rule.gitlab_id)), [draft.repositories]);

  function isGroupWithin(groupId: number, ancestorId: number): boolean {
    if (groupId === ancestorId) return true;
    let parent = allNodes.get(groupId)?.parent_group_id ?? null;
    const seen = new Set<number>();
    while (parent && !seen.has(parent)) {
      if (parent === ancestorId) return true;
      seen.add(parent);
      parent = allNodes.get(parent)?.parent_group_id ?? null;
    }
    return false;
  }
  function coveredByAncestor(node: GitLabScopeNode): boolean {
    let parent = node.parent_group_id ?? null;
    const seen = new Set<number>();
    while (parent && !seen.has(parent)) {
      if (selectedGroups.has(parent)) return true;
      seen.add(parent);
      parent = allNodes.get(parent)?.parent_group_id ?? null;
    }
    return false;
  }
  function descendantSelection(node: GitLabScopeNode): boolean {
    if (coveredByAncestor(node)) return false;
    return draft.groups.some(rule => rule.availability !== 'stale' && rule.gitlab_id !== node.id && isGroupWithin(rule.gitlab_id, node.id))
      || draft.repositories.some(rule => rule.availability !== 'stale' && rule.parent_group_id != null
        && isGroupWithin(rule.parent_group_id, node.id));
  }
  function matchesOrHasMatch(node: GitLabScopeNode, query: string): boolean {
    const own = `${node.name} ${node.full_path}`.toLocaleLowerCase().includes(query);
    const descendants = (childrenByGroup[node.id] ?? []).some(child => matchesOrHasMatch(child, query));
    return own || descendants;
  }
  const query = searchQuery.trim().toLocaleLowerCase();
  const renderNodes = (nodes: GitLabScopeNode[], depth: number): ReactNode => nodes
    .filter(node => !query || matchesOrHasMatch(node, query))
    .map(node => {
      const isExpanded = expanded.has(node.id) || (!!query && (childrenByGroup[node.id] ?? []).some(child => matchesOrHasMatch(child, query)));
      const explicit = node.type === 'group' ? selectedGroups.has(node.id) : selectedRepositories.has(node.id);
      const below = descendantSelection(node);
      const descendants = childrenByGroup[node.id] ?? [];
      const loading = loadingNodes.has(node.id);
      const error = nodeErrors[node.id];
      return <ScopeTreeNode key={`${node.type}-${node.id}`} node={node} depth={depth} expanded={isExpanded}
        selected={explicit} indeterminate={node.type === 'group' && !explicit && below}
        inherited={!explicit && coveredByAncestor(node)} loading={loading} error={error}
        empty={loaded.has(node.id) && descendants.length === 0}
        onExpand={() => onToggleExpanded(node.id)}
        onSelect={() => onToggleSelection(node)} onRetry={() => onLoadChildren(node.id)}>
        {isExpanded && descendants.length > 0 && <Stack role="group" spacing={0.25} sx={{ borderLeft: 1, borderColor: 'divider', ml: { xs: 2, sm: 3 }, pl: 1 }}>
          {renderNodes(descendants, depth + 1)}
        </Stack>}
      </ScopeTreeNode>;
    });

  return <TreePanel searchQuery={searchQuery} onSearchChange={setSearchQuery}>
    {rootLoading ? <LoadingState message="Loading top-level GitLab groups…" />
      : rootError ? <ErrorState title="GitLab hierarchy unavailable" message={rootError}
        action={<Button onClick={onRetryRoot}>Retry</Button>} />
        : rootNodes.length === 0 ? <EmptyState title="No groups available" message="No top-level GitLab groups are visible to this credential." />
          : <>
            {query && <Alert severity="info" sx={{ mb: 1 }}>Search filters hierarchy nodes already loaded in this session.</Alert>}
            <Box role="tree" aria-label="GitLab hierarchy"><Stack spacing={0.25}>{renderNodes(rootNodes, 0)}</Stack></Box>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
              Expanding a group loads only that group’s direct children. Search covers loaded entities only.
            </Typography>
          </>}
  </TreePanel>;
}
