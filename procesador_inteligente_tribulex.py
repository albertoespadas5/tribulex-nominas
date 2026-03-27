"""
Tribulex - Procesador inteligente de PDF de nóminas.
Split → Identificación → Organización por empresa → ZIPs → Informe CSV.

Soporta dos modos:
  - En memoria (para Streamlit Cloud): procesar_pdf_en_memoria(bytes, mes)
  - En disco  (para uso local / CLI):  procesar_pdf_gigante(ruta, carpeta, mes)
"""

import csv
import io
import os
import re
import tempfile
import zipfile

import pdfplumber
from PyPDF2 import PdfReader, PdfWriter

# Regex para extraer datos de cada página
RE_EMPRESA = re.compile(
    r"(Talleres Paco SL|Consultoría Beta|Restaurante El Puerto)", re.IGNORECASE
)
RE_NOMBRE = re.compile(r"Nombre:\s*(.+?)(?:\s{2,}|Código)", re.IGNORECASE)
RE_CODIGO = re.compile(r"Código empleado:\s*(EMP-\d+)", re.IGNORECASE)
RE_BRUTO = re.compile(r"TOTAL DEVENGADO\s+([\d.,]+)\s*€", re.IGNORECASE)
RE_LIQUIDO = re.compile(r"LÍQUIDO A PERCIBIR\s+([\d.,]+)\s*€", re.IGNORECASE)
RE_EMAIL = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

# Mapeo de nombre de empresa a nombre corto para archivos
NOMBRE_CORTO = {
    "Talleres Paco SL": "TalleresPaco",
    "Consultoría Beta": "ConsultoriaBeta",
    "Restaurante El Puerto": "RestauranteElPuerto",
}


def _parse_importe(texto):
    """Convierte '1,234.56' o '1.234,56' a float."""
    if not texto:
        return 0.0
    texto = texto.replace(",", "")
    try:
        return float(texto)
    except ValueError:
        return 0.0


def extraer_datos_pagina(texto):
    """Extrae empresa, nombre, código, bruto, líquido y email de una página."""
    empresa = m.group(1) if (m := RE_EMPRESA.search(texto)) else "Desconocida"
    nombre = m.group(1).strip() if (m := RE_NOMBRE.search(texto)) else "Sin_Nombre"
    codigo = m.group(1) if (m := RE_CODIGO.search(texto)) else "SIN-COD"
    bruto = _parse_importe(m.group(1)) if (m := RE_BRUTO.search(texto)) else 0.0
    liquido = _parse_importe(m.group(1)) if (m := RE_LIQUIDO.search(texto)) else 0.0
    email = m.group() if (m := RE_EMAIL.search(texto)) else None
    return {
        "empresa": empresa,
        "nombre": nombre,
        "codigo": codigo,
        "bruto": bruto,
        "liquido": liquido,
        "email": email,
    }


def _extraer_pagina_como_bytes(reader, num_pagina):
    """Extrae una página de un PdfReader y devuelve sus bytes."""
    writer = PdfWriter()
    writer.add_page(reader.pages[num_pagina])
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _generar_csv_resumen(registros, empresas, mes):
    """Genera el CSV de resumen por empresa como bytes UTF-8."""
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";")
    writer.writerow(["Empresa", "Num_Nominas", "Total_Bruto", "Total_Liquido"])
    gran_bruto = 0
    gran_liquido = 0
    for empresa in empresas:
        nominas_emp = [r for r in registros if r["empresa"] == empresa]
        total_bruto = sum(r["bruto"] for r in nominas_emp)
        total_liquido = sum(r["liquido"] for r in nominas_emp)
        gran_bruto += total_bruto
        gran_liquido += total_liquido
        writer.writerow([empresa, len(nominas_emp), f"{total_bruto:.2f}", f"{total_liquido:.2f}"])
    writer.writerow(["TOTAL GENERAL", len(registros), f"{gran_bruto:.2f}", f"{gran_liquido:.2f}"])
    return buf.getvalue().encode("utf-8")


def _generar_csv_detalle(registros, mes):
    """Genera el CSV de detalle por trabajador como bytes UTF-8."""
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";")
    writer.writerow(["Empresa", "Codigo", "Trabajador", "Email", "Sueldo_Bruto", "Sueldo_Liquido"])
    for r in sorted(registros, key=lambda x: (x["empresa"], x["codigo"])):
        writer.writerow([
            r["empresa"], r["codigo"], r["nombre"],
            r["email"] or "", f"{r['bruto']:.2f}", f"{r['liquido']:.2f}",
        ])
    return buf.getvalue().encode("utf-8")


