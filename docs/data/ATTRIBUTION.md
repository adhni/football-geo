# Data attribution

## Current GitHub Pages edition

The 2025–26 Big Five player appearance statistics are sourced from Hubert
Sidorowicz's [Football Players Stats (2025–2026)](https://www.kaggle.com/datasets/hubertsidorowicz/football-players-stats-2025-2026)
dataset, version 36, which is published under the MIT License and derived from
FBref. Player birthplace identities and coordinates are supplied by Wikidata
under CC0.

Country boundaries for the choropleth are the 1:110m Admin 0 Countries layer
from [Natural Earth](https://www.naturalearthdata.com/), which is in the public
domain. The committed GeoJSON retains only the properties needed by the site.

Local population totals for the population-normalized map come from
[WorldPop Global 2](https://hub.worldpop.org/project/categories?id=3), 2025
release R2025A, using the 1 km population grid under CC BY 4.0. Totals are
calculated only for occupied H3 resolution-1, resolution-2, and resolution-3
cells from the official country rasters.

The dashboard includes every player with at least one domestic-league
appearance in the Premier League, La Liga, Bundesliga, Serie A, or Ligue 1 in
2025–26. Unresolved birthplace matches remain explicitly flagged.

## Previous World Cup edition

The published dashboard data is derived from the Fjelstul World Cup Database.

- Author: Joshua C. Fjelstul, Ph.D.
- Copyright: © 2023 Joshua C. Fjelstul, Ph.D.
- Source: https://github.com/jfjelstul/worldcup
- Pinned source revision: `35a8667f518b07469182ae16d35574dd0e7a00fb`
- License: CC BY-SA 4.0 — https://creativecommons.org/licenses/by-sa/4.0/

The derived dashboard data is distributed under the same CC BY-SA 4.0 terms. The transformation filters the frozen project cohort, aggregates match-level appearances into player-tournament starts, and adds DOB-validated birthplace entities and coordinates from Wikidata (CC0).
