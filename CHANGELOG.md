# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](http://semver.org/).


## [v0.3.1] - 2026-01-30

### Added

- Limit on the amount of trunks used to request metrics (max 100 trunk IDs per request) [#39](https://github.com/splunk/genesys_cloud_ta/pull/39).
- Compatibility with Splunk 10.x [#41](https://github.com/splunk/genesys_cloud_ta/pull/41).


## [v0.3.0] - 2025-09-18

### Added

- `Actions Metrics` and `Audit Query` inputs to collect data from the following endpoints ([#36](https://github.com/splunk/genesys_cloud_ta/pull/36)):
  - `/api/v2/analytics/actions/aggregates/query`, and
  - `/api/v2/audits/query`

### Changed

- Details regarding the terraform automation to ingest extra data using the AWS EventBridge integration


## [v0.2.2] - 2025-08-12

### Added

- Option to configure start date to the `conversations details` input. This could avoid errors such as the one reported below: too many events in pagination ([#37](https://github.com/splunk/genesys_cloud_ta/pull/37))

```bash
Exception when calling ConversationsApi->post_analytics_conversations_details_query: [400] Bad Request - Pagination may not exceed 100000 results.

Tip: When extracting large chunks of data (multiple days/weeks), maximize pagination performance by querying in smaller intervals. For example, paging through 1am-2am, then 2am-3am, then 3am-4am, and so forth will outperform paging through one large interval that covers the same time frame.
```

### Changed

- Minors in user aggregates input and in the genesys cloud client ([#37](https://github.com/splunk/genesys_cloud_ta/pull/37))


## [v0.2.1] - 2025-06-16

### Added

- Default values to inputs dropdowns ([#35](https://github.com/splunk/genesys_cloud_ta/pull/35))
- External links in the navigation bar of the TA to provide a quick way to:
  - go to documentation ([#35](https://github.com/splunk/genesys_cloud_ta/pull/35))
  - report an issue ([#35](https://github.com/splunk/genesys_cloud_ta/pull/35))

### Fixed

- `NoneType` error thrown under specific circumstances by the `conversation_details` input ([#35](https://github.com/splunk/genesys_cloud_ta/pull/35))


## [v0.2.0] - 2025-05-15

### Fixed

- Reported `NoneType` errors ([#31](https://github.com/splunk/genesys_cloud_ta/pull/31))

### Changed

- Fields in `app.manifest` ([#31](https://github.com/splunk/genesys_cloud_ta/pull/31))
- Checkpoint strategy (#30, [#31](https://github.com/splunk/genesys_cloud_ta/pull/31))
- Logging for inputs ([#30](https://github.com/splunk/genesys_cloud_ta/pull/30), [#31](https://github.com/splunk/genesys_cloud_ta/pull/31))

### Removed

- Usage of lookups to avoid issues in distributed environments ([#31](https://github.com/splunk/genesys_cloud_ta/pull/31))


## [v0.1.0] - 2025-04-28

### Added

- Operational input to collect system services status ([#21](https://github.com/splunk/genesys_cloud_ta/pull/21))
- Custom tab _Configuration / Add More Data_ to inform users about AWS EventBridge integration availability and give some guidance ([#27](https://github.com/splunk/genesys_cloud_ta/pull/27))
- Genesys Cloud client initialisation via environment variable configuration ([#24](https://github.com/splunk/genesys_cloud_ta/pull/24))
- Automated tests ([#24](https://github.com/splunk/genesys_cloud_ta/pull/24))

### Removed

- Analytics input `Chat Observations` as per [#19](https://github.com/splunk/genesys_cloud_ta/issues/19) ([#25](https://github.com/splunk/genesys_cloud_ta/pull/25))

### Fixed

- Analytics input `Conversations Metrics` as per [#19](https://github.com/splunk/genesys_cloud_ta/issues/19) ([#25](https://github.com/splunk/genesys_cloud_ta/pull/25))
- Cloud vetting failure [#23](https://github.com/splunk/genesys_cloud_ta/issues/23) ([#26](https://github.com/splunk/genesys_cloud_ta/pull/26))

### Changed

- Events refactoring pre-indexing for analytic inputs:
  - `Queue Observations` ([#27](https://github.com/splunk/genesys_cloud_ta/pull/27))
  - `Conversations Metrics` ([#25](https://github.com/splunk/genesys_cloud_ta/pull/25))
- Checkpointers for user inputs `User Aggregates` and `User Routing Statuses` ([#24](https://github.com/splunk/genesys_cloud_ta/pull/24))
- License ([#21](https://github.com/splunk/genesys_cloud_ta/pull/21))


## [v0.0.1] - 2025-03-19

### Added

- Initial version of the Add-On

### Fixed

- py3.7 compatibility with GenesysCloud SDK version 221.0.0 ([#4](https://github.com/splunk/genesys_cloud_ta/pull/4))
