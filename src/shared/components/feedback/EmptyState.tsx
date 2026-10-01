import { InboxOutlined } from '@mui/icons-material';
import type { ReactNode } from 'react';
import { StateFrame } from './StateFrame';
export function EmptyState({ title = 'Nothing here yet', message, action }: { title?: string; message: string; action?: ReactNode }) { return <StateFrame icon={<InboxOutlined color="disabled" sx={{ fontSize: 44 }} />} title={title} message={message} action={action} />; }
