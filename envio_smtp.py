"""
Tribulex - Envio de nominas por email via Gmail SMTP.
Lee credenciales desde st.secrets (Streamlit Cloud) o .env (local).
"""

import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def enviar_zip_por_email(
    usuario_smtp,
    password_smtp,
    destinatario,
    nombre_empresa,
    nombre_zip,
    zip_bytes,
    mes="Marzo",
    notas_cliente="",
):
    """
    Envia un ZIP de nominas por email via Gmail SMTP.

    Args:
        usuario_smtp: email del remitente (Gmail).
        password_smtp: contrasena de aplicacion de Google.
        destinatario: email del cliente destino.
        nombre_empresa: nombre de la empresa (para el asunto).
        nombre_zip: nombre del archivo ZIP adjunto.
        zip_bytes: bytes del ZIP a adjuntar.
        mes: mes de las nominas.
        notas_cliente: notas personalizadas del cliente (se incluyen en el cuerpo).

    Returns:
        (True, mensaje_ok) o (False, mensaje_error)
    """
    asunto = f"Nominas {mes} - {nombre_empresa} | Tribulex"

    # ── Cuerpo del email ──────────────────────────────────────────
    lineas = [
        f"Estimado/a cliente,",
        f"",
        f"Adjunto encontrara las nominas del mes de {mes} para {nombre_empresa}.",
        f"",
    ]

    if notas_cliente:
        lineas.append(f"{notas_cliente}")
        lineas.append("")

    lineas.extend([
        f"El archivo adjunto ({nombre_zip}) contiene las nominas individuales en formato PDF.",
        f"",
        f"Si tiene alguna duda, no dude en contactarnos.",
        f"",
        f"Un cordial saludo,",
        f"Tribulex - Gestion de Nominas",
    ])

    cuerpo = "\n".join(lineas)

    # ── Construir mensaje MIME ────────────────────────────────────
    msg = MIMEMultipart()
    msg["From"] = usuario_smtp
    msg["To"] = destinatario
    msg["Subject"] = asunto
    msg.attach(MIMEText(cuerpo, "plain", "utf-8"))

    adjunto = MIMEApplication(zip_bytes, Name=nombre_zip)
    adjunto["Content-Disposition"] = f'attachment; filename="{nombre_zip}"'
    msg.attach(adjunto)

    # ── Enviar via SMTP ───────────────────────────────────────────
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            server.starttls()
            server.login(usuario_smtp, password_smtp)
            server.send_message(msg)
        return True, f"Enviado a {destinatario}"
    except smtplib.SMTPAuthenticationError:
        return False, "Error de autenticacion: verifica usuario y contrasena de aplicacion"
    except smtplib.SMTPRecipientsRefused:
        return False, f"Destinatario rechazado: {destinatario}"
    except Exception as e:
        return False, f"Error SMTP: {e}"
