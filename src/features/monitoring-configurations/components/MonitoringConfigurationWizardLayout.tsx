import type { PropsWithChildren } from 'react';
import { Box } from '@mui/material';
import { WizardBottomBar } from './WizardBottomBar';

export const configurationWizardSteps = ['General', 'GitLab Connection', 'Scope', 'Policy', 'Scheduling'] as const;

export function MonitoringConfigurationWizardLayout({ children, step, previous, next, nextLabel, previousLabel,
  nextDisabled, busy, final = false }: PropsWithChildren<{ step?: number; previous?: () => void; next: () => void;
  nextLabel?: string; previousLabel?: string; nextDisabled?: boolean; busy?: boolean; final?: boolean }>) {
  return <>
    <Box sx={{ pb: 12 }}>{children}</Box>
    <WizardBottomBar previous={previous} next={next} nextLabel={nextLabel} previousLabel={previousLabel}
      nextDisabled={nextDisabled} busy={busy} final={final} />
  </>;
}
