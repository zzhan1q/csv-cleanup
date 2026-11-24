"""Normalize the example order export and keep an audit trail."""
import argparse
import csv
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

FIELDS = ("order_id", "date", "product", "amount_usd")
AUDIT = ("record", "order_id", "action", "details")


def normalize(row):
    if None in row or any(value is None for value in row.values()):
        raise ValueError("wrong number of fields")
    order, raw_date, product, price = (row[field].strip() for field in FIELDS)
    if not order or not raw_date or not product or not price:
        raise ValueError("required field is blank")
    parsed = None
    for pattern in ("%Y-%m-%d", "%Y/%m/%d", "%d.%m.%Y"):
        try:
            parsed = datetime.strptime(raw_date, pattern).date()
            break
        except ValueError:
            continue
    if not isinstance(parsed, date):
        raise ValueError("invalid date or unsupported date format")
    try:
        amount = Decimal(price)
        if not amount.is_finite() or not 0 <= amount <= 1_000_000 or amount != round(amount, 2):
            raise ValueError("amount must be 0–1000000 with at most two decimal places")
    except InvalidOperation as exc:
        raise ValueError("invalid amount") from exc
    return dict(zip(FIELDS, (order.upper(), parsed.isoformat(), product, f"{abs(amount):.2f}")))


def clean(rows):
    cleaned, audit, seen = [], [], {}
    for index, raw in enumerate(rows, 1):
        order = (raw.get("order_id") or "").strip().upper()
        try:
            row = normalize(raw)
        except ValueError as exc:
            audit.append((index, order, "rejected", str(exc)))
            continue
        if order in seen:
            action = "duplicate" if seen[order] == row else "conflict"
            audit.append((index, order, action, "kept first valid record"))
            continue
        seen[order] = row
        cleaned.append(row)
        changes = [field for field in FIELDS if raw[field] != row[field]]
        if changes:
            audit.append((index, order, "normalized", ", ".join(changes)))
    return cleaned, audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir / "cleaned.csv"
    log = args.output_dir / "audit.csv"
    if args.source.resolve() in {output.resolve(), log.resolve()}:
        parser.error("output must not overwrite the source")
    try:
        with args.source.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream, strict=True)
            header = reader.fieldnames or []
            if len(header) != len(FIELDS) or set(header) != set(FIELDS):
                parser.error(f"expected columns: {', '.join(FIELDS)}")
            rows, audit = clean(reader)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        with log.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(AUDIT)
            writer.writerows(audit)
    except (OSError, UnicodeError, csv.Error) as exc:
        parser.exit(1, f"{exc}\n")
    print(f"{len(rows)} kept; {len(audit)} audit entries")


if __name__ == "__main__":
    main()
