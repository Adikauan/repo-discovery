import { useEffect, useRef, useState } from 'react';
import { Alert, Button, Dialog, DialogActions, DialogContent, DialogTitle, Stack, TextField, Typography } from '@mui/material';
import { useBlocker, useLocation, useNavigate, useParams } from 'react-router-dom';
import { ContentCard } from '../../../shared/components/layout/ContentCard';
import { PageContainer } from '../../../shared/components/layout/PageContainer';
import { PageHeader } from '../../../shared/components/layout/PageHeader';
import { ApiError } from '../../../shared/utils/apiClient';
import { monitoringConfigurationsApi } from '../api/monitoringConfigurationsApi';
import { gitlabConnectionApi } from '../api/gitlabConnectionApi';
import { ConfigurationWizardProgress } from '../components/ConfigurationWizardProgress';
import { MonitoringConfigurationWizardLayout } from '../components/MonitoringConfigurationWizardLayout';
import { GitLabConnectionPanel } from '../components/GitLabConnectionPanel';
import { useMonitoringConfigurationWizard } from '../context/MonitoringConfigurationWizardContext';

function safeMessage(error: unknown) {
  return error instanceof ApiError ? error.message : 'The request could not be completed. Try again.';
}

export function GitLabConnectionPage() {
  const { id = '' } = useParams();
  const createMode = !id;
  const wizard = useMonitoringConfigurationWizard();
  const location = useLocation();
  const navigate = useNavigate();
  const [url, setUrl] = useState(wizard.gitlabUrl);
  const [token, setToken] = useState('');
  const [validated, setValidated] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');
  const [editDirty, setEditDirty] = useState(false);
  const [credentialDirty, setCredentialDirty] = useState(false);
  const allowNavigation = useRef(false);
  const blocker = useBlocker(() => createMode
    ? !allowNavigation.current && (!!token || !!url)
    : !allowNavigation.current && editDirty);
  useEffect(() => {
    const beforeUnload = (event: BeforeUnloadEvent) => {
      if (createMode ? (!url && !token) : !editDirty) return;
      event.preventDefault(); event.returnValue = '';
    };
    window.addEventListener('beforeunload', beforeUnload);
    return () => window.removeEventListener('beforeunload', beforeUnload);
  }, [createMode, url, token, editDirty]);

  useEffect(() => {
    if (!createMode) return;
    if (!wizard.general && !wizard.createdConfigurationId) navigate('/monitoring-configurations/new', { replace: true });
  }, [createMode, wizard.general, wizard.createdConfigurationId, navigate]);

  useEffect(() => {
    if (wizard.createdConfigurationId && location.pathname === `/monitoring-configurations/${wizard.createdConfigurationId}/scope`) wizard.clear();
  }, [location.pathname, wizard.createdConfigurationId]);

  async function validateCandidate() {
    if (!url.trim() || !token.trim()) { setError('Enter a GitLab instance URL and access token.'); return false; }
    setBusy(true); setError(''); setStatus(''); setValidated(false);
    try {
      const result = await gitlabConnectionApi.validateUnpersistedCandidate(url.trim(), token);
      if (result.data.state !== 'validated') { setError(result.data.message); return false; }
      setValidated(true); setStatus(result.data.message); return true;
    } catch (reason) { setError(safeMessage(reason)); return false; }
    finally { setBusy(false); }
  }

  async function createAndSave() {
    if (!wizard.general) { navigate('/monitoring-configurations/new', { replace: true }); return; }
    setBusy(true); setError('');
    try {
      let configurationId = wizard.createdConfigurationId;
      if (!validated) {
        const valid = await validateCandidate();
        if (!valid) return;
      }
      if (!configurationId) {
        const created = await monitoringConfigurationsApi.create({
          name: wizard.general.name,
          description: wizard.general.description || null,
          gitlab_url: url.trim(),
          allowed_author_emails: [],
        }, wizard.idempotencyKey);
        configurationId = created.data.id;
        wizard.setCreatedConfigurationId(configurationId);
      }
      const saved = await gitlabConnectionApi.save(configurationId, token);
      const validation = await gitlabConnectionApi.validateSaved(configurationId);
      if (validation.data.state !== 'validated') throw new Error(validation.data.message || 'The saved credential could not be validated.');
      setToken('');
      allowNavigation.current = true;
      navigate(`/monitoring-configurations/${configurationId}/scope`, { replace: true,
        state: { notice: 'Monitoring Configuration and GitLab credential saved.' } });
      return saved;
    } catch (reason) {
      setError(safeMessage(reason));
    } finally { setBusy(false); }
  }

  if (!createMode) {
    function continueEdit() {
      if (credentialDirty) { setError('Save or validate the entered credential before continuing.'); return; }
      (document.getElementById('gitlab-connection-url-form') as HTMLFormElement | null)?.requestSubmit();
    }
    return <MonitoringConfigurationWizardLayout step={1} previous={() => navigate(`/monitoring-configurations/${id}/edit`)}
      previousLabel="General" next={continueEdit} nextLabel="Scope">
      <PageContainer>
        <PageHeader title="GitLab Connection" description="Configure the GitLab instance and credential used by this Monitoring Configuration."
          breadcrumbs={[{ label: 'Monitoring Configurations', path: '/monitoring-configurations' }, { label: 'Configuration', path: `/monitoring-configurations/${id}` }, { label: 'GitLab Connection', current: true }]} />
        <ContentCard><ConfigurationWizardProgress configurationId={id} currentStep={1} />
          {error && <Alert severity="error" role="alert" sx={{ mb: 2 }}>{error}</Alert>}
          <ConnectionUrlForm configurationId={id} onDirtyChange={setEditDirty} onSaved={() => setStatus('GitLab URL saved.')}
            onContinue={() => { allowNavigation.current = true; setEditDirty(false); navigate(`/monitoring-configurations/${id}/scope`); }} />
        </ContentCard>
        <GitLabConnectionPanel configurationId={id} onDirtyChange={value => { setCredentialDirty(value); setEditDirty(value); }} />
      </PageContainer>
      <Dialog open={blocker.state === 'blocked'} onClose={() => blocker.reset?.()} aria-labelledby="discard-gitlab-edit-title">
        <DialogTitle id="discard-gitlab-edit-title">Discard unsaved GitLab Connection changes?</DialogTitle>
        <DialogContent>Your URL or credential input has not been saved. A transient token will be cleared if you leave.</DialogContent>
        <DialogActions><Button onClick={() => blocker.reset?.()}>Stay</Button><Button color="error" onClick={() => { setEditDirty(false); setCredentialDirty(false); allowNavigation.current = true; blocker.proceed?.(); }}>Discard changes</Button></DialogActions>
      </Dialog>
    </MonitoringConfigurationWizardLayout>;
  }

  return <MonitoringConfigurationWizardLayout step={1} previous={() => navigate('/monitoring-configurations/new')} previousLabel="General"
    next={createAndSave} nextLabel={wizard.createdConfigurationId ? 'Retry and continue' : 'Create and continue'} busy={busy}>
    <PageContainer>
      <PageHeader title="GitLab Connection" description="Validate the instance and credential before creating this configuration."
        breadcrumbs={[{ label: 'Monitoring Configurations', path: '/monitoring-configurations' }, { label: 'New', path: '/monitoring-configurations/new' }, { label: 'GitLab Connection', current: true }]} />
      <ContentCard>
        <ConfigurationWizardProgress currentStep={1} />
        <Stack spacing={2}>
          <TextField label="GitLab instance URL" required fullWidth value={url} disabled={!!wizard.createdConfigurationId}
            placeholder="https://gitlab.example.com" onChange={event => { setUrl(event.target.value); wizard.setGitlabUrl(event.target.value); setValidated(false); setStatus(''); }} />
          <Typography variant="body2" color="text.secondary">Credentials are sent to the server for transient validation and are never returned or stored until you create the configuration.</Typography>
          <TextField label="GitLab access token" required fullWidth type="password" autoComplete="new-password" value={token}
            onChange={event => { setToken(event.target.value); setValidated(false); setStatus(''); }} />
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
            <Button variant="outlined" disabled={busy || !token || !url} onClick={() => void validateCandidate()}>
              {busy ? 'Validating…' : validated ? 'Connection validated' : 'Validate connection'}
            </Button>
            {token && !wizard.createdConfigurationId && <Button disabled={busy} onClick={() => { setToken(''); setValidated(false); }}>Clear token</Button>}
          </Stack>
          {status && <Alert severity="success" role="status">{status}</Alert>}
          {error && <Alert severity="error" role="alert">{error}</Alert>}
          {wizard.createdConfigurationId && <Alert severity="info">Configuration created. Retry will save the credential and continue without creating a duplicate.</Alert>}
        </Stack>
      </ContentCard>
      <Dialog open={blocker.state === 'blocked'} onClose={() => blocker.reset?.()} aria-labelledby="discard-connection-draft-title">
        <DialogTitle id="discard-connection-draft-title">Leave GitLab Connection?</DialogTitle>
        <DialogContent>The candidate token is kept only in this form. Leaving clears it; the non-secret URL and configuration identity are retained for this wizard attempt.</DialogContent>
        <DialogActions><Button onClick={() => blocker.reset?.()}>Stay</Button><Button color="error" onClick={() => { setToken(''); setValidated(false); allowNavigation.current = true; blocker.proceed?.(); }}>Leave step</Button></DialogActions>
      </Dialog>
    </PageContainer>
  </MonitoringConfigurationWizardLayout>;
}

