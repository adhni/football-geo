# Sport explorer feature-parity audit

Audited 14 September 2026. This is the contract for the current static editions, not a promise that unlike sports will use identical terminology.

## Shared map contract

Every published explorer now has:

- a map-first Explore view with its filters immediately above the map;
- a full-width map with rankings in an on-demand desktop drawer or mobile bottom sheet;
- a compact in-map sport switcher that carries the compatible map mode and viewport;
- city/location, country, raw workload and participant-count measures;
- participant and workload population-normalized views at H3 resolutions 1–3;
- searchable locations, comparison, participant table and data-quality views;
- persistent filter state while moving between the four view tabs.

Population rates remain birthplace-only when an edition also publishes a fallback origin. Workload names remain sport-specific; a lap, snap, minute, point, game and appearance are not presented as directly equivalent.

## Edition matrix

| Edition | Primary workload | Geographic lens | Group filtering | Multi-team colour comparison |
| --- | --- | --- | --- | --- |
| Football | Starts / starters | Birthplace | National team | Not yet |
| Cricket | Appearances | Birthplace | Competition and team | Not yet |
| UFC | Bouts | Birthplace or official hometown | Gender and division | Not applicable |
| Formula | Laps / starts | Birthplace | Series and team | Not yet |
| MotoGP | Laps / starts | Birthplace | Series and team | Not yet |
| Volleyball | Sets / matches | Birthplace | Gender and national team | Not yet |
| Tennis | Ranking points | Birthplace | Tour | Not applicable |
| Padel | Ranking points | Birthplace | Division | Not applicable |
| Badminton | Allocated ranking points | Birthplace | Group and event | Not applicable |
| Golf | Ranking points | Birthplace | Ranking | Not applicable |
| AFL | Games | Verified birthplace or labelled football origin | Club | Yes, up to six clubs |
| NRL | Games | Birthplace | Club | Yes, up to six clubs |
| NBA | Minutes / games | Birthplace | Conference and team | Yes, up to six teams |
| NFL | Snaps / games | Birthplace or college | Conference, division and team | Yes, up to six teams |
| NHL | Minutes / games | Birthplace | Conference and team | Yes, up to six teams |
| MLB | Workload / games | Birthplace | League and team | Yes, up to six teams |

## Intentional differences and next candidates

- College geography is NFL-only because the underlying player records contain a separately resolved college dataset.
- AFL football origins and UFC hometowns remain visibly labelled and are excluded from birthplace population rates.
- National-team colour comparison for Football, Cricket and Volleyball is the next sensible parity extension.
- Motorsport constructors need a season-aware colour registry before Formula and MotoGP can safely use the same interaction.
- All-team views stay neutral. Team colours activate only for an explicit selection of one to six teams, preventing an unreadable 17–32-colour map.

