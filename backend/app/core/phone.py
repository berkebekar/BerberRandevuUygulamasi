"""
phone.py - Turkiye telefon numarasi normalize/eslestirme yardimcilari.
"""


def normalize_tr_phone(phone: str) -> str:
    """
    Girilen numarayi +90XXXXXXXXXX formatina normalize etmeye calisir.
    Bilinmeyen formatlarda girdi trim'lenmis haliyle doner.
    """
    raw = (phone or "").strip()
    digits = "".join(ch for ch in raw if ch.isdigit())

    # 10 haneli GSM: 5XXXXXXXXX
    if len(digits) == 10 and digits.startswith("5"):
        return f"+90{digits}"

    # 11 haneli local: 05XXXXXXXXX
    if len(digits) == 11 and digits.startswith("0") and digits[1] == "5":
        return f"+90{digits[1:]}"

    # 12 haneli ulke kodu ile: 905XXXXXXXXX
    if len(digits) == 12 and digits.startswith("90") and digits[2] == "5":
        return f"+{digits}"

    return raw


def phone_variants(phone: str) -> list[str]:
    """
    DB'de eski/karisik formatli kayitlarla eslesmek icin olasi varyasyonlari dondurur.
    """
    normalized = normalize_tr_phone(phone)
    digits = "".join(ch for ch in normalized if ch.isdigit())
    variants: set[str] = {normalized}

    if len(digits) == 12 and digits.startswith("90") and digits[2] == "5":
        ten_digits = digits[2:]
        variants.add(digits)             # 905XXXXXXXXX
        variants.add(f"0{ten_digits}")   # 05XXXXXXXXX
        variants.add(ten_digits)         # 5XXXXXXXXX

    return list(variants)