function ConnectionUrlForm({ configurationId, onSaved, onContinue, onDirtyChange }: { configurationId: string; onSaved: () => void; onContinue: () => void; onDirtyChange: (dirty: boolean) => void }) {
  const [url, setUrl] = useState(''); const [etag, setEtag] = useState(''); const [error, setError] = useState(''); const [saving, setSaving] = useState(false);
  useEffect(() => { let live = true; monitoringConfigurationsApi.get(configurationId).then(result => { if (live) { setUrl(result.data.gitlab_url); setEtag(result.etag ?? `"${result.data.version}"`); } }).catch(reason => { if (live) setError(safeMessage(reason)); }); return () => { live = false; }; }, [configurationId]);
  async function saveUrl(advance = false) {
    setSaving(true); setError('');
    try { const existing = await monitoringConfigurationsApi.get(configurationId); const result = await monitoringConfigurationsApi.update(configurationId,
      { name: existing.data.name, description: existing.data.description, gitlab_url: url, enabled: existing.data.enabled }, etag);
      setEtag(result.etag ?? `"${result.data.version}"`); onSaved(); onDirtyChange(false);
      if (advance) {
        const credential = await gitlabConnectionApi.status(configurationId);
        if (credential.data.credential_configured) {
          const validation = await gitlabConnectionApi.validateSaved(configurationId);
          if (validation.data.state !== 'validated') throw new Error(validation.data.message || 'Validate the GitLab credential before continuing.');
        }
        onContinue();
      }
    } catch (reason) { setError(safeMessage(reason)); } finally { setSaving(false); }
  }
  return <form id="gitlab-connection-url-form" onSubmit={event => { event.preventDefault(); void saveUrl(true); }}>
    <Stack spacing={2}><TextField label="GitLab instance URL" required fullWidth value={url} onChange={event => { setUrl(event.target.value); onDirtyChange(true); }} />
      {error && <Alert severity="error" role="alert">{error}</Alert>}<Button type="button" onClick={() => void saveUrl()} disabled={saving || !url.trim()}>Save GitLab URL</Button>
    </Stack>
  </form>;
}
