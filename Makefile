.PHONY: test demo app

test:
	pytest -q

demo:
	python -m src.ftg.build_demo

app: demo
	streamlit run dashboard/app.py
