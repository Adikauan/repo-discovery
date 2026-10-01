import { CssBaseline, ThemeProvider } from '@mui/material'; import { RouterProvider } from 'react-router-dom'; import { theme } from './theme/theme'; import { router } from './routes/router';
export function App(){return <ThemeProvider theme={theme}><CssBaseline/><RouterProvider router={router}/></ThemeProvider>}
