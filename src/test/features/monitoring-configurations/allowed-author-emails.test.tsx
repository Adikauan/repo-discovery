import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { MonitoringConfigurationForm } from '../../../features/monitoring-configurations/components/MonitoringConfigurationForm';

describe('configuration general form author migration', () => {
  it('does not present or submit the legacy global email textarea', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<MemoryRouter><MonitoringConfigurationForm initial={{ name: 'Example', gitlab_url: 'https://gitlab.example.com' }} submitLabel="Save" onSubmit={onSubmit} /></MemoryRouter>);
    expect(screen.queryByRole('textbox', { name: 'Allowed commit authors' })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));
    await waitFor(() => expect(onSubmit).toHaveBeenCalledWith(expect.not.objectContaining({ allowed_author_emails: expect.anything() })));
  });
});
