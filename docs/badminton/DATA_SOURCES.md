# Badminton data notes

This edition freezes the official BWF World Ranking published on 30 December
2025. In BWF's archive it is stored as week 1 of 2026 because the date falls in
that ISO week.

- Cohort: men's and women's singles ranks 1–100; men's, women's and mixed
  doubles ranks 1–50.
- Rankings: [BWF World Rankings](https://bwfbadminton.com/rankings/). The build
  caches text-rendered copies of the five official archive pages under the
  ignored `data/cache/badminton_2025/` directory.
- Doubles: a pair is the ranking unit. Its full rank, points and tournament
  count are retained; half of its points are allocated to each partner only for
  geographic aggregation. The two halves always reconcile to the pair total.
- Deduplication: the BWF player ID is the stable athlete key. An athlete listed
  in more than one event appears once in league-wide athlete counts and keeps a
  separate event split for filtering.
- Birthplaces: the same BWF ID is matched to Wikidata property P3620, then its
  explicit place-of-birth statement and coordinates are used. Represented
  association is never substituted for birthplace. Country-only P19 values are
  left unresolved because a national centroid is not a local birthplace
  (Singapore is retained as a city-state).
- Population: WorldPop 2025 constrained estimates are aggregated to occupied
  H3 cells at resolutions 1–3. Only verified birthplaces enter per-capita maps.

Unresolved athletes remain in the dashboard QA queue. The principal future
improvement is to verify missing birthplaces from official federation or player
profiles and add cited overrides without inferring them from nationality.
