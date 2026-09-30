import marimo

__generated_with = "0.24.2"
app = marimo.App()


@app.cell
def _():
    import pandas as pd

    return (pd,)


@app.cell
def _(pd):
    df = pd.read_csv(
        "https://raw.githubusercontent.com/datasciencedojo/datasets/refs/heads/master/titanic.csv"
    )
    df


if __name__ == "__main__":
    app.run()
