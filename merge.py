import glob
import polars as pl


for year in ['2024', '2025']:
    q = pl.concat(
        [
            pl.scan_parquet(f, low_memory=True)
            for f in glob.glob(f'./export_data/{year}_*.parquet')
        ],
        how='diagonal_relaxed',
    )
    q.sink_parquet(f'{year}_merged.parquet', compression='zstd', compression_level=12)
