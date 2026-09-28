"""
Validate & chuẩn hóa SĐT / email cho PST (multi-market).

Mô hình triển khai:
- Mỗi thị trường là 1 bản build riêng.
- Thị trường của instance lấy từ app setting / biến môi trường PST_MARKET
  (mặc định 'VN'). KHÔNG cần trường country trên record.
- PST chỉ chấp nhận số DI ĐỘNG.

Thêm thị trường mới = thêm 1 entry vào MARKET_RULES + set PST_MARKET khi build.
"""

import os
import re
import pandas as pd


# ---------------------------------------------------------------------------
# CẤU HÌNH THỊ TRƯỜNG
# ---------------------------------------------------------------------------
# cc            : mã quốc gia (không có dấu +)
# mobile_len    : độ dài phần thân di động sau khi bỏ mã vùng / số 0 đầu
# mobile_prefixes: các đầu số di động hợp lệ (ký tự đầu của phần thân)
MARKET_RULES = {
    'VN': {'cc': '84', 'mobile_len': 9,  'mobile_prefixes': ('3', '5', '7', '8', '9')},
    # Ví dụ mở rộng (cần chốt luật thực tế trước khi bật):
    # 'SG': {'cc': '65', 'mobile_len': 8,  'mobile_prefixes': ('8', '9')},
    # 'TH': {'cc': '66', 'mobile_len': 9,  'mobile_prefixes': ('6', '8', '9')},
    # 'MY': {'cc': '60', 'mobile_len': 9,  'mobile_prefixes': ('1',)},  # thực tế 9-10, cần chốt
}

# Thị trường mặc định của bản build hiện tại.
DEFAULT_MARKET = os.environ.get('PST_MARKET', 'VN')


def _rule(market=None):
    return MARKET_RULES[market or DEFAULT_MARKET]


# ---------------------------------------------------------------------------
# PHONE
# ---------------------------------------------------------------------------

def clean_phone(phone, market=None):
    """
    Chuẩn hóa SĐT về E.164 (+<cc><national>) theo thị trường của build.
    Gom mọi biến thể: 0xxxxxxxxx, 84xxxxxxxxx, 840xxxxxxxxx, 8484xxxxxxxxx, +84...
    Không chuẩn hóa được thì vẫn trả về dạng đã gom để validate_phone loại ra.
    """
    rule = _rule(market)
    cc = rule['cc']
    mobile_len = rule['mobile_len']

    if phone is None or (isinstance(phone, float) and pd.isna(phone)):
        return ''
    digits = re.sub(r'\D', '', str(phone))
    if not digits:
        return ''

    if digits.startswith(cc):
        rest = digits[len(cc):]
        # lặp mã vùng: 8484xxxxxxxxx
        if rest.startswith(cc) and (len(rest) - len(cc)) == mobile_len:
            rest = rest[len(cc):]
        # số 0 thừa sau mã vùng: 840xxxxxxxxx
        if rest.startswith('0'):
            rest = rest[1:]
        body = rest
    elif digits.startswith('0'):
        body = digits[1:]
    else:
        body = digits

    return '+' + cc + body


def clean_phone_series(phone_column, market=None):
    """Vectorized wrapper cho pandas Series."""
    return phone_column.apply(lambda p: clean_phone(p, market=market))


def validate_phone(phone, market=None):
    """
    Validate SĐT đã chuẩn hóa (E.164). Chỉ chấp nhận di động.
    Trả True nếu: đúng mã vùng, đúng độ dài, đầu số di động hợp lệ.
    """
    rule = _rule(market)
    cc = rule['cc']
    mobile_len = rule['mobile_len']

    if not phone or not phone.startswith('+' + cc):
        return False

    body = phone[1 + len(cc):]
    if not body.isdigit():
        return False
    if len(body) != mobile_len:
        return False
    return body[0] in set(rule['mobile_prefixes'])


def validate_phone_series(phone_column, market=None):
    """Vectorized wrapper cho pandas Series."""
    return phone_column.apply(lambda p: validate_phone(p, market=market))


# ---------------------------------------------------------------------------
# EMAIL (không phụ thuộc thị trường)
# ---------------------------------------------------------------------------

def clean_email(email_str):
    """Trim, lowercase, sửa lỗi gõ sai domain gmail phổ biến."""
    if email_str is None or (isinstance(email_str, float) and pd.isna(email_str)):
        return ''
    email_str = str(email_str).strip().lower()
    if '@' not in email_str:
        return email_str

    try:
        domain_part = email_str.split('@')[1]
        looks_like_gmail = (
            domain_part.startswith('gm')
            or (domain_part.startswith('g') and domain_part.endswith('il.com'))
        )
        if looks_like_gmail and len(domain_part) <= 11 and domain_part != 'gmail.com':
            email_str = email_str.replace(domain_part, 'gmail.com')
    except IndexError:
        return email_str

    return email_str


def validate_email(email_column):
    """Validate email trong pandas Series -> Boolean Series."""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    regex_valid = email_column.str.match(email_pattern, na=False)

    def additional_validation(email):
        if email is None or (isinstance(email, float) and pd.isna(email)):
            return False
        email = str(email).strip().lower()

        if email in ('', '(empty)', 'n/a', 'na', 'none', 'null'):
            return False
        if '..' in email:
            return False
        if email.count('@') != 1:
            return False

        local_part, domain_part = email.split('@')
        if local_part.startswith('.') or local_part.endswith('.'):
            return False
        if domain_part.startswith('.') or domain_part.endswith('.'):
            return False
        return True

    additional_valid = email_column.apply(additional_validation)
    return regex_valid & additional_valid


# ---------------------------------------------------------------------------
# Quick test
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    print(f'DEFAULT_MARKET = {DEFAULT_MARKET}\n')

    phones = [
        '0912345678', '+84912345678', '84912345678', '840912345678',
        '8484912345678', '02838221234', '123', None, '  090-123-45-67 ',
    ]
    for p in phones:
        c = clean_phone(p)
        print(f'{str(p):>18} -> {c:>15} | valid={validate_phone(c)}')

    print()
    emails = ['A.User@Gmial.com', 'x@gmail.com', 'bad..dot@x.com',
              'no-at-sign', '(empty)', None, 'ok@domain.co']
    s = pd.Series([clean_email(e) for e in emails])
    print(pd.DataFrame({'clean': s, 'valid': validate_email(s)}))