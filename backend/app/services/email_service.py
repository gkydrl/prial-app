import asyncio
from decimal import Decimal
import resend
from app.config import settings


def _client():
    resend.api_key = settings.resend_api_key


ALARM_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head><meta charset="UTF-8"><style>
  body {{ font-family: Arial, sans-serif; background: #f5f5f5; }}
  .container {{ max-width: 600px; margin: 40px auto; background: #fff; border-radius: 12px; overflow: hidden; }}
  .header {{ background: #0A1628; color: #fff; padding: 24px; text-align: center; }}
  .header h1 {{ margin: 0; font-size: 22px; }}
  .content {{ padding: 32px; }}
  .price-badge {{ background: #EFF6FF; border-radius: 8px; padding: 16px; margin: 20px 0; text-align: center; }}
  .price-now {{ font-size: 36px; font-weight: bold; color: #1D4ED8; }}
  .price-target {{ font-size: 14px; color: #888; margin-top: 4px; }}
  .btn {{ display: inline-block; background: #1D4ED8; color: #fff; padding: 14px 32px;
          border-radius: 8px; text-decoration: none; font-weight: bold; margin-top: 16px; }}
  .footer {{ text-align: center; padding: 16px; color: #aaa; font-size: 12px; }}
</style></head>
<body>
<div class="container">
  <div class="header"><h1>Fiyat Alarmı Tetiklendi</h1></div>
  <div class="content">
    <p>Merhaba,</p>
    <p>Takip ettiğiniz ürünün fiyatı hedef fiyatınızın altına indi!</p>
    <p><strong>{product_title}</strong></p>
    <div class="price-badge">
      <div class="price-now">{current_price} ₺</div>
      <div class="price-target">Hedef fiyatınız: {target_price} ₺</div>
    </div>
    <center><a href="{product_url}" class="btn">Ürüne Git</a></center>
  </div>
  <div class="footer">
    Bu e-postayı Prial fiyat alarmı için aldınız.<br>
    Bildirim tercihlerinizi uygulama üzerinden değiştirebilirsiniz.
  </div>
</div>
</body></html>
"""

RESET_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head><meta charset="UTF-8"><style>
  body {{ font-family: Arial, sans-serif; background: #f5f5f5; }}
  .container {{ max-width: 600px; margin: 40px auto; background: #fff; border-radius: 12px; overflow: hidden; }}
  .header {{ background: #0A1628; color: #fff; padding: 24px; text-align: center; }}
  .header h1 {{ margin: 0; font-size: 22px; }}
  .content {{ padding: 32px; color: #333; line-height: 1.6; }}
  .btn {{ display: inline-block; background: #1D4ED8; color: #fff; padding: 14px 32px;
          border-radius: 8px; text-decoration: none; font-weight: bold; margin-top: 20px; }}
  .note {{ font-size: 12px; color: #888; margin-top: 24px; }}
  .footer {{ text-align: center; padding: 16px; color: #aaa; font-size: 12px; }}
</style></head>
<body>
<div class="container">
  <div class="header"><h1>Şifre Sıfırlama</h1></div>
  <div class="content">
    <p>Merhaba,</p>
    <p>Prial hesabınız için şifre sıfırlama talebinde bulundunuz.</p>
    <p>Aşağıdaki butona tıklayarak yeni şifrenizi belirleyebilirsiniz:</p>
    <center><a href="{reset_url}" class="btn">Şifremi Sıfırla</a></center>
    <p class="note">
      Bu bağlantı <strong>1 saat</strong> geçerlidir.<br>
      Eğer bu talebi siz yapmadıysanız bu e-postayı görmezden gelebilirsiniz.
    </p>
  </div>
  <div class="footer">Prial · destek@prial.com</div>
</div>
</body></html>
"""


async def send_alarm_email(
    to_email: str,
    product_title: str,
    product_url: str,
    target_price: Decimal,
    current_price: Decimal,
    image_url: str | None = None,
) -> None:
    _client()
    html = ALARM_TEMPLATE.format(
        product_title=product_title[:100],
        product_url=product_url,
        target_price=target_price,
        current_price=current_price,
    )
    await asyncio.to_thread(
        resend.Emails.send,
        {
            "from": f"{settings.from_email_name} <{settings.from_email}>",
            "to": [to_email],
            "subject": f"Fiyat Düştü: {product_title[:60]}",
            "html": html,
        },
    )


async def send_password_reset_email(to_email: str, reset_token: str) -> None:
    _client()
    reset_url = f"prial://reset-password?token={reset_token}"
    html = RESET_TEMPLATE.format(reset_url=reset_url)
    await asyncio.to_thread(
        resend.Emails.send,
        {
            "from": f"{settings.from_email_name} <{settings.from_email}>",
            "to": [to_email],
            "subject": "Prial - Şifre Sıfırlama",
            "html": html,
        },
    )
