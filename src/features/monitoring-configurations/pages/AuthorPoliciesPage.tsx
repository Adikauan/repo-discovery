import { useEffect, useRef, useState } from 'react';
import { Alert, Box, Button, Card, CardContent, Chip, CircularProgress, Dialog, DialogActions,
  DialogContent, DialogTitle, FormControl, Grid, InputLabel, MenuItem, Select, Stack, TextField, Typography } from '@mui/material';
import { useBlocker, useNavigate, useParams } from 'react-router-dom';
import { PageContainer } from '../../../shared/components/layout/PageContainer';
import { PageHeader } from '../../../shared/components/layout/PageHeader';
import { LoadingState } from '../../../shared/components/feedback/LoadingState';
import { authorPoliciesApi } from '../api/authorPoliciesApi';
import type { AuthorPoliciesResponse, AuthorPolicy, GitLabBranch } from '../types/authorPolicies';
import { ConfigurationWizardProgress } from '../components/ConfigurationWizardProgress';
import { ApiError } from '../../../shared/utils/apiClient';
import { MonitoringConfigurationWizardLayout } from '../components/MonitoringConfigurationWizardLayout';

type LocalPolicy = AuthorPolicy & { draft?: boolean };
const safeError = (error: unknown) => error instanceof ApiError ? error.message : 'The request could not be completed. Try again.';
const validEmail = (email: string) => /^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/.test(email);
const policyKey = (type: string, id: number, branch?: string | null) => `${type}:${id}:${branch ?? ''}`;

