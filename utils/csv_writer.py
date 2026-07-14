import csv
from pathlib import Path

ACCOUNT_SUMMARY_FILE_PATH = (
    Path(__file__).resolve().parent.parent / "logs" / "account_summary.csv"
)
RAID_SUMMARY_FILE_PATH = (
    Path(__file__).resolve().parent.parent / "logs" / "raid_summary.csv"
)

_csv_writer = None


class CSVWriter:
    def __init__(self, configs):
        self.writers = {}

        for name, config in configs.items():
            file = open(config["path"], "a", newline="", encoding="utf-8")
            writer = csv.DictWriter(file, fieldnames=config["fieldnames"])

            if Path(config["path"]).stat().st_size == 0:
                writer.writeheader()

            self.writers[name] = {
                "file": file,
                "writer": writer,
            }

    def write(self, table, row):
        self.writers[table]["writer"].writerow(row)

    def close(self):
        for item in self.writers.values():
            item["file"].close()


def setup_csv_writer():
    global _csv_writer

    if _csv_writer is None:
        _csv_writer = CSVWriter(
            {
                "account_summary": {
                    "path": ACCOUNT_SUMMARY_FILE_PATH,
                    "fieldnames": [
                        "start_time",
                        "stop_time",
                        "account_name",
                        "townhall_level",
                        "total_attacked",
                        "total_skipped",
                        "total_gold",
                        "total_elixir",
                        "total_dark_elixir",
                    ],
                },
                "raid_summary": {
                    "path": RAID_SUMMARY_FILE_PATH,
                    "fieldnames": [
                        "timestamp",
                        "account_name",
                        "attacked",
                        "townhall_level",
                        "attack_duration_ms",
                        "gold_available",
                        "elixir_available",
                        "dark_elixir_available",
                        "gold_looted",
                        "elixir_looted",
                        "dark_elixir_looted",
                    ],
                },
            }
        )

    return _csv_writer
