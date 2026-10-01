import { createContext, useCallback, useContext, useMemo, useState, type PropsWithChildren } from 'react';

export interface GeneralDraft {
  name: string;
  description: string;
  enabled: boolean;
}

interface WizardDraftState {
  general: GeneralDraft | null;
  gitlabUrl: string;
  idempotencyKey: string;
  createdConfigurationId: string | null;
  setGeneral: (value: GeneralDraft) => void;
  setGitlabUrl: (value: string) => void;
  begin: () => void;
  setCreatedConfigurationId: (id: string) => void;
  clear: () => void;
}

const WizardDraftContext = createContext<WizardDraftState | null>(null);
const createKey = () => globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;

export function MonitoringConfigurationWizardProvider({ children }: PropsWithChildren) {
  const [general, setGeneralState] = useState<GeneralDraft | null>(null);
  const [gitlabUrl, setGitlabUrl] = useState('');
  const [idempotencyKey, setIdempotencyKey] = useState(createKey);
  const [createdConfigurationId, setCreatedConfigurationId] = useState<string | null>(null);
  const begin = useCallback(() => {
    setGeneralState(null);
    setGitlabUrl('');
    setCreatedConfigurationId(null);
    setIdempotencyKey(createKey());
  }, []);
  const value = useMemo<WizardDraftState>(() => ({ general, gitlabUrl, idempotencyKey, createdConfigurationId,
    setGeneral: setGeneralState, setGitlabUrl, begin, setCreatedConfigurationId, clear: () => {
      setGeneralState(null); setGitlabUrl(''); setCreatedConfigurationId(null); setIdempotencyKey(createKey());
    } }), [general, gitlabUrl, idempotencyKey, createdConfigurationId, begin]);
  return <WizardDraftContext.Provider value={value}>{children}</WizardDraftContext.Provider>;
}

export function useMonitoringConfigurationWizard() {
  const state = useContext(WizardDraftContext);
  if (!state) throw new Error('MonitoringConfigurationWizardProvider is missing.');
  return state;
}
