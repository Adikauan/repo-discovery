import { Button, ListItem, ListItemText } from '@mui/material';
import type { GitLabScopeRule } from '../types/gitlabScope';

export function UnavailableScopeItem({ kind, item, onRemove }: {
  kind: 'groups' | 'repositories'; item: GitLabScopeRule; onRemove: () => void;
}) {
  const typeName = kind === 'groups' ? 'Group' : 'Repository';
  const reason = item.availability === 'stale' ? 'from a different GitLab instance'
    : item.availability === 'unavailable' ? 'unavailable to this credential' : 'could not be checked';
  return <ListItem divider secondaryAction={<Button size="small" color="error" aria-label={`Remove ${typeName.toLowerCase()} ${item.name}`} onClick={onRemove}>Remove</Button>}>
    <ListItemText primary={`${typeName}: ${item.name}`} secondary={`${item.full_path} — ${reason}`} />
  </ListItem>;
}
