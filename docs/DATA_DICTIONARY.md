# Data Dictionary

## player_season_starts.parquet

| field | type | description |
|---|---|---|
| team | string | national team |
| fifa_code | string | frozen team code |
| season | string | e.g. 2005-06 |
| season_end_year | int | e.g. 2006 |
| player_name | string | source player name |
| player_url | string | 11v11 profile URL |
| starts | int | `A` column from team season table |
| sub_appearances | int | `S` column |
| goals | int | goals if present |
| position_source | string | source position |
| source_url | string | provenance |

## players.parquet

| field | type | description |
|---|---|---|
| player_id | string | stable local ID |
| player_name | string | canonical name |
| dob | date | date of birth |
| birthplace_text | string | raw 11v11 place of birth |
| nationality_source | string | raw source nationality |
| wikidata_qid | string | resolved entity |
| birth_place_qid | string | Wikidata place entity |
| birth_lat | float | latitude |
| birth_lon | float | longitude |
| birth_country | string | country containing birthplace / Wikidata country |
| resolution_confidence | float | 0-1 |

## player_geography.parquet

| field | type | description |
|---|---|---|
| player_id | string | player |
| adm0_code | string | country code |
| adm0_name | string | country |
| adm1_code | string | first-order admin |
| adm1_name | string | first-order admin |
| adm2_code | string | second-order admin |
| adm2_name | string | second-order admin |
| admin_source | string | geometry source/version |

## population_admin.parquet

| field | type | description |
|---|---|---|
| geo_level | string | ADM1 / ADM2 |
| geo_code | string | admin code |
| year | int | population epoch |
| population | float | residents |
| source | string | e.g. GHSL |

## area_metrics.parquet

| field | type | description |
|---|---|---|
| team | string | represented national team |
| geo_level | string | ADM1 / ADM2 |
| geo_code | string | area |
| geo_name | string | display name |
| period_start | int | first season end year |
| period_end | int | last season end year |
| unique_starters | int | players with >=1 start |
| starts | int | sum of starts |
| sub_appearances | int | sum of sub appearances |
| population | float | denominator |
| starts_per_million | float | starts/pop * 1m |
| starters_per_million | float | unique starters/pop * 1m |
