import { Breadcrumbs, Link, Typography } from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import type { BreadcrumbItem } from '../../types/presentation';
export function AppBreadcrumbs({ items }: { items: BreadcrumbItem[] }) { return <Breadcrumbs aria-label="Breadcrumb" sx={{ mb: 1.5 }}>{items.map((item) => item.current || !item.path ? <Typography key={item.label} color="text.primary" aria-current={item.current ? 'page' : undefined} sx={{ fontWeight: item.current ? 650 : 400 }}>{item.label}</Typography> : <Link key={item.label} component={RouterLink} to={item.path} underline="hover" color="text.secondary">{item.label}</Link>)}</Breadcrumbs>; }