# ═══════════════════════════════════════════════════════════════════════
#  MODO MEMORIA — para Streamlit Cloud
# ═══════════════════════════════════════════════════════════════════════

def procesar_pdf_en_memoria(pdf_bytes, mes="Marzo"):
    """
    Procesa un PDF multi-página de nóminas enteramente en RAM.

    Args:
        pdf_bytes: bytes del archivo PDF subido.
        mes: nombre del mes para los nombres de archivo.

    Returns:
        (registros, zips_dict, csv_resumen_bytes, csv_detalle_bytes)
        - registros: lista de dicts con los datos de cada nómina.
        - zips_dict: dict {nombre_zip: bytes_zip} por empresa.
        - csv_resumen_bytes: bytes del CSV resumen por empresa.
        - csv_detalle_bytes: bytes del CSV detalle por trabajador.
    """
    pdf_stream = io.BytesIO(pdf_bytes)

    # ── Paso 1: leer páginas y extraer datos ─────────────────────────
    registros = []
    with pdfplumber.open(pdf_stream) as pdf:
        total_paginas = len(pdf.pages)
        for i, pagina in enumerate(pdf.pages):
            texto = pagina.extract_text() or ""
            datos = extraer_datos_pagina(texto)
            datos["pagina"] = i
            datos["total_paginas"] = total_paginas
            registros.append(datos)

    # ── Paso 2: extraer cada página como PDF individual (en memoria) ─
    pdf_stream.seek(0)
    reader = PdfReader(pdf_stream)
    paginas_pdf = {}  # pagina_idx → bytes del PDF de 1 página
    for reg in registros:
        paginas_pdf[reg["pagina"]] = _extraer_pagina_como_bytes(reader, reg["pagina"])

    # ── Paso 3: agrupar por empresa y crear ZIPs en memoria ─────────
    empresas_encontradas = sorted({r["empresa"] for r in registros})
    zips_dict = {}

    for empresa in empresas_encontradas:
        empresa_corta = NOMBRE_CORTO.get(empresa, empresa.replace(" ", "_"))
        nombre_zip = f"Nominas_{empresa_corta}_{mes}.zip"

        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for reg in registros:
                if reg["empresa"] != empresa:
                    continue
                nombre_limpio = re.sub(r"[^\w\s\-]", "", reg["nombre"]).strip().replace(" ", "_")
                nombre_pdf = f"{reg['codigo']}_{nombre_limpio}.pdf"
                zf.writestr(nombre_pdf, paginas_pdf[reg["pagina"]])

        zips_dict[nombre_zip] = zip_buf.getvalue()

    # ── Paso 4: generar CSVs en memoria ──────────────────────────────
    csv_resumen = _generar_csv_resumen(registros, empresas_encontradas, mes)
    csv_detalle = _generar_csv_detalle(registros, mes)

    return registros, zips_dict, csv_resumen, csv_detalle


# ═══════════════════════════════════════════════════════════════════════
#  MODO DISCO — para uso local / CLI  (compatibilidad)
# ═══════════════════════════════════════════════════════════════════════

def separar_pagina_a_pdf(pdf_origen, num_pagina, ruta_destino):
    """Extrae una página del PDF original y la guarda como PDF independiente."""
    reader = PdfReader(pdf_origen)
    writer = PdfWriter()
    writer.add_page(reader.pages[num_pagina])
    with open(ruta_destino, "wb") as f:
        writer.write(f)


