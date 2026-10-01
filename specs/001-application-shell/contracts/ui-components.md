# UI Contract: Shared Components

## Layout

- `AppShell`: owns responsive navigation and one main-content landmark; renders routed content.
- `Sidebar`: renders identity, primary navigation, active state, and optional isolated presentation
  profile. It contains no authentication behavior.
- `PageContainer`: applies shared content width, responsive gutters, and vertical rhythm.
- `PageHeader`: composes title, optional description, breadcrumbs/back navigation, status, and
  actions without assuming a feature.
- `ContentCard` and `SectionHeader`: establish reusable surface and section hierarchy.

## Feedback and Status

- `LoadingState`: communicates progress accessibly and does not present stale content as current.
- `EmptyState`: distinguishes a valid empty collection from a deferred placeholder.
- `ErrorState`: explains failure and accepts an optional recovery action.
- `StatusBadge`: accepts only supported presentation statuses and always renders a text label.
- Alerts, helper text, and validation messages use shared theme treatment and correct semantic
  association with their triggering control or field.

## Listing and Forms

- Listing layout composes title/description, search, page actions, table region, status column, and
  actions column. Feature pages own columns, row wording, and action availability.
- Table overflow stays within a labeled container on narrow screens.
- Form layout provides label, required indicator, helper text, validation placement, and responsive
  action groups. It does not provide configuration-specific validation.

## Wizard

- `WizardShell` is controlled: the consumer supplies steps, current step, content, and navigation
  callbacks.
- Current and completed steps are conveyed by text/semantics as well as color and icons.
- Back, Next, and Cancel use meaningful accessible labels and predictable keyboard order.
- The shared component never performs GitLab calls, repository selection, validation, submission,
  or persistence.

## Tree and Dashboard

- Tree primitives render hierarchy, expansion affordance, selection visuals, and a selected-items
  panel from supplied presentation data; they define no recursive selection rules.
- Dashboard primitives arrange header, tabs, metrics, sections, chart placeholders, and table
  regions. They calculate no metrics and import no charting library.

## Accessibility

All components conform to WCAG 2.2 Level AA in their documented composition, expose native
semantics wherever possible, use ARIA only to fill semantic gaps, support keyboard interaction,
show visible focus, and never communicate meaning through color alone.
