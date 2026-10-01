import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { WizardBottomBar } from '../../../features/monitoring-configurations/components/WizardBottomBar';

it('keeps Previous on the left and Next on the right in a fixed accessible navigation bar', async () => {
  const user = userEvent.setup();
  const previous = vi.fn(); const next = vi.fn();
  render(<WizardBottomBar previous={previous} previousLabel="Authors" next={next} nextLabel="Scheduling" />);
  const navigation = screen.getByRole('navigation', { name: 'Configuration wizard navigation' });
  expect(getComputedStyle(navigation).position).toBe('fixed');
  expect(screen.getByRole('button', { name: 'Previous step: Authors' })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Next step: Scheduling' })).toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Previous step: Authors' }));
  await user.click(screen.getByRole('button', { name: 'Next step: Scheduling' }));
  expect(previous).toHaveBeenCalledOnce(); expect(next).toHaveBeenCalledOnce();
});

it('omits a nonexistent previous step and labels the final action without another step', () => {
  render(<WizardBottomBar next={() => undefined} nextLabel="Save configuration" final />);
  expect(screen.queryByRole('button', { name: /previous step/i })).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Save configuration' })).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: /next step/i })).not.toBeInTheDocument();
});
