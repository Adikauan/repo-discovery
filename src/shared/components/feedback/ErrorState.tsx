import { ErrorOutlined } from '@mui/icons-material';
import type { ReactNode } from 'react';
import { StateFrame } from './StateFrame';
export function ErrorState({ title = 'Something went wrong', message, action }: { title?: string; message: string; action?: ReactNode }) { return <StateFrame role="alert" live="assertive" icon={<ErrorOutlined color="error" sx={{ fontSize: 44 }} />} title={title} message={message} action={action} />; }
