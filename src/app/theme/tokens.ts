export const tokens = {
  colors: {
    navy900: '#0d1f3a', navy800: '#142b4d', navy700: '#1d3962',
    blue600: '#1557f0', blue500: '#3478f6', blue100: '#e8f0ff',
    canvas: '#f4f7fb', surface: '#ffffff', border: '#dce4ef',
    text: '#111b35', muted: '#64748b', success: '#087a5b', warning: '#9a5b00',
    danger: '#c92a2a', info: '#1557f0',
  },
  radii: { sm: 8, md: 12, lg: 18 },
  spacing: { pageX: { xs: 2, sm: 3, lg: 4 }, pageY: { xs: 2, md: 3 }, section: 3 },
  content: { maxWidth: 1600 },
  sidebar: { width: 264, narrow: 280 },
  shadows: { card: '0 10px 28px rgba(24, 46, 82, 0.06)' },
} as const;
