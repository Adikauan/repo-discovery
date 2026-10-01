import { render } from '@testing-library/react';
import { CssBaseline, ThemeProvider } from '@mui/material';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { routeConfig } from '../app/routes/routeConfig';
import { theme } from '../app/theme/theme';

export function setViewport(width: number) {
  Object.defineProperty(window, 'innerWidth', { configurable: true, value: width });
  window.matchMedia = ((query: string) => ({
    matches: query.includes('min-width') ? width >= Number(query.match(/(\d+(?:\.\d+)?)px/)?.[1] ?? 900) : false,
    media: query, onchange: null, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {}, dispatchEvent() { return true; },
  })) as typeof window.matchMedia;
}

export function renderApp(path = '/', width = 1440) {
  setViewport(width);
  const router = createMemoryRouter(routeConfig, { initialEntries: [path] });
  return { router, ...render(<ThemeProvider theme={theme}><CssBaseline/><RouterProvider router={router}/></ThemeProvider>) };
}
