# CSV cleanup with an audit trail

Clean an order export without changing the source file. On the [sample CSV](data/dirty.csv), the script keeps 6 of 14 records. The [audit](example/audit.csv) shows why each row was changed or dropped.

```sh
python clean_csv.py data/dirty.csv --output-dir example
python -m unittest -v
```

The script normalizes dates and amounts, rejects missing or invalid fields, and keeps the first valid record when an order ID repeats. It distinguishes exact duplicates from conflicts. Audit record numbers start at 1 and exclude the header. The sample orders are fictional. Free-text fields are not sanitized for spreadsheet formula execution.

*Built with AI assistance.*
