import type { PropsWithChildren } from 'react'; import { Box } from '@mui/material';
export function DashboardGrid({children,columns=2}:PropsWithChildren<{columns?:number}>){return <Box sx={{display:'grid',gridTemplateColumns:{xs:'1fr',md:`repeat(${columns}, minmax(0,1fr))`},gap:2.25}}>{children}</Box>}
