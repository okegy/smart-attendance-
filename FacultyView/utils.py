import qrcode
import socket
import os
from io import BytesIO
from django.conf import settings


def get_client_ip(request):
    """
    Extract the real client IP address from the request.
    Handles X-Forwarded-For for reverse proxy setups,
    falls back to REMOTE_ADDR for direct connections.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Take the first IP (the original client)
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


def get_local_ip():
    """
    Get the local network IP of this machine.
    Used to generate the QR code URL that students will scan.
    Falls back to 127.0.0.1 if no network is available.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2)
        # Connect to a public DNS to determine local IP
        # This doesn't actually send any data
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except (socket.error, OSError):
        return "127.0.0.1"


def generate_qr_code(qr_token, port=8000):
    """
    Generate a QR code image containing the attendance URL.
    The URL points to the student mark-attendance page with the daily token.
    
    Returns the absolute path to the saved QR code image.
    """
    local_ip = get_local_ip()
    url = f"http://{local_ip}:{port}/qr-entry/{qr_token}/"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#10b981", back_color="#0a0a0f")

    # Save to static directory
    static_dir = os.path.join(settings.BASE_DIR, 'static', 'qr')
    os.makedirs(static_dir, exist_ok=True)
    filepath = os.path.join(static_dir, f'session_{qr_token}.png')
    img.save(filepath)

    return filepath, url


def get_user_agent(request):
    """Extract User-Agent string from request headers."""
    return request.META.get('HTTP_USER_AGENT', '')
