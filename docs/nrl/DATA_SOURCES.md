# NRL data sources

## Scope

The published cohort covers all 204 completed matches in the 2025 men's NRL
regular season. Finals and women's competitions are outside this edition.
Games are player appearances in aggregate match rows.

## Sources and processing

- Match and player statistics: Champion Data competition `12755` fixture and
  match JSON feeds. The builder reads `playerStats`, not `playerPeriodStats`,
  and removes unused reserves whose aggregate match statistics are all zero.
- Birthplaces: Wikidata entities matched by exact normalised player name and
  accepted only when the entity is explicitly classified as a rugby league
  player or has rugby league as its sport. Ambiguous and coordinate-less results
  remain unresolved.
- Population: WorldPop Global 2 R2025A.

Raw responses and retrieval metadata are cached under ignored `data/cache/` and
`data/raw/` paths. The committed dashboard retains Champion Data player IDs,
club splits, geographic provenance, and the unresolved QA queue.
