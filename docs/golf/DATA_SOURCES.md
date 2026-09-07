# Golf data notes

This edition freezes the final official 2025 professional world rankings:
OWGR Week 52 ending 28 December for men and WWGR dated 29 December for women.

- Cohort: exact ranks 1–100 from each ranking system.
- Men's ranking: the official [OWGR archive](https://www.owgr.com/archive)
  Week 52 PDF. The builder reads the table by fixed columns and validates all
  ranks before publishing.
- Women's ranking: the official [WWGR archive](https://www.wwgr.net/rankings/2025-12-28)
  CSV, using its stable WWGR player ID.
- Measures: total ranking points, average points and events played are retained.
  OWGR and WWGR are separate systems, so point comparisons should use the tour
  filter rather than treating the two scales as interchangeable.
- Birthplaces: identities are resolved from the WWGR Wikidata identifier or an
  exact golfer page. Wikidata P19 coordinates are preferred; when P19 is
  missing, an explicit English Wikipedia infobox birthplace link may supply the
  place and Wikidata supplies its coordinates. Nationality and residence are
  never substituted. Country-only P19 values remain unresolved except for
  city-states.
- Population: WorldPop 2025 constrained estimates are aggregated to occupied
  H3 cells at resolutions 1–3. Each mapped golfer appears once per resolution.

Raw ranking inputs, HTTP metadata and enrichment responses are cached in the
ignored `data/cache/` and `data/raw/wikidata/` directories. Unresolved golfers
remain visible in the dashboard QA queue.
