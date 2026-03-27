"""
Tribulex - Extractor de emails desde archivos PDF y envío por Outlook
Lee todos los PDF de la carpeta indicada, extrae la primera dirección de email,
envía cada PDF como adjunto al destinatario y registra el resultado en CSV.
"""

import csv
import os
import re
import sys
from datetime import datetime

import pdfplumber

# Por defecto usa la misma carpeta donde está el script
CARPETA_PDF = os.path.dirname(os.path.abspath(__file__))

REGEX_EMAIL = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)

ASUNTO = "Nómina del mes - Tribulex"
CUERPO = "Hola, le adjuntamos su documentación laboral. Saludos."
ARCHIVO_CSV = "registro_envios_tribulex.csv"


def extraer_primer_email(ruta_pdf):
    """Extrae el primer email encontrado en un archivo PDF (orden de aparición)."""
    try:
        with pdfplumber.open(ruta_pdf) as pdf:
            for pagina in pdf.pages:
                texto = pagina.extract_text()
                if texto:
                    match = REGEX_EMAIL.search(texto)
                    if match:
                        return match.group()
    except Exception as e:
        print(f"  ERROR leyendo {os.path.basename(ruta_pdf)}: {e}")
    return None


def registrar_envio(ruta_csv, archivo, email, estado):
    """Añade una fila al CSV de registro de envíos."""
    escribir_cabecera = not os.path.exists(ruta_csv)

    with open(ruta_csv, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        if escribir_cabecera:
            writer.writerow(["Archivo", "Email", "Fecha_Hora", "Estado"])
        writer.writerow([
            archivo,
            email,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            estado,
        ])


def enviar_por_outlook(destinatarios, ruta_csv):
    """Envía un correo con PDF adjunto a cada destinatario usando Outlook."""
    import win32com.client

    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
    except Exception as e:
        print(f"\nERROR: No se pudo conectar con Outlook: {e}")
        return 0, len(destinatarios)

    enviados = 0
    errores = 0

    for email, ruta_pdf, archivo in destinatarios:
        try:
            mail = outlook.CreateItem(0)  # 0 = olMailItem
            mail.To = email
            mail.Subject = ASUNTO
            mail.Body = CUERPO
            mail.Attachments.Add(ruta_pdf)
            mail.Send()
            print(f"  Enviado -> {email}  ({archivo})")
            registrar_envio(ruta_csv, archivo, email, "OK")
            enviados += 1
        except Exception as e:
            print(f"  ERROR enviando a {email}: {e}")
            registrar_envio(ruta_csv, archivo, email, f"ERROR: {e}")
            errores += 1

    return enviados, errores


def main():
    carpeta = sys.argv[1] if len(sys.argv) > 1 else CARPETA_PDF

    if not os.path.isdir(carpeta):
        print(f"La carpeta no existe: {carpeta}")
        sys.exit(1)

    archivos_pdf = sorted(
        f for f in os.listdir(carpeta) if f.lower().endswith(".pdf")
    )

    if not archivos_pdf:
        print(f"No se encontraron archivos PDF en: {carpeta}")
        sys.exit(0)

    print(f"Carpeta: {carpeta}")
    print(f"PDFs encontrados: {len(archivos_pdf)}")
    print("-" * 60)

    sin_email = []
    destinatarios = []  # lista de (email, ruta_absoluta, nombre_archivo)

    for archivo in archivos_pdf:
        ruta = os.path.join(carpeta, archivo)
        ruta_abs = os.path.abspath(ruta)
        email = extraer_primer_email(ruta)

        if email:
            print(f"{archivo}  ->  {email}")
            destinatarios.append((email, ruta_abs, archivo))
        else:
            sin_email.append(archivo)

    if sin_email:
        print("-" * 60)
        print(f"Sin email encontrado ({len(sin_email)}):")
        for archivo in sin_email:
            print(f"  - {archivo}")

    if not destinatarios:
        print("\nNo hay destinatarios a los que enviar.")
        return

    print("-" * 60)
    respuesta = input("¿Deseas enviar los correos ahora? (S/N): ").strip().upper()

    if respuesta == "S":
        ruta_csv = os.path.join(carpeta, ARCHIVO_CSV)
        print(f"\nEnviando {len(destinatarios)} correo(s) via Outlook...")
        print("-" * 60)

        enviados, errores = enviar_por_outlook(destinatarios, ruta_csv)

        print("=" * 60)
        print("RESUMEN DE ENVÍOS")
        print(f"  Total procesados:  {enviados + errores}")
        print(f"  Enviados con éxito: {enviados}")
        print(f"  Con errores:        {errores}")
        print(f"  Registro guardado:  {ruta_csv}")
        print("=" * 60)
    else:
        print("Envío cancelado.")


if __name__ == "__main__":
    main()
