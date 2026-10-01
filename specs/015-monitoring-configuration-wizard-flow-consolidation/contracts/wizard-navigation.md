# Wizard Navigation Contract

## Step order

| Index | Label | Create route | Existing-configuration route | Bottom-right action |
|---:|---|---|---|---|
| 1 | General | `/monitoring-configurations/new` | `/monitoring-configurations/{id}/edit` | Next |
| 2 | GitLab Connection | `/monitoring-configurations/new/gitlab-connection` | `/monitoring-configurations/{id}/gitlab-connection` | Next |
| 3 | Scope | Reached after successful creation at `/monitoring-configurations/{id}/scope` | `/monitoring-configurations/{id}/scope` | Next |
| 4 | Authors | `/monitoring-configurations/{id}/authors` | `/monitoring-configurations/{id}/authors` | Next |
| 5 | Scheduling | `/monitoring-configurations/{id}/schedule` | `/monitoring-configurations/{id}/schedule` | Save schedule (final) |

Existing `/:id` remains the read-only overview for compatibility. It has no configuration section shortcut, Enable/Disable, or Delete action. The list's Edit opens General; Open/name may open the overview. New-mode Connection without a General draft returns to General. Invalid IDs follow existing not-found handling. Progress labels are not interactive; only the fixed bottom bar navigates steps.

## Save and progression semantics

| Mode/step | Before moving forward | Previous/exit behavior |
|---|---|---|
| Create / General | Validate Name and existing General fields; keep valid values in memory only. No configuration create request. | Back/Cancel goes to the list; warn before dropping a dirty draft. |
| Create / GitLab Connection | Validate candidate URL/token server-side without persistence. After success, Next creates once with the existing create API, saves the token securely, and validates the saved token so its current validation state is recorded. Advance only after success. | Back returns to General. A transient unsubmitted token must be cleared only after explicit discard. |
| Edit / General | Existing configuration update with current ETag; GitLab URL is carried unchanged because the current update contract is full-resource. | Existing dirty-change behavior; no implicit save. |
| Edit / GitLab Connection | Save changed URL with current ETag; preserve existing candidate/replacement and saved-validation flow for tokens. Refresh current ETag after the URL mutation. | Existing dirty-change behavior; no implicit save. |
| Scope | Invoke existing scope replace/save only when dirty; wait for success. | Existing scope confirmation for dirty selection. |
| Authors | Invoke existing policy save-all only when dirty; wait for success. | Existing author-policy dirty guard. |
| Scheduling | Invoke existing schedule validation/save; on success show existing success feedback and remain on step 5. | Existing schedule dirty guard. |

Any validation or save failure keeps the active step and makes the existing safe error available. New-mode configuration creation is idempotent for retry; after an ID is known, retry does not issue another create request.

## Action placement

- Enable/Disable: General only, after a configuration exists. New configurations keep their current disabled default.
- Delete: Monitoring Configurations list only, with existing confirmation and delete operation.
- No configuration-header actions for Edit General, Configure Scope, Configure Scheduling, Enable, or Delete.

## Shared bottom bar

The bottom bar belongs to the application's main content region, remains fixed at the viewport bottom, and leaves scroll padding for its full height. Previous is on the left; Next/final action is on the right. Step 1 has no previous wizard step. Step 5 has no next step. Labels, focus, disabled state, and keyboard access remain understandable at narrow widths.
