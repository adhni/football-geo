from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SEED = ROOT / "data" / "seed"
OUT = ROOT / "data" / "processed"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    squad = pd.read_csv(SEED / "italy_2005_06_11v11.csv")
    summary = squad.groupby("position", as_index=False).agg(
        players=("player", "nunique"), starts=("starts", "sum"), sub_appearances=("sub_appearances", "sum")
    )
    summary.to_csv(OUT / "demo_position_summary.csv", index=False)

    final = pd.read_csv(SEED / "italy_2006_final_starters.csv")
    area = final.groupby(["birth_country", "adm1"], as_index=False).agg(players=("player", "nunique"))
    area.to_csv(OUT / "demo_birth_area_summary.csv", index=False)
    print(f"Demo outputs written to {OUT}")


if __name__ == "__main__":
    main()
