.PHONY: test demo ingest app

test:
	pytest -q

demo:
	python -m src.ftg.build_demo

ingest:
	python -m src.ftg.import_data --input data/incoming

app: demo
	streamlit run dashboard/app.py
