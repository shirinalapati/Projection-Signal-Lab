from psl.admission.run import run_all

if __name__ == "__main__":
    table = run_all(resume=True)
    print(table.groupby(["component", "target", "verdict"]).size())
