import { getContrastRatio } from '@mui/material/styles';
import { describe, expect, it } from 'vitest';
import { theme } from '../../app/theme/theme';
import { tokens } from '../../app/theme/tokens';

const textPairs = [
  ['primary text on workspace', tokens.colors.text, tokens.colors.canvas],
  ['primary text on surface', tokens.colors.text, tokens.colors.surface],
  ['secondary text on surface', tokens.colors.muted, tokens.colors.surface],
  ['sidebar text', '#d8e3f3', tokens.colors.navy900],
  ['sidebar caption', '#9fb0c8', tokens.colors.navy900],
  ['active navigation text', '#ffffff', '#274d96'],
  ['primary control text', theme.palette.primary.contrastText, theme.palette.primary.main],
  ['success status text', theme.palette.success.contrastText, theme.palette.success.main],
  ['warning status text', theme.palette.warning.contrastText, theme.palette.warning.main],
  ['error status text', theme.palette.error.contrastText, theme.palette.error.main],
  ['information status text', theme.palette.info.contrastText, theme.palette.info.main],
] as const;

describe('WCAG 2.2 AA theme contrast', () => {
  it.each(textPairs)('%s has at least 4.5:1 contrast', (_name, foreground, background) => {
    expect(getContrastRatio(foreground, background)).toBeGreaterThanOrEqual(4.5);
  });

  it.each([
    ['surface', tokens.colors.surface],
    ['workspace', tokens.colors.canvas],
    ['sidebar', tokens.colors.navy900],
  ] as const)('focus indicator against %s has at least 3:1 contrast', (_name, background) => {
    expect(getContrastRatio(tokens.colors.blue500, background)).toBeGreaterThanOrEqual(3);
  });

  it('subtle borders remain distinguishable from adjacent surfaces', () => {
    expect(getContrastRatio(tokens.colors.border, tokens.colors.surface)).toBeGreaterThanOrEqual(1.2);
  });
});
