"""Re-apply audited verdicts to cached OOS admission rows, then overwrite the canonical table."""

from psl.admission.run import rebuild_cached_admission

if __name__ == "__main__":
    table = rebuild_cached_admission()
    print(table.groupby(["player_type", "verdict"]).size())
    print("wrote artifacts/admission_table.parquet")