def procesar_pdf_gigante(ruta_pdf, carpeta_salida, mes="Marzo"):
    """
    Procesa un PDF multi-página de nóminas (modo disco).
    Devuelve (registros, zips, ruta_csv, ruta_detalle).
    """
    os.makedirs(carpeta_salida, exist_ok=True)

    registros = []
    with pdfplumber.open(ruta_pdf) as pdf:
        total_paginas = len(pdf.pages)
        for i, pagina in enumerate(pdf.pages):
            texto = pagina.extract_text() or ""
            datos = extraer_datos_pagina(texto)
            datos["pagina"] = i
            datos["total_paginas"] = total_paginas
            registros.append(datos)

    empresas_encontradas = sorted({r["empresa"] for r in registros})
    zips_generados = []

    with tempfile.TemporaryDirectory(prefix="tribulex_") as tmp_dir:
        for reg in registros:
            empresa_corta = NOMBRE_CORTO.get(reg["empresa"], reg["empresa"].replace(" ", "_"))
            carpeta_empresa = os.path.join(tmp_dir, empresa_corta)
            os.makedirs(carpeta_empresa, exist_ok=True)

            nombre_limpio = re.sub(r"[^\w\s\-]", "", reg["nombre"]).strip().replace(" ", "_")
            nombre_pdf = f"{reg['codigo']}_{nombre_limpio}.pdf"
            ruta_destino = os.path.join(carpeta_empresa, nombre_pdf)

            separar_pagina_a_pdf(ruta_pdf, reg["pagina"], ruta_destino)
            reg["ruta_pdf"] = ruta_destino

        for empresa in empresas_encontradas:
            empresa_corta = NOMBRE_CORTO.get(empresa, empresa.replace(" ", "_"))
            carpeta_empresa = os.path.join(tmp_dir, empresa_corta)
            nombre_zip = f"Nominas_{empresa_corta}_{mes}.zip"
            ruta_zip = os.path.join(carpeta_salida, nombre_zip)

            with zipfile.ZipFile(ruta_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                for archivo in sorted(os.listdir(carpeta_empresa)):
                    ruta_archivo = os.path.join(carpeta_empresa, archivo)
                    zf.write(ruta_archivo, arcname=archivo)

            zips_generados.append({
                "empresa": empresa,
                "zip": nombre_zip,
                "ruta": ruta_zip,
                "nominas": sum(1 for r in registros if r["empresa"] == empresa),
            })

    ruta_detalle = os.path.join(carpeta_salida, f"Detalle_Trabajadores_{mes}.csv")
    with open(ruta_detalle, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["Empresa", "Codigo", "Trabajador", "Email", "Sueldo_Bruto", "Sueldo_Liquido"])
        for r in sorted(registros, key=lambda x: (x["empresa"], x["codigo"])):
            writer.writerow([
                r["empresa"], r["codigo"], r["nombre"],
                r["email"] or "", f"{r['bruto']:.2f}", f"{r['liquido']:.2f}",
            ])

    ruta_csv = os.path.join(carpeta_salida, f"Resumen_Empresas_{mes}.csv")
    with open(ruta_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["Empresa", "Num_Nominas", "Total_Bruto", "Total_Liquido"])
        gran_bruto = 0
        gran_liquido = 0
        for empresa in empresas_encontradas:
            nominas_emp = [r for r in registros if r["empresa"] == empresa]
            total_bruto = sum(r["bruto"] for r in nominas_emp)
            total_liquido = sum(r["liquido"] for r in nominas_emp)
            gran_bruto += total_bruto
            gran_liquido += total_liquido
            writer.writerow([empresa, len(nominas_emp), f"{total_bruto:.2f}", f"{total_liquido:.2f}"])
        writer.writerow(["TOTAL GENERAL", len(registros), f"{gran_bruto:.2f}", f"{gran_liquido:.2f}"])

    return registros, zips_generados, ruta_csv, ruta_detalle


# ── Ejecución directa por consola ─────────────────────────────────────
if __name__ == "__main__":
    import sys

    base = os.path.dirname(os.path.abspath(__file__))
    pdf = sys.argv[1] if len(sys.argv) > 1 else os.path.join(base, "NÓMINAS", "nominas_prueba_20.pdf")
    salida = os.path.join(base, "NÓMINAS", "Procesado")

    if not os.path.isfile(pdf):
        print(f"No se encontró el PDF: {pdf}")
        sys.exit(1)

    print(f"Procesando: {pdf}")
    registros, zips, csv_path, detalle_path = procesar_pdf_gigante(pdf, salida)

    print(f"\nNóminas procesadas: {len(registros)}")
    print(f"ZIPs generados:     {len(zips)}")
    for z in zips:
        print(f"  - {z['zip']}  ({z['nominas']} nóminas)")
    print(f"Detalle CSV:        {detalle_path}")
    print(f"Resumen CSV:        {csv_path}")
