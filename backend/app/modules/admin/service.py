"""
admin/service.py — Admin panel business logic.

Bu dosya admin dashboard için veri toplama işlemlerini yapar.
HTTP katmanı (router.py) buradan aldığı veriyi response'a çevirir.

Bağımlılıklar:
- booking/service.py: get_bookings_by_date() fonksiyonu dashboard için yeniden kullanılır
  (kod tekrarından kaçınmak için — booking listesi zaten oradan geliyor)
"""

import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.booking import service as booking_service


async def get_dashboard(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    target_date: date,
) -> dict:
    """
    Belirli bir gün için admin dashboard verisini hazırlar.

    Çalışma sırası:
    1. booking_service.get_bookings_by_date() ile o günün tüm randevularını çek
       (bu fonksiyon Booking + User JOIN'i yapıyor — ayrı sorgu gerekmez)
    2. Veriyi DashboardResponse formatına uygun dict olarak döndür

    Neden cancelled randevular da döndürülüyor?
    Admin o günün tam geçmişini görmeli — iptal edilenler de takip edilsin.

    Returns:
        dict: {
            "date": date,
            "bookings": [{"id": ..., "user_first_name": ..., ...}, ...]
        }
    """
    # Günün tüm randevularını müşteri bilgileriyle çek (slot_time ASC sıralı)
    rows = await booking_service.get_bookings_by_date(db, tenant_id, target_date)

    # Her (booking, user) çiftini dashboard item formatına çevir
    bookings = [
        {
            "id": booking.id,
            "user_first_name": user.first_name,
            "user_last_name": user.last_name,
            "user_phone": user.phone,
            "slot_time": booking.slot_time,
            "status": booking.status,
            "cancelled_by": booking.cancelled_by,
        }
        for booking, user in rows
    ]

    return {
        "date": target_date,
        "bookings": bookings,
    }
