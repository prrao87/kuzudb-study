from pathlib import Path

import polars as pl


def write_parquet(df: pl.DataFrame, filepath: str | Path, compression_level: int = 10) -> None:
    df.write_parquet(
        file=filepath,
        # compression="gzip",
        # compression_level=compression_level,
        use_pyarrow=True,
    )