export function AuthorPoliciesPage() {
  const { id = '' } = useParams();
  const navigate = useNavigate();
  const [state, setState] = useState<AuthorPoliciesResponse | null>(null);
  const [policies, setPolicies] = useState<LocalPolicy[]>([]);
  const [emails, setEmails] = useState<Record<string, string[]>>({});
  const [emailInputs, setEmailInputs] = useState<Record<string, string>>({});
  const [branches, setBranches] = useState<Record<number, GitLabBranch[]>>({});
  const [branchLoading, setBranchLoading] = useState<Record<number, boolean>>({});
  const [branchErrors, setBranchErrors] = useState<Record<number, string>>({});
  const [branchSelections, setBranchSelections] = useState<Record<number, string>>({});
  const [removed, setRemoved] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saveError, setSaveError] = useState('');
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const allowNext = useRef(false);
  const blocker = useBlocker(({ nextLocation }) => dirty && !(allowNext.current && nextLocation.pathname === `/monitoring-configurations/${id}/schedule`));

  useEffect(() => {
    const beforeUnload = (event: BeforeUnloadEvent) => {
      if (!dirty) return;
      event.preventDefault(); event.returnValue = '';
    };
    window.addEventListener('beforeunload', beforeUnload);
    return () => window.removeEventListener('beforeunload', beforeUnload);
  }, [dirty]);

  async function reload() {
    setLoading(true); setError('');
    try {
      const policyResult = await authorPoliciesApi.list(id);
      setState(policyResult.data); setPolicies(policyResult.data.policies);
      setEmails(Object.fromEntries(policyResult.data.policies.map(policy => [policy.id, policy.allowed_author_emails])));
      setRemoved([]); setDirty(false);
    } catch (reason) { setError(safeError(reason)); }
    finally { setLoading(false); }
  }
  useEffect(() => { void reload(); }, [id]);

  const policyFor = (type: AuthorPolicy['scope_type'], scopeId: number, branch: string | null) =>
    policies.find(item => item.scope_type === type && (type === 'group' ? item.gitlab_group_id === scopeId :
      item.gitlab_project_id === scopeId && item.branch === branch) && !removed.includes(item.id));

  function createDraft(type: AuthorPolicy['scope_type'], scopeId: number, name: string, path: string, branch: string | null) {
    const key = policyKey(type, scopeId, branch);
    if (policyFor(type, scopeId, branch)) return;
    const draft: LocalPolicy = { id: `draft:${key}`, draft: true, scope_type: type, active: true,
      gitlab_instance_fingerprint: '', gitlab_group_id: type === 'group' ? scopeId : null,
      gitlab_project_id: type === 'repository_branch' ? scopeId : null,
      scope_name: name, scope_path: path, branch, allowed_author_emails: [] };
    setPolicies(current => [...current, draft]); setEmails(current => ({ ...current, [draft.id]: [] })); setDirty(true);
  }

  async function loadBranches(projectId: number) {
    setBranchLoading(current => ({ ...current, [projectId]: true }));
    setBranchErrors(current => ({ ...current, [projectId]: '' }));
    try { const result = await authorPoliciesApi.branches(id, projectId); setBranches(current => ({ ...current, [projectId]: result.data.items })); }
    catch (reason) { setBranchErrors(current => ({ ...current, [projectId]: safeError(reason) })); }
    finally { setBranchLoading(current => ({ ...current, [projectId]: false })); }
  }

  function addEmail(policyId: string) {
    const value = (emailInputs[policyId] ?? '').trim();
    if (!validEmail(value)) { setSaveError('Enter a valid author email before adding it.'); return; }
    const normalized = value.toLocaleLowerCase();
    if ((emails[policyId] ?? []).some(email => email.toLocaleLowerCase() === normalized)) {
      setSaveError('That author is already in this policy.'); return;
    }
    setSaveError(''); setEmails(current => ({ ...current, [policyId]: [...(current[policyId] ?? []), value] }));
    setEmailInputs(current => ({ ...current, [policyId]: '' })); setDirty(true);
  }

  async function saveAll(): Promise<boolean> {
    if (!state) return false;
    setSaving(true); setSaveError('');
    let revision = state.configuration_revision;
    let nextPolicies = [...policies];
    let nextRemoved = [...removed];
    try {
      for (const policy of policies.filter(item => item.draft && !removed.includes(item.id))) {
        const authors = emails[policy.id] ?? [];
        const result = await authorPoliciesApi.saveRepositoryBranch(id, policy.gitlab_project_id!, policy.branch!, authors, revision);
        revision = result.data.configuration_revision;
        const persisted: LocalPolicy = { ...policy, id: result.data.id, draft: false,
          allowed_author_emails: result.data.allowed_author_emails };
        nextPolicies = nextPolicies.map(item => item.id === policy.id ? persisted : item);
        setEmails(current => { const copy = { ...current }; delete copy[policy.id]; copy[persisted.id] = persisted.allowed_author_emails; return copy; });
        setState(current => current ? { ...current, configuration_revision: revision } : current);
      }
      for (const policy of policies.filter(item => !item.draft && removed.includes(item.id))) {
        await authorPoliciesApi.remove(id, policy.id, revision); revision += 1;
        nextPolicies = nextPolicies.filter(item => item.id !== policy.id);
        nextRemoved = nextRemoved.filter(value => value !== policy.id);
        setState(current => current ? { ...current, configuration_revision: revision } : current);
      }
      for (const policy of nextPolicies.filter(item => !item.draft && !removed.includes(item.id))) {
        const currentEmails = emails[policy.id] ?? policy.allowed_author_emails;
        if (currentEmails.join('\n') === policy.allowed_author_emails.join('\n')) continue;
        const result = await authorPoliciesApi.saveRepositoryBranch(id, policy.gitlab_project_id!, policy.branch!, currentEmails, revision);
        revision = result.data.configuration_revision;
        nextPolicies = nextPolicies.map(item => item.id === policy.id ? { ...item, allowed_author_emails: result.data.allowed_author_emails } : item);
        setEmails(current => ({ ...current, [policy.id]: result.data.allowed_author_emails }));
        setState(current => current ? { ...current, configuration_revision: revision } : current);
      }
      setPolicies(nextPolicies); setState(current => current ? { ...current, configuration_revision: revision } : current);
      setRemoved([]); setDirty(false);
      return true;
    } catch (reason) {
      setPolicies(nextPolicies); setRemoved(nextRemoved);
      setState(current => current ? { ...current, configuration_revision: revision } : current);
      setSaveError(safeError(reason));
      return false;
    }
    finally { setSaving(false); }
  }

  async function migrate() {
    if (!state) return;
    setSaving(true); setSaveError('');
    try { const result = await authorPoliciesApi.migrate(id, state.configuration_revision); setState(result.data); setPolicies(result.data.policies); setEmails(Object.fromEntries(result.data.policies.map(policy => [policy.id, policy.allowed_author_emails]))); }
    catch (reason) { setSaveError(safeError(reason)); }
    finally { setSaving(false); }
  }

  const policyCard = (policy: LocalPolicy, label: string) => {
    const emailsForPolicy = emails[policy.id] ?? policy.allowed_author_emails ?? [];
    return <Card variant="outlined" key={policy.id} sx={{ mb: 1.5 }}>
      <CardContent>
        <Stack direction={{ xs: 'column', sm: 'row' }} sx={{ justifyContent: 'space-between', gap: 1 }}>
          <Box><Typography variant="subtitle1" sx={{ fontWeight: 700 }}>{label}</Typography>
            <Typography variant="body2" color="text.secondary">Mining and author authorization branch: {policy.branch}</Typography></Box>
          <Button color="error" disabled={state?.mode !== 'scope_aware' || saving}
            aria-label={`Remove ${label} branch policy ${policy.branch}`}
            onClick={() => { setRemoved(current => [...current, policy.id]); setDirty(true); }}>Remove policy</Button>
        </Stack>
        <Stack direction="row" sx={{ gap: 1, alignItems: 'center', mt: 1.5 }}>
          <TextField size="small" type="email" label="Allowed commit author email" value={emailInputs[policy.id] ?? ''}
            disabled={state?.mode !== 'scope_aware' || saving} onChange={event => setEmailInputs(current => ({ ...current, [policy.id]: event.target.value }))}
            onKeyDown={event => { if (event.key === 'Enter') { event.preventDefault(); addEmail(policy.id); } }} />
          <Button disabled={state?.mode !== 'scope_aware' || saving} onClick={() => addEmail(policy.id)}>Add author</Button>
        </Stack>
        <Stack direction="row" sx={{ gap: 1, flexWrap: 'wrap', mt: 1.5 }} aria-label={`${label} allowed authors`}>
          {emailsForPolicy.map(email => <Chip key={email.toLocaleLowerCase()} label={email} onDelete={state?.mode === 'scope_aware'
            ? () => { setEmails(current => ({ ...current, [policy.id]: (current[policy.id] ?? []).filter(value => value !== email) })); setDirty(true); }
            : undefined} aria-label={`${email}, allowed author`} deleteIcon={undefined} />)}
          {emailsForPolicy.length === 0 && <Typography variant="body2" color="text.secondary">No allowed authors. All valid commit author emails are unauthorized for this explicit policy.</Typography>}
        </Stack>
      </CardContent>
    </Card>;
  };

  async function next() {
    if (dirty && !(await saveAll())) return;
    allowNext.current = true;
    navigate(`/monitoring-configurations/${id}/schedule`);
  }
  const previous = () => navigate(`/monitoring-configurations/${id}/scope`);
  if (loading) return <MonitoringConfigurationWizardLayout step={3} previous={previous} previousLabel="Scope" next={() => void next()} nextLabel="Scheduling" busy><PageContainer><LoadingState message="Loading Policy configuration…" /></PageContainer></MonitoringConfigurationWizardLayout>;
  if (error || !state) return <MonitoringConfigurationWizardLayout step={3} previous={previous} previousLabel="Scope" next={() => void next()} nextLabel="Scheduling"><PageContainer><PageHeader title="Policy" />
    <Alert severity="error" action={<Button color="inherit" onClick={() => void reload()}>Retry</Button>}>{error || 'Author policies are unavailable.'}</Alert></PageContainer></MonitoringConfigurationWizardLayout>;

  const inactive = policies.filter(policy => !policy.active && !removed.includes(policy.id));
  return <MonitoringConfigurationWizardLayout step={3} previous={previous} previousLabel="Scope" next={() => void next()} nextLabel="Scheduling" busy={saving}><PageContainer>
    <PageHeader title="Policy" description="Configure the branches mined and the author identities allowed on each branch."
      breadcrumbs={[{ label: 'Monitoring Configurations', path: '/monitoring-configurations' }, { label: 'Configuration', path: `/monitoring-configurations/${id}` }, { label: 'Policy', current: true }]} />
    <ConfigurationWizardProgress configurationId={id} currentStep={3} />
    <Alert severity="info" sx={{ mb: 2 }}>Policies define which branches are mined and which authors are allowed to commit to each branch. Every repository in the effective Scope needs at least one Policy before execution.</Alert>
    {state.mode === 'legacy' && <Alert severity="warning" sx={{ mb: 2 }}>
      <Typography sx={{ fontWeight: 700 }}>Legacy global author list (read only)</Typography>
      <Typography variant="body2">This legacy list is retained for historical compatibility and does not authorize new executions. The original values will not be erased.</Typography>
      <Stack direction="row" sx={{ gap: 1, flexWrap: 'wrap', my: 1 }}>
        {state.legacy_fallback.allowed_author_emails.length ? state.legacy_fallback.allowed_author_emails.map(email => <Chip key={email} label={email} />) : <Typography variant="body2">No legacy author entries.</Typography>}
      </Stack>
      <Button variant="contained" disabled={saving} onClick={() => void migrate()}>{saving ? 'Switching…' : 'Switch to scope-aware policies'}</Button>
    </Alert>}
    {saveError && <Alert severity="error" sx={{ mb: 2 }}>{saveError}</Alert>}
    <Grid container spacing={2}>
      {(state.repositories ?? []).map(item => {
        const rows = policies.filter(policy => policy.scope_type === 'repository_branch' && policy.gitlab_project_id === item.gitlab_project_id && !removed.includes(policy.id));
        return <Grid size={{ xs: 12 }} key={`repo-${item.gitlab_project_id}`}>
          <Card variant="outlined"><CardContent>
            <Stack direction={{ xs: 'column', sm: 'row' }} sx={{ alignItems: { sm: 'center' }, justifyContent: 'space-between', gap: 1 }}>
              <Box><Typography variant="h2" sx={{ fontSize: '1.1rem' }}>{item.full_path}</Typography><Typography variant="body2" color="text.secondary">Repository · {item.source === 'group' ? 'included through selected Group scope' : 'selected directly'}</Typography>
                <Chip size="small" color={item.status === 'configured' ? 'success' : 'warning'} label={item.status === 'configured' ? 'Configured' : 'Policy required'} /></Box>
              {!branches[item.gitlab_project_id] && <Button disabled={!!branchLoading[item.gitlab_project_id]} onClick={() => void loadBranches(item.gitlab_project_id)}>
                {branchLoading[item.gitlab_project_id] ? <CircularProgress size={18} aria-label="Loading branches" /> : 'Load GitLab branches'}</Button>}
              {branches[item.gitlab_project_id] && <FormControl size="small" sx={{ minWidth: 220 }}>
                <InputLabel id={`branch-label-${item.gitlab_project_id}`}>Add branch policy</InputLabel>
                <Select labelId={`branch-label-${item.gitlab_project_id}`} label="Add branch policy" value={branchSelections[item.gitlab_project_id] ?? ''}
                  onChange={event => setBranchSelections(current => ({ ...current, [item.gitlab_project_id]: event.target.value }))}>
                  {branches[item.gitlab_project_id].map(branch => <MenuItem key={branch.name} value={branch.name}>{branch.name}{branch.default ? ' (default)' : ''}</MenuItem>)}
                </Select>
              </FormControl>}
              {branches[item.gitlab_project_id] && <Button disabled={state.mode !== 'scope_aware' || !branchSelections[item.gitlab_project_id] || !!policyFor('repository_branch', item.gitlab_project_id, branchSelections[item.gitlab_project_id])}
                onClick={() => { const branch = branchSelections[item.gitlab_project_id]; const draft = createDraft('repository_branch', item.gitlab_project_id, item.name, item.full_path, branch); void draft; }}>
                Add policy</Button>}
            </Stack>
            {branchErrors[item.gitlab_project_id] && <Alert severity="error" sx={{ mt: 1 }} action={<Button color="inherit" onClick={() => void loadBranches(item.gitlab_project_id)}>Retry</Button>}>{branchErrors[item.gitlab_project_id]}</Alert>}
            {branches[item.gitlab_project_id]?.length === 0 && <Typography role="status" sx={{ mt: 1 }}>GitLab returned no branches for this repository.</Typography>}
            {rows.map(policy => <Box key={policy.id} sx={{ mt: 1.5 }}>{policy.branch && branches[item.gitlab_project_id] && !branches[item.gitlab_project_id].some(branch => branch.name === policy.branch) &&
              <Alert severity="warning" sx={{ mb: 1 }}>Branch “{policy.branch}” is unavailable in GitLab. This policy is retained; no other branch is substituted.</Alert>}
              {policyCard(policy, item.full_path)}</Box>)}
          </CardContent></Card>
        </Grid>;
      })}
    </Grid>
    {inactive.length > 0 && <Card variant="outlined" sx={{ mt: 2 }}><CardContent><Typography variant="h2" sx={{ fontSize: '1.1rem' }}>Policies outside the current scope</Typography>
      <Typography variant="body2" color="text.secondary">These policies are inactive and retained. They will not be reassigned.</Typography>
      {inactive.map(policy => <Stack key={policy.id} direction="row" sx={{ justifyContent: 'space-between', mt: 1 }}>
        <Typography>{policy.scope_path}{policy.branch ? ` · ${policy.branch}` : ''}</Typography>
        <Button color="error" aria-label={`Delete inactive policy ${policy.scope_path}`} onClick={() => { setRemoved(current => [...current, policy.id]); setDirty(true); }}>Delete</Button>
      </Stack>)}
    </CardContent></Card>}
    <Stack direction={{ xs: 'column', sm: 'row' }} sx={{ justifyContent: 'space-between', gap: 1, mt: 2 }}>
      <Stack direction="row" sx={{ gap: 1, justifyContent: 'flex-end' }}>
        <Button variant="contained" disabled={!dirty || saving || state.mode !== 'scope_aware'} onClick={() => void saveAll()}>{saving ? 'Saving…' : 'Save author policies'}</Button>
      </Stack>
    </Stack>
    <Dialog open={blocker.state === 'blocked'} onClose={() => blocker.reset?.()}>
      <DialogTitle>Discard unsaved author policy changes?</DialogTitle>
      <DialogContent>Your author policy changes have not been saved. Continue and discard them?</DialogContent>
      <DialogActions><Button onClick={() => blocker.reset?.()}>Stay</Button><Button color="error" onClick={() => blocker.proceed?.()}>Leave page</Button></DialogActions>
    </Dialog>
  </PageContainer></MonitoringConfigurationWizardLayout>;
}
