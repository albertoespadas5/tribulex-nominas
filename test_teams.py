"""
Tribulex - Test de conexión a SharePoint.
Verifica credenciales y lista los PDFs en la carpeta de entrada.

Ejecutar:  python test_teams.py
"""

import os
import sys
from dotenv import load_dotenv

# Cargar .env del mismo directorio
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

SP_EMAIL = os.getenv("SP_EMAIL", "")
SP_PASSWORD = os.getenv("SP_PASSWORD", "")
SP_SITE_URL = os.getenv("SP_SITE_URL", "")
SP_CARPETA_ENTRADA = os.getenv("SP_CARPETA_ENTRADA", "")


def main():
    # ── Verificar variables ───────────────────────────────────────────
    print("=" * 60)
    print("  TRIBULEX - Test de conexión a SharePoint")
    print("=" * 60)

    errores = []
    if not SP_EMAIL or SP_EMAIL == "tu_email@tribulex.es":
        errores.append("SP_EMAIL no configurado en .env")
    if not SP_PASSWORD or SP_PASSWORD == "tu_contraseña_aqui":
        errores.append("SP_PASSWORD no configurado en .env")
    if not SP_SITE_URL:
        errores.append("SP_SITE_URL no configurado en .env")
    if not SP_CARPETA_ENTRADA:
        errores.append("SP_CARPETA_ENTRADA no configurado en .env")

    print(f"\n  Email:    {SP_EMAIL}")
    print(f"  Sitio:    {SP_SITE_URL}")
    print(f"  Carpeta:  {SP_CARPETA_ENTRADA}")

    if errores:
        print(f"\n  ERRORES en .env:")
        for e in errores:
            print(f"    - {e}")
        print("\n  Edita el archivo .env con tus datos reales y vuelve a ejecutar.")
        sys.exit(1)

    # ── Conectar ──────────────────────────────────────────────────────
    print("\n  Conectando a SharePoint...")

    from office365.runtime.auth.user_credential import UserCredential
    from office365.sharepoint.client_context import ClientContext

    try:
        credentials = UserCredential(SP_EMAIL, SP_PASSWORD)
        ctx = ClientContext(SP_SITE_URL).with_credentials(credentials)
        web = ctx.web.get().execute_query()
        print(f"  CONECTADO al sitio: {web.properties['Title']}")
    except Exception as e:
        print(f"\n  ERROR DE CONEXIÓN: {e}")
        print("\n  Posibles causas:")
        print("    - Email o contraseña incorrectos")
        print("    - La URL del sitio no es válida")
        print("    - Tu cuenta requiere autenticación multifactor (MFA)")
        print("    - La cuenta no tiene permisos en este sitio")
        sys.exit(1)

    # ── Listar archivos ───────────────────────────────────────────────
    print(f"\n  Listando archivos en: {SP_CARPETA_ENTRADA}")
    print("-" * 60)

    try:
        folder = ctx.web.get_folder_by_server_relative_url(SP_CARPETA_ENTRADA)
        files = folder.files.get().execute_query()

        if not files:
            print("  (carpeta vacía o no encontrada)")
        else:
            pdfs = []
            for f in files:
                nombre = f.properties["Name"]
                size = int(f.properties.get("Length", 0))
                size_str = f"{size/1024:.0f} KB" if size < 1048576 else f"{size/1048576:.1f} MB"
                es_pdf = nombre.lower().endswith(".pdf")
                marca = " [PDF]" if es_pdf else ""
                print(f"    {nombre}  ({size_str}){marca}")
                if es_pdf:
                    pdfs.append(nombre)

            print("-" * 60)
            print(f"  Total archivos: {len(files)}")
            print(f"  PDFs encontrados: {len(pdfs)}")

            if pdfs:
                print(f"\n  El robot puede procesar:")
                for p in pdfs:
                    print(f"    -> {p}")
            else:
                print("\n  No hay PDFs en la carpeta. Sube un PDF para procesarlo.")

    except Exception as e:
        print(f"\n  ERROR al listar carpeta: {e}")
        print("  Verifica que la ruta SP_CARPETA_ENTRADA es correcta.")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  Test completado con éxito")
    print("=" * 60)


if __name__ == "__main__":
    main()
