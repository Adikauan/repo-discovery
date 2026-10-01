import { useCallback, useEffect, useMemo, useState } from 'react';
import { ApiError } from '../../../shared/utils/apiClient';
import { gitlabScopeApi } from '../api/gitlabScopeApi';
import type { GitLabScope, GitLabScopeDraft, GitLabScopeNode, GitLabScopeRule } from '../types/gitlabScope';

function errorMessage(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 404) return 'This Monitoring Configuration is unavailable.';
    if (error.status === 409) return error.problem?.detail ?? 'Configure a GitLab connection before browsing new scope.';
    return error.message;
  }
  return 'The scope request could not be completed.';
}

function ruleFromNode(node: GitLabScopeNode): GitLabScopeRule {
  return { selection_id: '', gitlab_id: node.id, name: node.name, full_path: node.full_path,
    parent_group_id: node.parent_group_id, availability: 'available' };
}

function stableDraft(draft: GitLabScopeDraft) {
  return JSON.stringify({ groups: draft.groups.map(item => `${item.selection_id}:${item.gitlab_id}`).sort(),
    repositories: draft.repositories.map(item => `${item.selection_id}:${item.gitlab_id}`).sort() });
}

export function useGitLabScope(configurationId: string) {
  const [scope, setScope] = useState<GitLabScope>();
  const [etag, setEtag] = useState('"0"');
  const [draft, setDraft] = useState<GitLabScopeDraft>({ groups: [], repositories: [] });
  const [rootNodes, setRootNodes] = useState<GitLabScopeNode[]>([]);
  const [children, setChildren] = useState<Record<number, GitLabScopeNode[]>>({});
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const [loaded, setLoaded] = useState<Set<number>>(new Set());
  const [loadingNodes, setLoadingNodes] = useState<Set<number>>(new Set());
  const [nodeErrors, setNodeErrors] = useState<Record<number, string>>({});
  const [rootLoading, setRootLoading] = useState(true);
  const [scopeLoading, setScopeLoading] = useState(true);
  const [rootError, setRootError] = useState('');
  const [scopeError, setScopeError] = useState('');
  const [saveError, setSaveError] = useState('');
  const [notice, setNotice] = useState('');
  const [saving, setSaving] = useState(false);

  const persistedKey = useMemo(() => scope ? stableDraft({ groups: scope.groups, repositories: scope.repositories }) : '', [scope]);
  const dirty = !!scope && stableDraft(draft) !== persistedKey;

  const loadScope = useCallback(async (signal?: AbortSignal) => {
    setScopeLoading(true); setScopeError('');
    try {
      const result = await gitlabScopeApi.get(configurationId, signal);
      setScope(result.data); setDraft({ groups: result.data.groups, repositories: result.data.repositories });
      setEtag(result.etag ?? '"0"');
    } catch (error) { if (!signal?.aborted) setScopeError(errorMessage(error)); }
    finally { if (!signal?.aborted) setScopeLoading(false); }
  }, [configurationId]);

  const loadRoot = useCallback(async (signal?: AbortSignal) => {
    setRootLoading(true); setRootError('');
    try {
      const result = await gitlabScopeApi.root(configurationId, signal);
      setRootNodes(result.data.nodes);
    } catch (error) { if (!signal?.aborted) setRootError(errorMessage(error)); }
    finally { if (!signal?.aborted) setRootLoading(false); }
  }, [configurationId]);

  const reload = useCallback(async () => {
    const controller = new AbortController();
    await Promise.all([loadScope(controller.signal), loadRoot(controller.signal)]);
  }, [loadRoot, loadScope]);

  useEffect(() => {
    const controller = new AbortController();
    void Promise.all([loadScope(controller.signal), loadRoot(controller.signal)]);
    return () => controller.abort();
  }, [loadRoot, loadScope]);

  const loadChildren = useCallback(async (groupId: number) => {
    if (loaded.has(groupId) || loadingNodes.has(groupId)) return;
    setLoadingNodes(previous => new Set(previous).add(groupId));
    setNodeErrors(previous => ({ ...previous, [groupId]: '' }));
    try {
      const result = await gitlabScopeApi.children(configurationId, groupId);
      setChildren(previous => ({ ...previous, [groupId]: result.data.nodes }));
      setLoaded(previous => new Set(previous).add(groupId));
    } catch (error) { setNodeErrors(previous => ({ ...previous, [groupId]: errorMessage(error) })); }
    finally { setLoadingNodes(previous => { const next = new Set(previous); next.delete(groupId); return next; }); }
  }, [configurationId, loaded, loadingNodes]);

  const toggleExpanded = useCallback((groupId: number) => {
    const isExpanded = expanded.has(groupId);
    setExpanded(previous => {
      const next = new Set(previous);
      if (isExpanded) next.delete(groupId); else next.add(groupId);
      return next;
    });
    if (!isExpanded) void loadChildren(groupId);
  }, [expanded, loadChildren]);

  const toggleSelection = useCallback((node: GitLabScopeNode) => {
    setDraft(previous => {
      const key = node.type === 'group' ? 'groups' : 'repositories';
      const existing = previous[key];
      const currentIndex = existing.findIndex(item => item.availability !== 'stale' && item.gitlab_id === node.id);
      const next = currentIndex >= 0 ? existing.filter((_, index) => index !== currentIndex) : [...existing, ruleFromNode(node)];
      return { ...previous, [key]: next };
    });
    setSaveError(''); setNotice('');
  }, []);

  const removeRule = useCallback((kind: 'groups' | 'repositories', item: GitLabScopeRule) => {
    setDraft(previous => ({ ...previous, [kind]: previous[kind].filter(rule =>
      item.selection_id ? rule.selection_id !== item.selection_id : rule !== item) }));
    setSaveError(''); setNotice('');
  }, []);

  const clear = useCallback(() => { setDraft({ groups: [], repositories: [] }); setSaveError(''); setNotice(''); }, []);

  const save = useCallback(async () => {
    setSaving(true); setSaveError(''); setNotice('');
    try {
      const result = await gitlabScopeApi.replace(configurationId, {
        groups: draft.groups.map(({ selection_id, gitlab_id }) => ({ ...(selection_id ? { selection_id } : {}), gitlab_id })),
        repositories: draft.repositories.map(({ selection_id, gitlab_id }) => ({ ...(selection_id ? { selection_id } : {}), gitlab_id })),
      }, etag);
      setScope(result.data); setDraft({ groups: result.data.groups, repositories: result.data.repositories });
      setEtag(result.etag ?? etag); setNotice('GitLab scope saved successfully.');
      return true;
    } catch (error) {
      setSaveError(error instanceof ApiError && error.status === 412
        ? 'The saved scope changed elsewhere. Reload it and review your selections before saving.' : errorMessage(error));
      return false;
    } finally { setSaving(false); }
  }, [configurationId, draft, etag]);

  return { scope, draft, dirty, rootNodes, children, expanded, loaded, loadingNodes, nodeErrors,
    rootLoading, scopeLoading, rootError, scopeError, saveError, notice, saving,
    reload, loadRoot, loadChildren, toggleExpanded, toggleSelection, removeRule, clear, save, dismissNotice: () => setNotice('') };
}
