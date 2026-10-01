import { Autocomplete, TextField } from '@mui/material';

export function TimezoneSelector({ value, options, disabled, error, helperText, onChange }: {
  value: string; options: string[]; disabled?: boolean; error?: boolean; helperText?: string;
  onChange: (timezone: string) => void;
}) {
  const supportedOptions = options ?? [];
  const choices = value && !supportedOptions.includes(value) ? [value, ...supportedOptions] : supportedOptions;
  return <Autocomplete
    options={choices}
    value={value || null}
    disabled={disabled}
    onChange={(_, next) => onChange(next ?? '')}
    renderInput={params => <TextField {...params} label="Timezone" required error={error}
      helperText={helperText ?? 'Choose a supported IANA timezone; this is not inferred from your browser.'} />}
  />;
}
