"""
Tribulex - Procesamiento nube-a-nube vía SharePoint.
Descarga el PDF de SharePoint, procesa todo en memoria/tmp, y sube los ZIPs
de vuelta a SharePoint sin dejar archivos permanentes en disco.
"""

import csv
import io
import os
import re
import tempfile
import zipfile

import pdfplumber
from dotenv import load_dotenv
from office365.runtime.auth.user_credential import UserCredential
from office365.sharepoint.client_context import ClientContext
from PyPDF2 import PdfReader, PdfWriter

from procesador_inteligente_tribulex import (
    NOMBRE_CORTO,
    extraer_datos_pagina,
)

# ── Cargar variables de entorno ────────────────────────────────────────
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

SP_EMAIL = os.getenv("SP_EMAIL", "")
SP_PASSWORD = os.getenv("SP_PASSWORD", "")
SP_SITE_URL = os.getenv("SP_SITE_URL", "")
SP_CARPETA_ENTRADA = os.getenv("SP_CARPETA_ENTRADA", "")
SP_CARPETA_SALIDA = os.getenv("SP_CARPETA_SALIDA", "")


# ── Conexión a SharePoint ──────────────────────────────────────────────

def conectar_sharepoint():
    """Devuelve un ClientContext autenticado contra el sitio de SharePoint."""
    credentials = UserCredential(SP_EMAIL, SP_PASSWORD)
    ctx = ClientContext(SP_SITE_URL).with_credentials(credentials)
    # Verificar conexión cargando info del sitio
    web = ctx.web.get().execute_query()
    return ctx, web.properties["Title"]


def listar_archivos(ctx, carpeta_sp):
    """Lista los archivos de una carpeta de SharePoint."""
    folder = ctx.web.get_folder_by_server_relative_url(carpeta_sp)
    files = folder.files.get().execute_query()
    return [(f.properties["Name"], f.properties["Length"]) for f in files]


def descargar_archivo(ctx, carpeta_sp, nombre_archivo):
    """Descarga un archivo de SharePoint a memoria (bytes)."""
    ruta = f"{carpeta_sp}/{nombre_archivo}"
    response = (
        ctx.web.get_file_by_server_relative_url(ruta)
        .download(io.BytesIO())
        .execute_query()
    )
    buf = response.value
    buf.seek(0)
    return buf.read()


def subir_archivo(ctx, carpeta_sp, nombre_archivo, contenido_bytes):
    """Sube un archivo (bytes) a una carpeta de SharePoint."""
    folder = ctx.web.get_folder_by_server_relative_url(carpeta_sp)
    folder.upload_file(nombre_archivo, contenido_bytes).execute_query()


def asegurar_carpeta(ctx, carpeta_sp):
    """Crea la carpeta en SharePoint si no existe."""
    ctx.web.ensure_folder_path(carpeta_sp).execute_query()


# ── Procesamiento nube-a-nube (todo en RAM) ────────────────────────────

