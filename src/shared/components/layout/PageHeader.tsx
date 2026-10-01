import type { ReactNode } from 'react';
import { Box, IconButton, Stack, Typography } from '@mui/material';
import { ArrowBackRounded } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import type { BreadcrumbItem } from '../../types/presentation';
import { AppBreadcrumbs } from '../navigation/AppBreadcrumbs';

export function PageHeader({ title, description, breadcrumbs, action, status, back }: { title: string; description?: string; breadcrumbs?: BreadcrumbItem[]; action?: ReactNode; status?: ReactNode; back?: boolean }) { const navigate = useNavigate(); return <Box sx={{ mb: 3, minWidth: 0 }}>{breadcrumbs && <AppBreadcrumbs items={breadcrumbs} />}<Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 2, flexWrap: 'wrap' }}><Stack direction="row" spacing={1.25} sx={{ alignItems: 'flex-start', minWidth: 0, maxWidth: '100%' }}>{back && <IconButton aria-label="Go back" onClick={() => navigate(-1)} sx={{ mt: .3 }}><ArrowBackRounded /></IconButton>}<Box sx={{ minWidth: 0, maxWidth: '100%' }}><Stack direction="row" spacing={1.5} sx={{ alignItems: 'center', flexWrap: 'wrap', minWidth: 0 }}><Typography component="h1" variant="h1" sx={{ overflowWrap: 'anywhere' }}>{title}</Typography>{status}</Stack>{description && <Typography color="text.secondary" sx={{ mt: .75, fontSize: 17, overflowWrap: 'anywhere' }}>{description}</Typography>}</Box></Stack>{action}</Box></Box>; }
