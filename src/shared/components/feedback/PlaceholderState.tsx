import { ConstructionOutlined } from '@mui/icons-material';
import { StateFrame } from './StateFrame';
export function PlaceholderState({ title, message }: { title: string; message: string }) { return <StateFrame icon={<ConstructionOutlined color="primary" sx={{ fontSize: 42 }} />} title={title} message={message} />; }
