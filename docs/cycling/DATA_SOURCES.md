# Road cycling — Kigali 2025 men's elite

This edition covers actual starters in the **men's elite road race and men's
elite individual time trial at the 2025 UCI Road World Championships**. It is
a championship selection cohort, not a full WorldTour season or a world ranking.
Women, juniors, under-23 events and the mixed team relay are outside this edition.

## Cohort and results

The official [Tissot Timing archive](https://archive.tissottiming.com/2025/crdwch/)
supplies the result lists, stable eleven-digit UCI rider IDs and represented
delegations. These public JSON endpoints are the same sources used by its site:

- [Men's elite road race results](https://prod.server.tissottiming.com/competitions/crdwch2025/events/13/phases/1/results)
- [Men's elite individual time trial results](https://prod.server.tissottiming.com/competitions/crdwch2025/events/2/phases/1/results)
- [Road race teams](https://prod.server.tissottiming.com/competitions/crdwch2025/events/13/phases/1/teams)
- [Time trial teams](https://prod.server.tissottiming.com/competitions/crdwch2025/events/2/phases/1/teams)
- [Official dated time-trial start list](https://prod.server.tissottiming.com/file/0003180200010601FFFFFFFFFFFFFF01)

| Event | Date | Entries | DNS | Actual starts | Classified finishes |
| --- | --- | ---: | ---: | ---: | ---: |
| Men's elite road race | 28 September 2025 | 165 | 1 | 164 | 30 |
| Men's elite individual time trial | 21 September 2025 | 55 | 1 | 54 | 54 |
| Combined | | 220 | 2 | **218** | **84** |

There are **182 unique starters**, representing 66 delegations. Thirty-six riders
started both events. Each is counted once as a person and twice in race starts.
DNS riders contribute no start. DNF, OTL and DSQ outcomes count as starts but not
classified finishes. The road race has 134 DNF results. The six podium positions
contribute six medals; medals and finish positions are preserved in each rider's
event log. A missing placing is never converted into a finish or a medal.

The cohort is joined by UCI ID, never by race number: bibs differ between events.
National-team labels describe representation, including the Refugee Team and
Individual Neutral Athletes. The UCI World Cycling Centre's administrative
Swiss label is not used to turn its riders into Swiss representatives.

Event and team selections use matching contribution splits. Selecting the time
trial therefore counts 54 starts and three medals, even for riders who also
started the road race. Rider profiles and their result logs follow that selection.

## Birthplaces and identity

Birthplace claims and their coordinates come from [Wikidata](https://www.wikidata.org/),
whose structured data is CC0. Candidate people must have a ProCyclingStats cyclist
identifier (P1663), and their names must match an exact source name or alias after
normalizing name order, punctuation and accents. Multiple matching people remain
unresolved. The search rank of a name is never identity evidence.

Where the official time-trial start list supplies a date of birth, Wikidata's DOB
must agree exactly. For other riders the record labels its unique exact-name and
cycling-identifier method explicitly. Ages use the available documented DOB at
**28 September 2025**, with the DOB source retained on each record.

Only an unambiguous recorded birthplace with valid direct coordinates and a
resolved birth-country label enters the map. Country-level places, conflicting
birthplace claims and unresolved identities remain in the public QA list.
Nationality, team headquarters, training bases and current residence are never
substituted for birthplace. Missing geography does not remove a rider from totals.

Each record retains its UCI ID, original official name, event result URLs,
Wikidata identity and birthplace IDs where resolved, and identity method.
`meta.sources` records the URLs and retrieval timestamps for the cached inputs.
The About data tab displays current rider and start coverage from the snapshot.

## Population maps

The three area sizes use H3 resolutions 1, 2 and 3 and **WorldPop Global 2 R2025A,
2025, constrained 1 km country rasters**, licensed CC BY 4.0.
See [WorldPop](https://hub.worldpop.org/project/categories?id=3).
Populated-land reference cells remain visible even when no selected rider was
born there. Layers are rebuilt from this edition's mapped rider IDs; only
resident population totals may be reused from the cache.

Riders per million = unique mapped riders / residents × 1,000,000.
Starts per million = mapped race starts / residents × 1,000,000.
These describe this championship cohort, not the probability of becoming a
professional cyclist. Small samples and incomplete birthplace coverage matter.
Race starts retain their cycling-specific meaning in cross-sport comparisons.

## Rebuild

With the project's Python dependencies installed:

```bash
make rebuild-cycling
```

The builder is `python -m src.ftg.build_cycling_site`. It caches public source
responses under ignored `data/cache/cycling_2025/`, validates both complete event
cohorts, and writes `docs/cycling/data/dashboard.json`. `--force` refreshes inputs.
Raw source documents are retained locally rather than redistributed with the site.

Results attribution: Union Cycliste Internationale / Tissot Timing. Their source
documents remain subject to their respective terms. Map attribution:
OpenStreetMap contributors. Location data: Wikidata (CC0). Population: WorldPop
(CC BY 4.0).
