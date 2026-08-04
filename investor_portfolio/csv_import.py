"""
CSV holdings import — parse + validate only. Nothing here writes to the
database; the view applies the returned rows after the user confirms the
preview (see investor_portfolio/views.py:portfolio_import_confirm).

Expected columns (header row required, case-insensitive, order-independent):
    ticker, company_name, quantity, avg_price, currency, acquisition_date

Only `ticker` OR `company_name` and `quantity` are required per row.
"""
import csv
import datetime
import io
from decimal import Decimal, InvalidOperation

from league.models import Company

REQUIRED_ANY_OF = ('ticker', 'company_name')
EXPECTED_COLUMNS = ('ticker', 'company_name', 'quantity', 'avg_price', 'currency', 'acquisition_date')


def _parse_decimal(raw, field_name, errors):
    raw = (raw or '').strip()
    if not raw:
        return None
    try:
        value = Decimal(raw)
    except InvalidOperation:
        errors.append(f'{field_name} "{raw}" is not a valid number')
        return None
    return value


def _parse_date(raw, errors):
    raw = (raw or '').strip()
    if not raw:
        return None
    for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y'):
        try:
            return datetime.datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    errors.append(f'acquisition_date "{raw}" is not a recognised date (use YYYY-MM-DD)')
    return None


def parse_holdings_csv(file_obj, existing_company_ids=None):
    """
    Returns a list of row dicts:
      {row_number, raw, status ('matched'|'unmatched'|'invalid'|'duplicate'),
       errors: [...], company_id, company_name, ticker, quantity, avg_price,
       currency, acquisition_date}

    `existing_company_ids` — company IDs already held in the target
    portfolio, so a CSV row for an already-held company is flagged as a
    duplicate rather than silently creating a second Holding row (Holding
    is one-per-company — see models.py).
    """
    existing_company_ids = set(existing_company_ids or [])
    seen_in_file = set()

    text = file_obj.read()
    if isinstance(text, bytes):
        text = text.decode('utf-8-sig', errors='replace')
    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames:
        normalized_fields = {f.strip().lower(): f for f in reader.fieldnames}
    else:
        normalized_fields = {}

    rows = []
    for i, raw_row in enumerate(reader, start=2):  # header is row 1
        row = {(k or '').strip().lower(): (v or '').strip() for k, v in raw_row.items() if k}
        errors = []

        ticker = row.get('ticker', '')
        company_name = row.get('company_name', '')

        company = None
        if ticker:
            company = Company.objects.filter(ticker__iexact=ticker).first()
        if company is None and company_name:
            company = Company.objects.filter(name__iexact=company_name).first()

        quantity = _parse_decimal(row.get('quantity', ''), 'quantity', errors)
        if quantity is None and 'quantity' not in errors:
            errors.append('quantity is required')
        elif quantity is not None and quantity <= 0:
            errors.append('quantity must be greater than zero')

        avg_price = _parse_decimal(row.get('avg_price', ''), 'avg_price', errors)
        currency = (row.get('currency') or 'USD').upper()[:8]
        acquisition_date = _parse_date(row.get('acquisition_date', ''), errors)

        if not ticker and not company_name:
            errors.append('either ticker or company_name is required')

        status = 'invalid' if errors else 'matched'
        if not errors and company is None:
            status = 'unmatched'
            errors.append(f'No EcoIQ company found for ticker="{ticker}" name="{company_name}"')
        elif not errors and company is not None:
            if company.pk in existing_company_ids or company.pk in seen_in_file:
                status = 'duplicate'
                errors.append(f'{company.name} already has a holding in this portfolio (or repeats in this file)')

        if company is not None:
            seen_in_file.add(company.pk)

        rows.append({
            'row_number': i,
            'raw': row,
            'status': status,
            'errors': errors,
            'company_id': company.pk if company else None,
            'company_name': company.name if company else (company_name or ticker),
            'ticker': company.ticker if company else ticker,
            'quantity': str(quantity) if quantity is not None else '',
            'avg_price': str(avg_price) if avg_price is not None else '',
            'currency': currency,
            'acquisition_date': acquisition_date.isoformat() if acquisition_date else '',
        })

    return rows


def summarize_rows(rows):
    return {
        'total': len(rows),
        'matched': sum(1 for r in rows if r['status'] == 'matched'),
        'unmatched': sum(1 for r in rows if r['status'] == 'unmatched'),
        'invalid': sum(1 for r in rows if r['status'] == 'invalid'),
        'duplicate': sum(1 for r in rows if r['status'] == 'duplicate'),
    }


def export_holdings_csv(snapshot_holding_rows):
    """
    Builds CSV text for a portfolio's holdings + calculated EcoIQ exposure
    fields, from the holding_snapshots list already computed by
    calculations.compute_portfolio_snapshot (never recomputed here).
    """
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        'company_name', 'ticker', 'sector', 'country', 'shares', 'currency',
        'market_value', 'weight_pct', 'classification', 'evidence_confidence',
        'report_date', 'stale_report', 'missing_market_data',
    ])
    for r in snapshot_holding_rows:
        writer.writerow([
            r.get('company_name', ''), r.get('ticker', ''), r.get('sector_display', ''),
            r.get('country', ''), r.get('shares', ''), r.get('currency', '') or '',
            r.get('market_value', '') or '', r.get('weight_pct', ''),
            r.get('classification', '') or 'none', r.get('evidence_confidence', '') or '',
            r.get('report_date', '') or '', r.get('stale_report', False),
            r.get('missing_market_data', False),
        ])
    return buf.getvalue()
