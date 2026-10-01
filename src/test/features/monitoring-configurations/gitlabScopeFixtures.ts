export type ScopeFixtureNode = {
  id: number;
  type: 'group' | 'repository';
  name: string;
  full_path: string;
  parent_group_id?: number;
  expandable: boolean;
};

export const gitlabScopeHierarchy: ScopeFixtureNode[] = [
  { id: 10, type: 'group', name: 'Engineering', full_path: 'engineering', expandable: true },
  { id: 11, type: 'group', name: 'Platform', full_path: 'engineering/platform', parent_group_id: 10, expandable: true },
  { id: 12, type: 'repository', name: 'API', full_path: 'engineering/platform/api', parent_group_id: 11, expandable: false },
  { id: 20, type: 'group', name: 'Research', full_path: 'research', expandable: true },
  { id: 21, type: 'repository', name: 'Miner', full_path: 'research/miner', parent_group_id: 20, expandable: false },
];

export function makeScopeNode(overrides: Partial<ScopeFixtureNode> = {}): ScopeFixtureNode {
  const id = overrides.id ?? 100;
  const type = overrides.type ?? 'group';
  return {
    id,
    type,
    name: overrides.name ?? `node-${id}`,
    full_path: overrides.full_path ?? `namespace/node-${id}`,
    ...(overrides.parent_group_id === undefined ? {} : { parent_group_id: overrides.parent_group_id }),
    expandable: overrides.expandable ?? type === 'group',
  };
}
