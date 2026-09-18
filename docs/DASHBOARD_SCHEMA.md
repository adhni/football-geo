# Dashboard JSON contract

The static site reads `docs/data/dashboard.json` for football and
`docs/<sport>/data/dashboard.json` for other editions. Python builders own these
files; frontends consume them. This describes their existing common contract,
including the football exception. Source-specific fields remain documented in
each sport's `DATA_SOURCES.md`.

## Envelope

| Field | Meaning |
| --- | --- |
| `meta` | Cohort scope, snapshot year/season, groups, generation time and source attribution |
| `summary` | Full-snapshot participant and workload totals plus mapping coverage |
| `records` | Participant records; football uses participant/club/season rows |
| `unresolved` | Public QA entries with a name and resolution status |

Metadata is sport-specific: football has `years` and `leagues`; most other
editions have `year`, `season` and `conferences`. Consumers must not infer the
cohort from `generated_at`, which is the export time rather than the data period.

## Participant records

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | string | Stable identifier within an edition; not a cross-sport identity |
| `name` | string | Display name |
| `team` | string | Primary team, tour, series or ranking group |
| `year` | integer | Edition's snapshot year |
| `teamCode`, `conference`, `division` | string, optional | Sport-specific group labels |
| `teams` | string array, optional | All represented teams/groups |
| `teamSplits` | object array, optional | Contributions to each represented team/group |
| `dob`, `age` | string/number or null | Source date of birth and age at the edition's frozen date |
| `mapped` | boolean | Whether a publishable map location exists |
| `place`, `country` | string or null | Map location labels |
| `lat`, `lon` | number or null | Latitude/longitude, in that order |
| `status` | string | Resolution result, including reasons for unresolved locations |
| `locationType` | string, optional | `birthplace` or an explicitly labelled fallback origin |

Mapped coordinates must be finite and within latitude ±90 and longitude ±180.
Unmapped players remain in records, totals and QA. A fallback can be mapped
without being a verified birthplace. Absent `locationType` is treated as
birthplace for older editions. AFL football origins and UFC hometowns are
excluded from population layers. NFL college fields form a separate lens and
are not birthplace population denominators.

## Identity and contributions

Football records repeat the same `id` for different club/season contributions.
For example, two rows with starts of 20 and 17 represent **one person with 37
starts**, not two people and not one row chosen arbitrarily. Count unique IDs
for people and sum contributions for workloads. This is the intended contract;
the cross-sport comparison's football deduplication remains a known follow-up.

Other editions currently publish one record per participant. Where present,
`teamSplits` partitions the participant's contributions between teams or groups.
When filtering to a team, use its matching split rather than assigning the
whole season to the primary team. Count the participant once even if multiple
splits match. Ranking fields such as `rank` require their configured minimum
operation rather than summation; other split statistics follow the edition's
`teamSplitStats` configuration.

## Workload units

The shared navigation registry in `docs/assets/sport-navigation.js` declares the
comparison workload field for each sport:

| Editions | Field | Unit |
| --- | --- | --- |
| Football | `starts` | Starting appearances |
| Cricket | `appearances` | Match appearances |
| UFC | `bouts` | Fighter-bout appearances |
| Formula, MotoGP | `laps` | Completed laps |
| Volleyball | `sets` | Sets played |
| Athletics | `entries` | Unique athlete-event starts |
| Tennis, padel, badminton, golf | `points` | Edition-specific ranking points |
| AFL, NRL | `games` | Games played |
| NBA, NHL | `minutes` | Minutes played |
| NFL | `snaps` | Snaps played |
| MLB | `minutes` | Workload alias: plate appearances plus batters faced |

`league-app.js` projects the configured `workloadField` into `row.minutes` in
memory. That internal alias does not change the unit. Use edition labels for
display; raw workloads and separate ranking systems are not directly equivalent
across sports. Badminton doubles points are allocated between partners.

Summary coverage keys also vary by sport. The edition's
`qualityWorkloadCoverageField`, `qualityMappedWorkloadField` and
`qualityTotalWorkloadField` select the appropriate fields. Do not derive these
keys by assuming every field pluralizes the same way.

## Population GeoJSON

Each dashboard is accompanied by `population_hexes_r1.geojson`,
`population_hexes_r2.geojson` and `population_hexes_r3.geojson`.

| Feature property | Meaning |
| --- | --- |
| `hex_id` | H3 cell identifier, including its resolution |
| `population`, `population_year` | Resident denominator and its year |
| `area_km2`, `population_density` | Cell area and population per km² |
| `player_ids` | Unique birthplace-mapped participant IDs in this cell |
| `all_players` | Number of those IDs in the unfiltered snapshot |
| `reference_cell` | True when the published cell has no mapped participant IDs |
| `players_per_million` | Unfiltered player count / population × 1,000,000; null if denominator unavailable |
| `label`, `country` | Representative labels, not polygon boundaries or nationality |

Top-level `metadata` records source, license, method, raster/H3 resolution and
coverage totals. Geometry may be Polygon or MultiPolygon for cells crossing the
antimeridian. A cell can span several countries; its country label does not
restrict the resident denominator to that country.

Editions may opt into populated-land reference cells. These cells have an
empty `player_ids` list and remain visible when filters leave an area with no
selected participants. Cells with a zero population denominator are omitted.

For a filtered view, intersect `player_ids` with the selected unique players,
sum their matching workload contributions, then divide by the same resident
denominator. Rebuild all three layers whenever participant membership or
birthplace coordinates change. Population totals may be cached; membership and
rates must always derive from the current dashboard.
