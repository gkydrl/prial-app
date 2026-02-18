from decimal import Decimal
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import aiosmtplib
from app.config import settings


EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head><meta charset="UTF-8"><style>
  body {{ font-family: Arial, sans-serif; background: #f5f5f5; }}
  .container {{ max-width: 600px; margin: 40px auto; background: #fff; border-radius: 12px; overflow: hidden; }}
  .header {{ background: #6C47FF; color: #fff; padding: 24px; text-align: center; }}
  .header h1 {{ margin: 0; font-size: 24px; }}
  .content {{ padding: 32px; }}
  .price-badge {{ background: #f0edff; border-radius: 8px; padding: 16px; margin: 20px 0; text-align: center; }}
  .price-now {{ font-size: 36px; font-weight: bold; color: #6C47FF; }}
  .price-target {{ font-size: 14px; color: #888; }}
  .btn {{ display: inline-block; background: #6C47FF; color: #fff; padding: 14px 32px;
          border-radius: 8px; text-decoration: none; font-weight: bold; margin-top: 16px; }}
  .footer {{ text-align: center; padding: 16px; color: #aaa; font-size: 12px; }}
</style></head>
<body>
<div class="container">
  <div class="header">
    <h1>🔔 Fiyat Alarmı Tetiklendi!</h1>
  </div>
  <div class="content">
    <p>Merhaba,</p>
    <p>Takip ettiğiniz ürünün fiyatı hedef fiyatınızın altına indi!</p>
    <p><strong>{product_title}</strong></p>
    <div class="price-badge">
      <div class="price-now">{current_price} TL</div>
      <div class="price-target">Hedef fiyatınız: {target_price} TL</div>
    </div>
    <center>
      <a href="{product_url}" class="btn">Ürüne Git</a>
    </center>
  </div>
  <div class="footer">
    Bu e-postayı Prial fiyat alarmı için aldınız.<br>
    Bildirim tercihlerinizi uygulama üzerinden değiştirebilirsiniz.
  </div>
</div>
</body>
</html>
"""


async def send_alarm_email(
    to_email: str,
    product_title: str,
    product_url: str,
    target_price: Decimal,
    current_price: Decimal,
    image_url: str | None = None,
) -> None:
    html = EMAIL_TEMPLATE.format(
        product_title=product_title[:100],
        product_url=product_url,
        target_price=target_price,
        current_price=current_price,
    )

    message = MIMEMultipart("alternative")
    message["Subject"] = f"Prial: Fiyat Düştü! {product_title[:50]}"
    message["From"] = f"{settings.email_from_name} <{settings.email_from}>"
    message["To"] = to_email
    message.attach(MIMEText(html, "html"))

    await aiosmtplib.send(
        message,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user,
        password=settings.smtp_password,
        start_tls=True,
    )
