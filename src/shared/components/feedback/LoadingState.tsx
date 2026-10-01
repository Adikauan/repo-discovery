import { CircularProgress } from '@mui/material';
import { StateFrame } from './StateFrame';
export function LoadingState({ message = 'Loading content…' }: { message?: string }) { return <StateFrame role="status" live="polite" icon={<CircularProgress aria-label="Loading" size={36} />} message={message} />; }
