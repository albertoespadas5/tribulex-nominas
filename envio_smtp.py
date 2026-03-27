"""
Tribulex - Envio de nominas por email via Gmail SMTP.
Lee credenciales desde st.secrets (Streamlit Cloud) o .env (local).
Soporta redaccion inteligente con Gemini AI.
"""

import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def generar_cuerpo_estandar(nombre_empresa, nombre_zip, mes):
    """Genera el cuerpo de email estandar (sin IA)."""
    return (
        f"Estimado/a cliente,\n"
        f"\n"
        f"Adjunto encontrara las nominas del mes de {mes} para {nombre_empresa}.\n"
        f"\n"
        f"El archivo adjunto ({nombre_zip}) contiene las nominas individuales en formato PDF.\n"
        f"\n"
        f"Si tiene alguna duda, no dude en contactarnos.\n"
        f"\n"
        f"Un cordial saludo,\n"
        f"Tribulex - Gestion de Nominas"
    )


def generar_cuerpo_ia(nombre_empresa, nombre_zip, mes, notas_cliente, gemini_api_key):
    """
    Usa Gemini para redactar un correo profesional que incorpore las notas
    del cliente de forma natural en el cuerpo del email.

    Returns:
        (True, texto_generado) o (False, mensaje_error)
    """
    try:
        import google.generativeai as genai

        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")

        prompt = (
            f"Redacta un correo electronico profesional y breve en español para enviar "
            f"las nominas del mes de {mes} a la empresa {nombre_empresa}.\n\n"
            f"El archivo adjunto se llama '{nombre_zip}' y contiene las nominas "
            f"individuales en PDF.\n\n"
            f"INSTRUCCION IMPORTANTE DEL CLIENTE que debes incorporar de forma natural "
            f"en el cuerpo del correo:\n"
            f'"{notas_cliente}"\n\n'
            f"Reglas:\n"
            f"- Tono profesional y cercano.\n"
            f"- No uses asteriscos, negritas ni formato markdown.\n"
            f"- Maximo 8 lineas de texto.\n"
            f"- Firma como 'Tribulex - Gestion de Nominas'.\n"
            f"- Devuelve SOLO el cuerpo del correo, sin asunto ni encabezados extra."
        )

        response = model.generate_content(prompt)
        texto = response.text.strip()
        return True, texto

    except Exception as e:
        return False, f"Error Gemini: {e}"


def enviar_zip_por_email(
    usuario_smtp,
    password_smtp,
    destinatario,
    nombre_empresa,
    nombre_zip,
    zip_bytes,
    mes="Marzo",
    cuerpo_email="",
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
        cuerpo_email: texto del cuerpo (ya sea estandar, editado o generado por IA).

    Returns:
        (True, mensaje_ok) o (False, mensaje_error)
    """
    asunto = f"Nominas {mes} - {nombre_empresa} | Tribulex"

    if not cuerpo_email:
        cuerpo_email = generar_cuerpo_estandar(nombre_empresa, nombre_zip, mes)

    # ── Construir mensaje MIME ────────────────────────────────────
    msg = MIMEMultipart()
    msg["From"] = usuario_smtp
    msg["To"] = destinatario
    msg["Subject"] = asunto
    msg.attach(MIMEText(cuerpo_email, "plain", "utf-8"))

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
