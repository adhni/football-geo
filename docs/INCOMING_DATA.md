# Incoming 20-team data

Put CSV or Parquet files in `data/incoming/`. Files may be split by team or season; the importer combines them and records each source filename.

## Canonical fields

| field | required | notes |
|---|---:|---|
| `team` | yes* | Must match the frozen cohort name. Can be derived from `fifa_code`. |
| `fifa_code` | yes* | Must match the frozen cohort code. Can be derived from `team`. |
| `season` | yes* | Canonical form is `2005-06`. Can be derived from `season_end_year`. |
| `season_end_year` | yes* | Integer from 2000 through 2026. Can be derived from `season`. |
| `player_id` | yes* | Stable ID. Generated from profile URL, or name plus DOB when absent. |
| `player_name` | yes | Source player name. |
| `starts` | yes | Whole number; the 11v11 `A` field. |
| `sub_appearances` | yes | Whole number; the 11v11 `S` field. |
| `player_url` | no | Preferred because it makes generated player IDs more reliable. |
| `goals` | no | Defaults to zero. |
| `position_source` | no | Preserve the source wording. |
| `source_url` | no | Strongly recommended for provenance. |
| `retrieved_at` | no | ISO-8601 timestamp when available. |
| `expected_matches` | no | Enables comparison with `11 * matches` in coverage QA. |

`*` means the importer can derive the field from its paired value. It never derives birth country from the represented national team.

Common source headings are accepted without deleting the originals: `country`, `player`, `A`, `S`, `G`, `position`, and `profile_url`.

Use `config/incoming_player_seasons_template.csv` as the canonical header template.

## Import

```bash
python -m src.ftg.import_data --input data/incoming
```

The validated output is `data/processed/player_season_starts.parquet`. Reports are always written to `data/qa/`:

- `ingest_issues.csv`
- `coverage_team_season.csv`
- `coverage_team.csv`

Any error stops publication of a new processed dataset. All incoming rows remain in the source files and every detected problem is reported for correction.
