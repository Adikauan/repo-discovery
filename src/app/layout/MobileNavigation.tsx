import { Drawer } from '@mui/material';
import { Sidebar } from './Sidebar';
export function MobileNavigation({ open, onClose }: { open: boolean; onClose: () => void }) { return <Drawer open={open} onClose={onClose} ModalProps={{ keepMounted: true }} slotProps={{ paper: { sx: { width: 264 } } }}><Sidebar onNavigate={onClose} /></Drawer>; }
