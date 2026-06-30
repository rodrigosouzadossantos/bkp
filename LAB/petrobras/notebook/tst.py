import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell
def _():
    import petrobras

    return (petrobras,)


@app.cell
def _(petrobras):
    for i in range(1,5):
        petrobras.run( f'marimo {i}' )
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
