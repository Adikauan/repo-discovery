# UI Contract: Visual Reference Map

References guide appearance and composition; they do not create business requirements. Precedence
is constitution, specification, plan, then image.

| Reference | Adopt | Do not infer or implement |
|-----------|-------|---------------------------|
| `references/1.png` | Dark sidebar, identity placement, active item treatment, light workspace, title/description hierarchy, search/action row, bordered table, status badges, row-action density | Scheduling terminology, shown records, run actions, CRUD, dates, URLs, profile identity |
| `references/2.png` | Back/title header, four-step rhythm, field spacing, helper text, checkbox groups, form footer and navigation actions | Form values, mining objectives, validation rules, token entry, submission |
| `references/3.png` | Completed/current step treatment, tree panel, indentation, expansion visuals, checkbox alignment, selected-items panel, two-panel layout | GitLab hierarchy retrieval, recursive selection semantics, selected repository state, clearing business data |
| `references/4.png` | Breadcrumb/header/status layout, tabs, metric-card hierarchy, dashboard grid, chart/table containers | Real execution status, dates, report download, metrics, charts, findings, logs, repository results |

## Responsive Interpretation

- Preserve hierarchy and usability, not exact desktop pixels.
- Sidebar becomes a temporary drawer when space is constrained.
- Search/actions wrap or stack; form actions remain ordered and reachable.
- Tree and dashboard columns stack; tables use localized horizontal overflow.
- Decorative sample graphics may be simplified if their detail is not required to validate layout.
