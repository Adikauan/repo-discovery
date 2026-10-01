import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError } from '../../../shared/utils/apiClient';
import { gitlabConnectionApi } from '../api/gitlabConnectionApi';
import type { GitLabConnectionStatus, GitLabValidationResponse } from '../types/gitlabConnection';
function message(error: unknown) { if (error instanceof ApiError) { if (error.status === 404) return 'This Monitoring Configuration is unavailable.'; if (error.status === 409) return error.problem?.detail ?? 'The connection changed. Try again.'; if (error.status === 422) return 'Review the token or GitLab URL and try again.'; return error.message; } return 'The request could not be completed.'; }
export function useGitLabConnection(configurationId: string) {
  const [status, setStatus] = useState<GitLabConnectionStatus>(); const [candidateResult, setCandidateResult] = useState<GitLabValidationResponse>();
  const [loading, setLoading] = useState(true); const [busy, setBusy] = useState(false); const [error, setError] = useState(''); const [notice, setNotice] = useState('');
  const controller = useRef<AbortController | null>(null);
  const run = useCallback(async <T,>(operation: (signal: AbortSignal) => Promise<{ data: T }>) => { if (busy) return undefined; controller.current?.abort(); const next = new AbortController(); controller.current = next; setBusy(true); setError(''); setNotice(''); try { return (await operation(next.signal)).data; } catch (e) { if (!next.signal.aborted) setError(message(e)); return undefined; } finally { setBusy(false); } }, [busy]);
  const refresh = useCallback(async () => { controller.current?.abort(); const next = new AbortController(); controller.current = next; setLoading(true); setError(''); try { setStatus((await gitlabConnectionApi.status(configurationId, next.signal)).data); } catch (e) { if (!next.signal.aborted) setError(message(e)); } finally { if (!next.signal.aborted) setLoading(false); } }, [configurationId]);
  useEffect(() => { void refresh(); return () => controller.current?.abort(); }, [refresh]);
  return { status, candidateResult, loading, busy, error, notice, refresh, clearFeedback: () => { setError(''); setNotice(''); setCandidateResult(undefined); },
    save: async (token: string) => { const value = await run(s => gitlabConnectionApi.save(configurationId, token, s)); if (value) { setStatus(value); setNotice('Credential saved. Validate it when ready.'); } return !!value; },
    remove: async () => { const value = await run(async s => { await gitlabConnectionApi.remove(configurationId, s); return { data: true }; }); if (value) { setCandidateResult(undefined); await refresh(); setNotice('Credential removed.'); return true; } return false; },
    validateSaved: async () => { const value = await run(s => gitlabConnectionApi.validateSaved(configurationId, s)); if (value) { setNotice(value.message); await refresh(); } return !!value; },
    validateCandidate: async (token: string) => { const value = await run(s => gitlabConnectionApi.validateCandidate(configurationId, token, s)); if (value) { setCandidateResult(value); setNotice(value.message); } return !!value; },
  };
}
