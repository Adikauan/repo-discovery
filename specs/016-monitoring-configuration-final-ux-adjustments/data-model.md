# Data Model: Monitoring Configuration Final UX Adjustments

Feature 016 introduces no domain or persistence model changes.

- **Manual execution row action** uses the existing `MonitoringConfiguration.id` as the request identity and the existing execution result. It introduces no stored fields.
- **Selected Scope** remains a presentation of the existing selected Group/Repository scope values. No scope relation or selection semantics change.
- **Final save completion** uses the existing persisted schedule response to determine whether navigation may proceed. It adds no saved state or wizard-step persistence.

No database migration, new table, endpoint, or response field is required.
