PYTHON ?= python
NODE ?= node

.PHONY: test test-python test-js demo ingest birthplaces worldcup-birthplaces population app preview rebuild-football football-export football-population

test: test-python test-js

test-python:
	$(PYTHON) -m pytest -q

test-js:
	$(NODE) --test tests/js/*.test.cjs

demo:
	$(PYTHON) -m src.ftg.build_demo

ingest:
	$(PYTHON) -m src.ftg.import_data --input data/incoming

birthplaces: worldcup-birthplaces

worldcup-birthplaces:
	$(PYTHON) -m src.ftg.enrich_wikidata --players data/processed/worldcup_players_source.parquet --output data/processed/worldcup_players_enriched.parquet
	$(PYTHON) -m src.ftg.build_birthplaces --starts data/processed/worldcup_player_starts.parquet --players data/processed/worldcup_players_enriched.parquet

population:
	$(PYTHON) -m src.ftg.build_population_hexes --use-rasters

preview:
	$(PYTHON) -m http.server 8000 --directory docs

rebuild-football:
	$(PYTHON) -m src.ftg.import_top5
	$(PYTHON) -m src.ftg.enrich_top5_wikidata
	$(PYTHON) -m src.ftg.build_top5
	$(MAKE) football-export
	$(MAKE) football-population

football-export:
	$(PYTHON) -m src.ftg.export_static_site --input data/processed/top5_players_with_birthplace.parquet --unresolved data/qa/top5_wikidata_resolution_queue.csv

football-population:
	$(PYTHON) -m src.ftg.build_population_hexes --use-rasters --h3-resolution 1 --output docs/data/population_hexes_r1.geojson
	$(PYTHON) -m src.ftg.build_population_hexes --use-rasters --h3-resolution 2 --output docs/data/population_hexes_r2.geojson
	$(PYTHON) -m src.ftg.build_population_hexes --use-rasters --h3-resolution 3 --output docs/data/population_hexes_r3.geojson

app: demo
	streamlit run dashboard/app.py
