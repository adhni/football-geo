.PHONY: test demo ingest birthplaces population app

test:
	pytest -q

demo:
	python -m src.ftg.build_demo

ingest:
	python -m src.ftg.import_data --input data/incoming

birthplaces:
	python -m src.ftg.enrich_wikidata
	python -m src.ftg.build_birthplaces

population:
	python -m src.ftg.build_population_hexes

app: demo
	streamlit run dashboard/app.py