def _pagina_a_bytes(reader, num_pagina):
    """Extrae una página de un PdfReader y la devuelve como bytes."""
    writer = PdfWriter()
    writer.add_page(reader.pages[num_pagina])
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def procesar_nube_a_nube(ctx, carpeta_entrada, carpeta_salida, nombre_pdf, mes="Marzo"):
    """
    Flujo completo nube-a-nube:
      1. Descarga el PDF de SharePoint a RAM.
      2. Extrae datos de cada página (empresa, nombre, código, bruto, líquido).
      3. Separa cada página en un PDF en memoria.
      4. Agrupa por empresa y genera ZIPs en memoria.
      5. Genera CSVs en memoria.
      6. Sube ZIPs y CSVs a la carpeta de salida en SharePoint.

    No toca disco en ningún momento.
    Devuelve (registros, archivos_subidos).
    """

    # ── 1. Descargar PDF a RAM ────────────────────────────────────────
    pdf_bytes = descargar_archivo(ctx, carpeta_entrada, nombre_pdf)

    # ── 2. Leer páginas y extraer datos ───────────────────────────────
    registros = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for i, pagina in enumerate(pdf.pages):
            texto = pagina.extract_text() or ""
            datos = extraer_datos_pagina(texto)
            datos["pagina"] = i
            registros.append(datos)

    # ── 3. Separar cada página en bytes ───────────────────────────────
    reader = PdfReader(io.BytesIO(pdf_bytes))
    for reg in registros:
        nombre_limpio = re.sub(r"[^\w\s\-]", "", reg["nombre"]).strip().replace(" ", "_")
        reg["nombre_pdf"] = f"{reg['codigo']}_{nombre_limpio}.pdf"
        reg["pdf_bytes"] = _pagina_a_bytes(reader, reg["pagina"])

    # ── 4. Generar ZIPs en memoria por empresa ────────────────────────
    empresas = sorted({r["empresa"] for r in registros})
    archivos_subidos = []

    asegurar_carpeta(ctx, carpeta_salida)

    for empresa in empresas:
        empresa_corta = NOMBRE_CORTO.get(empresa, empresa.replace(" ", "_"))
        nominas_emp = [r for r in registros if r["empresa"] == empresa]

        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for r in nominas_emp:
                zf.writestr(r["nombre_pdf"], r["pdf_bytes"])

        nombre_zip = f"Nominas_{empresa_corta}_{mes}.zip"
        zip_bytes = zip_buf.getvalue()

        subir_archivo(ctx, carpeta_salida, nombre_zip, zip_bytes)
        archivos_subidos.append({
            "nombre": nombre_zip,
            "empresa": empresa,
            "nominas": len(nominas_emp),
            "size_kb": len(zip_bytes) / 1024,
        })

    # ── 5. Generar CSVs en memoria y subir ────────────────────────────

    # 5a. Detalle por trabajador
    det_buf = io.StringIO()
    det_writer = csv.writer(det_buf, delimiter=";")
    det_writer.writerow(["Empresa", "Codigo", "Trabajador", "Email", "Sueldo_Bruto", "Sueldo_Liquido"])
    for r in sorted(registros, key=lambda x: (x["empresa"], x["codigo"])):
        det_writer.writerow([
            r["empresa"], r["codigo"], r["nombre"],
            r["email"] or "", f"{r['bruto']:.2f}", f"{r['liquido']:.2f}",
        ])
    det_bytes = det_buf.getvalue().encode("utf-8")
    nombre_det = f"Detalle_Trabajadores_{mes}.csv"
    subir_archivo(ctx, carpeta_salida, nombre_det, det_bytes)
    archivos_subidos.append({"nombre": nombre_det, "empresa": "—", "nominas": len(registros), "size_kb": len(det_bytes) / 1024})

    # 5b. Resumen por empresa
    res_buf = io.StringIO()
    res_writer = csv.writer(res_buf, delimiter=";")
    res_writer.writerow(["Empresa", "Num_Nominas", "Total_Bruto", "Total_Liquido"])
    gran_bruto = gran_liquido = 0
    for empresa in empresas:
        nominas_emp = [r for r in registros if r["empresa"] == empresa]
        t_bruto = sum(r["bruto"] for r in nominas_emp)
        t_liquido = sum(r["liquido"] for r in nominas_emp)
        gran_bruto += t_bruto
        gran_liquido += t_liquido
        res_writer.writerow([empresa, len(nominas_emp), f"{t_bruto:.2f}", f"{t_liquido:.2f}"])
    res_writer.writerow(["TOTAL GENERAL", len(registros), f"{gran_bruto:.2f}", f"{gran_liquido:.2f}"])
    res_bytes = res_buf.getvalue().encode("utf-8")
    nombre_res = f"Resumen_Empresas_{mes}.csv"
    subir_archivo(ctx, carpeta_salida, nombre_res, res_bytes)
    archivos_subidos.append({"nombre": nombre_res, "empresa": "—", "nominas": len(registros), "size_kb": len(res_bytes) / 1024})

    # Limpiar bytes pesados de los registros antes de devolver
    for r in registros:
        r.pop("pdf_bytes", None)

    return registros, archivos_subidos


# ── Ejecución directa ─────────────────────────────────────────────────
if __name__ == "__main__":
    print("Conectando a SharePoint...")
    ctx, titulo = conectar_sharepoint()
    print(f"Conectado al sitio: {titulo}\n")

    print(f"Carpeta entrada: {SP_CARPETA_ENTRADA}")
    archivos = listar_archivos(ctx, SP_CARPETA_ENTRADA)
    pdfs = [a for a in archivos if a[0].lower().endswith(".pdf")]

    if not pdfs:
        print("No se encontraron PDFs en la carpeta de entrada.")
    else:
        nombre_pdf = pdfs[0][0]
        print(f"Procesando: {nombre_pdf}")

        registros, subidos = procesar_nube_a_nube(
            ctx, SP_CARPETA_ENTRADA, SP_CARPETA_SALIDA, nombre_pdf,
        )

        print(f"\nNóminas procesadas: {len(registros)}")
        print(f"Archivos subidos a SharePoint:")
        for s in subidos:
            print(f"  - {s['nombre']}  ({s['size_kb']:.0f} KB)")
