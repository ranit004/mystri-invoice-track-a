import re
from datetime import date
from decimal import Decimal, ROUND_HALF_UP


HEADERS = {
    'invoices': ['customer_id', 'invoice_number', 'amount', 'due_date'],
    'payments': ['payment_id', 'customer_id', 'invoice_number', 'amount'],
}


def to_paise(val):
    if val is None:
        return 0
    if isinstance(val, int) and val > 10000000:
        return val
    d = Decimal(str(val))
    return int((d * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def normalize(row, kind, customer_ids):
    result = {}
    for key in HEADERS[kind]:
        value = row.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f'{key} is required')
        result[key] = value.strip()
    if result['customer_id'] not in customer_ids:
        raise ValueError('Unknown customer_id')
    if not re.fullmatch(r'\d+(?:\.\d{1,2})?', result['amount']):
        raise ValueError('amount must be a positive decimal with at most two decimal places')
    amt_decimal = Decimal(result['amount'])
    if not (Decimal('0') < amt_decimal <= Decimal('10000000')):
        raise ValueError('amount must be greater than zero and at most 10000000')
    result['amount'] = int((amt_decimal * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    if kind == 'invoices':
        try:
            parsed = date.fromisoformat(result['due_date'])
            if parsed.isoformat() != result['due_date']:
                raise ValueError()
        except ValueError:
            raise ValueError('due_date must be YYYY-MM-DD') from None
    return result


def classify_error(msg):
    s = str(msg).lower()
    if 'is required' in s:
        field = s.split(' ')[0] if s.split(' ') else None
        return {'code': 'MISSING_FIELD', 'field': field}
    if 'unknown customer_id' in s:
        return {'code': 'UNKNOWN_CUSTOMER', 'field': 'customer_id'}
    if 'amount' in s:
        return {'code': 'INVALID_AMOUNT', 'field': 'amount'}
    if 'due_date' in s:
        return {'code': 'INVALID_DATE', 'field': 'due_date'}
    if 'already exists' in s:
        field = 'payment_id' if 'payment' in s else 'invoice_number'
        return {'code': 'CONFLICTING_RECORD', 'field': field}
    return {'code': 'ROW_FORMAT_ERROR', 'field': None}


