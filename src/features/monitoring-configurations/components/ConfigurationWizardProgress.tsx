import { Step, StepLabel, Stepper } from '@mui/material';
import { useLocation } from 'react-router-dom';

const steps = ['General', 'GitLab Connection', 'Scope', 'Policy', 'Scheduling'];

export function ConfigurationWizardProgress({ configurationId, currentStep }: { configurationId?: string; currentStep?: number }) {
  const { pathname } = useLocation();
  const routeStep = pathname.endsWith('/edit') || pathname.endsWith('/new') ? 0
    : pathname.endsWith('/gitlab-connection') ? 1
      : pathname.endsWith('/scope') ? 2
        : pathname.endsWith('/authors') ? 3
          : pathname.endsWith('/schedule') ? 4 : undefined;
  const activeStep = routeStep ?? currentStep ?? 0;
  void configurationId;
  return <Stepper activeStep={activeStep} alternativeLabel aria-label="Configuration progress" sx={{ mb: 3, px: { xs: 0, md: 1 }, '& .MuiStepLabel-label': { fontSize: { xs: '.72rem', sm: '.82rem' } } }}>
    {steps.map((label, index) => <Step key={label} completed={index < activeStep} aria-current={index === activeStep ? 'step' : undefined}>
      <StepLabel>{label}</StepLabel>
    </Step>)}
  </Stepper>;
}
