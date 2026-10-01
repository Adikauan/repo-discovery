import type { WizardStepDescriptor } from '../../../shared/types/presentation';
export const wizardSteps:WizardStepDescriptor[]=[{id:'general',label:'General information',state:'completed'},{id:'connection',label:'GitLab connection',state:'completed'},{id:'repositories',label:'Repository selection',state:'current'},{id:'schedule',label:'Scheduling',state:'upcoming'}];
export const hierarchyFixtures=[{label:'platform',depth:0,kind:'group' as const,expanded:true},{label:'backend',depth:1,kind:'group' as const,expanded:true},{label:'api-gateway',depth:2,kind:'repository' as const,selected:true},{label:'auth-service',depth:2,kind:'repository' as const},{label:'frontend',depth:1,kind:'group' as const,expanded:true},{label:'web-app',depth:2,kind:'repository' as const,selected:true}];

export const authorPolicyScopeFixtures = {
  groups: [{ id: 17, name: 'backend', fullPath: 'sequor/backend' }],
  repositories: [{ id: 42, name: 'api-gateway', fullPath: 'sequor/backend/api-gateway' }],
} as const;

export const authorPolicyBranchFixtures = [
  { name: 'main', commitSha: 'a'.repeat(40), isDefault: true },
  { name: 'release/2026-q4', commitSha: 'b'.repeat(40), isDefault: false },
] as const;

export const authorPolicyFixtures = {
  repositoryPolicies: [
    { repositoryId: 42, branch: 'main', allowedAuthorEmails: ['a@example.com'] },
    { repositoryId: 42, branch: 'release/2026-q4', allowedAuthorEmails: ['b@example.com'] },
  ],
  groupPolicies: [{ groupId: 17, allowedAuthorEmails: ['group@example.com'] }],
} as const;
