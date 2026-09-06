# Padel 2025 data sources

## Scope

This edition freezes the completed 2025 FIP individual ranking cohort dated 22 December 2025:

- The top 100 men and top 100 women are included.
- Padel matches are played in pairs, but FIP ranks players individually.
- The values are rolling FIP ranking points, not a sum of points earned only during calendar year 2025.
- Men's and women's point totals are best compared within their own division.

The archived 2025 week-51 FIP feed supplies the men's rows. After FIP rebuilt its ranking pages, the same archived women's query stopped returning the ranked cohort. The women's rows therefore use FIP's unchanged week-3 opening ranking from January 2026, which carries forward the final 2025 list. This is explicit in the dashboard metadata rather than silently mixing snapshots.

## Sources

- [FIP rankings](https://www.padelfip.com/fip-rankings/) for stable player IDs, ranks, points, represented-country codes and profile links.
- Individual official FIP player profiles for names, DOB, height, playing side and birthplace labels.
- [FIP's recognition of the 2025 number ones](https://www.padelfip.com/2025/12/fip-ranking-number-ones-honored-in-barcelona/) as an independent top-of-table check.
- [GeoNames](https://www.geonames.org/) for exact-name birthplace coordinates and country labels, under CC BY 4.0.
- [WorldPop Global 2 R2025A](https://hub.worldpop.org/project/categories?id=3) for 2025 population estimates in occupied H3 areas.

## Birthplace resolution

The FIP profile URL comes from the ranking record. Its embedded structured data must repeat the expected player name, and its internal profile ID must agree where present. FIP supplies the birthplace text; GeoNames supplies only coordinates.

Common duplicated names and FIP abbreviations are resolved through a small reviewed place table—for example Valencia, Spain; Posadas, Misiones; and La Puebla del Río. This table does not use represented nationality programmatically. “Chaco” and “Sakhalin” remain unresolved because FIP supplied regions rather than cities.

Represented nationality, residence, training base and partner are never substituted for birthplace. Unresolved records remain visible in public QA.
