# UI Contract: Navigation and Routes

## Registered Destinations

| Path | Page title | Primary section | Breadcrumb expectation |
|------|------------|-----------------|------------------------|
| `/` | Home | Home | None required |
| `/monitoring-configurations` | Monitoring Configurations | Monitoring Configurations | None required |
| `/monitoring-configurations/new` | New Monitoring Configuration | Monitoring Configurations | Listing > current page |
| `/monitoring-configurations/:id` | Monitoring Configuration Details | Monitoring Configurations | Listing > display-safe reference |
| `/monitoring-configurations/:id/executions` | Configuration Executions | Monitoring Configurations | Listing > display-safe reference > Executions |
| `/executions` | Executions | Executions | None required |
| `/executions/:id` | Execution Details | Executions | Executions > display-safe reference |
| `/settings` | Settings | Settings | None required |

## Behavioral Contract

- Every route renders inside exactly one `AppShell`.
- Direct entry and in-app link navigation produce the same title, active section, and breadcrumbs.
- Home, Monitoring Configurations, Executions, and Settings remain reachable from every route.
- Nested monitoring routes keep Monitoring Configurations active; execution details keep Executions
  active. Configuration-specific executions remain owned by Monitoring Configurations.
- Parent breadcrumb items are links; the current item is identified semantically and is not a
  redundant link.
- On narrow viewports, navigation opens from a labeled button, traps focus only while open, closes
  after selection or dismissal, and restores focus appropriately.
- Unknown route handling may use a simple not-found state but must not invent business recovery.
- Route parameters are display-only in this feature and must be formatted safely before rendering.
