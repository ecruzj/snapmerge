from __future__ import annotations
from pathlib import Path
import typer
from .config import Settings
from .pipeline import run_merge

app = typer.Typer()

@app.command()
def merge(
input_dir: Path = typer.Argument(..., exists=True, file_okay=False),
output_pdf: Path = typer.Argument(...),
config: Path = typer.Option(Path("config.yaml"), exists=False),
):
    settings = Settings.from_file(config)
    report = run_merge(input_dir, output_pdf, settings)
    typer.echo(report)

if __name__ == "__main__":
    app()