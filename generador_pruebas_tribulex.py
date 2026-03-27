"""
Tribulex - Generador de PDF de prueba con 20 nóminas ficticias.
Cada página simula la nómina de un empleado distinto.
Ejecutar:  python generador_pruebas_tribulex.py
"""

import os
import random
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

# ── Datos ficticios ────────────────────────────────────────────────────

EMPRESAS = [
    {"nombre": "Talleres Paco SL", "cif": "B-12345678", "dir": "C/ Industria 12, Sevilla"},
    {"nombre": "Consultoría Beta", "cif": "B-87654321", "dir": "Av. de la Innovación 5, Madrid"},
    {"nombre": "Restaurante El Puerto", "cif": "B-11223344", "dir": "Paseo Marítimo 3, Cádiz"},
]

NOMBRES = [
    "María García López", "Carlos Ruiz Fernández", "Ana Martínez Díaz",
    "Pedro Sánchez Romero", "Laura Hernández Gil", "David López Navarro",
    "Elena Torres Moreno", "Javier Ramírez Ortega", "Sofía Díaz Castillo",
    "Miguel Álvarez Serrano", "Carmen Molina Reyes", "Alejandro Vega Prieto",
    "Lucía Fernández Ruiz", "Pablo Jiménez Santos", "Marta Domínguez León",
    "Sergio Castro Ibáñez", "Raquel Herrera Blanco", "Andrés Morales Peña",
    "Isabel Delgado Vargas", "Fernando Ortiz Medina",
]

EMAILS = [
    "maria.garcia@email.com", "carlos.ruiz@email.com", "ana.martinez@email.com",
    "pedro.sanchez@email.com", "laura.hernandez@email.com", "david.lopez@email.com",
    "elena.torres@email.com", "javier.ramirez@email.com", "sofia.diaz@email.com",
    "miguel.alvarez@email.com", "carmen.molina@email.com", "alejandro.vega@email.com",
    "lucia.fernandez@email.com", "pablo.jimenez@email.com", "marta.dominguez@email.com",
    "sergio.castro@email.com", "raquel.herrera@email.com", "andres.morales@email.com",
    "isabel.delgado@email.com", "fernando.ortiz@email.com",
]

CATEGORIAS = [
    "Oficial 1ª", "Oficial 2ª", "Peón", "Administrativo",
    "Técnico", "Encargado", "Auxiliar", "Jefe de equipo",
]

random.seed(42)  # reproducible


def generar_dni():
    numero = random.randint(10000000, 99999999)
    letras = "TRWAGMYFPDXBNJZSQVHLCKE"
    return f"{numero}{letras[numero % 23]}"


# ── Colores ────────────────────────────────────────────────────────────
AZUL_OSCURO = HexColor("#1e3a5f")
AZUL_MEDIO  = HexColor("#2d5986")
GRIS_CLARO  = HexColor("#f0f2f5")
GRIS_LINEA  = HexColor("#cccccc")
NEGRO       = HexColor("#222222")
BLANCO      = HexColor("#ffffff")


def dibujar_nomina(c, empresa, nombre, email, page_num):
    """Dibuja una página de nómina profesional."""
    w, h = A4
    dni = generar_dni()
    codigo = f"EMP-{page_num:04d}"
    categoria = random.choice(CATEGORIAS)
    antiguedad = random.randint(0, 20)

    # Importes
    salario_base = round(random.uniform(1200, 3500), 2)
    plus_convenio = round(salario_base * random.uniform(0.05, 0.15), 2)
    plus_transporte = round(random.uniform(50, 120), 2)
    horas_extra = round(random.uniform(0, 300), 2)
    bruto = round(salario_base + plus_convenio + plus_transporte + horas_extra, 2)

    pct_irpf = round(random.uniform(8, 24), 2)
    irpf = round(bruto * pct_irpf / 100, 2)
    ss_trabajador = round(bruto * 0.0635, 2)
    desempleo = round(bruto * 0.0155, 2)
    formacion = round(bruto * 0.001, 2)
    total_deducciones = round(irpf + ss_trabajador + desempleo + formacion, 2)
    liquido = round(bruto - total_deducciones, 2)

    y = h - 20 * mm

    # ── Cabecera empresa ───────────────────────────────────────────────
    c.setFillColor(AZUL_OSCURO)
    c.rect(15 * mm, y - 18 * mm, w - 30 * mm, 22 * mm, fill=True, stroke=False)
    c.setFillColor(BLANCO)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(22 * mm, y - 4 * mm, empresa["nombre"])
    c.setFont("Helvetica", 9)
    c.drawString(22 * mm, y - 11 * mm, f"CIF: {empresa['cif']}   |   {empresa['dir']}")
    c.drawRightString(w - 22 * mm, y - 4 * mm, "RECIBO DE SALARIOS")
    c.drawRightString(w - 22 * mm, y - 11 * mm, "Período: Febrero 2026")

    y -= 28 * mm

    # ── Datos del trabajador ───────────────────────────────────────────
    c.setFillColor(GRIS_CLARO)
    c.rect(15 * mm, y - 28 * mm, w - 30 * mm, 30 * mm, fill=True, stroke=False)
    c.setStrokeColor(GRIS_LINEA)
    c.rect(15 * mm, y - 28 * mm, w - 30 * mm, 30 * mm, fill=False, stroke=True)

    c.setFillColor(AZUL_OSCURO)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(20 * mm, y - 2 * mm, "DATOS DEL TRABAJADOR")

    c.setFillColor(NEGRO)
    c.setFont("Helvetica", 9)
    labels_left = [
        ("Nombre:", nombre),
        ("DNI:", dni),
        ("Email:", email),
    ]
    labels_right = [
        ("Código empleado:", codigo),
        ("Categoría:", categoria),
        ("Antigüedad:", f"{antiguedad} años"),
    ]
    for i, (lbl, val) in enumerate(labels_left):
        yy = y - 10 * mm - i * 6 * mm
        c.setFont("Helvetica-Bold", 9)
        c.drawString(20 * mm, yy, lbl)
        c.setFont("Helvetica", 9)
        c.drawString(48 * mm, yy, val)

    for i, (lbl, val) in enumerate(labels_right):
        yy = y - 10 * mm - i * 6 * mm
        c.setFont("Helvetica-Bold", 9)
        c.drawString(115 * mm, yy, lbl)
        c.setFont("Helvetica", 9)
        c.drawString(152 * mm, yy, val)

    y -= 36 * mm

    # ── Tabla de devengos ──────────────────────────────────────────────
    def tabla_header(y_pos, titulo):
        c.setFillColor(AZUL_MEDIO)
        c.rect(15 * mm, y_pos - 7 * mm, w - 30 * mm, 8 * mm, fill=True, stroke=False)
        c.setFillColor(BLANCO)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(20 * mm, y_pos - 4.5 * mm, titulo)
        c.drawRightString(w - 22 * mm, y_pos - 4.5 * mm, "Importe (€)")
        return y_pos - 8 * mm

    def fila(y_pos, concepto, importe, bold=False):
        c.setStrokeColor(GRIS_LINEA)
        c.line(15 * mm, y_pos - 6 * mm, w - 15 * mm, y_pos - 6 * mm)
        c.setFillColor(NEGRO)
        font = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font, 9)
        c.drawString(20 * mm, y_pos - 4 * mm, concepto)
        c.drawRightString(w - 22 * mm, y_pos - 4 * mm, f"{importe:,.2f} €")
        return y_pos - 6.5 * mm

    y = tabla_header(y, "DEVENGOS")
    y = fila(y, "Salario base", salario_base)
    y = fila(y, "Plus convenio", plus_convenio)
    y = fila(y, "Plus transporte", plus_transporte)
    y = fila(y, "Horas extraordinarias", horas_extra)
    y = fila(y, "TOTAL DEVENGADO", bruto, bold=True)

    y -= 6 * mm

    # ── Tabla de deducciones ───────────────────────────────────────────
    y = tabla_header(y, "DEDUCCIONES")
    y = fila(y, f"IRPF ({pct_irpf}%)", irpf)
    y = fila(y, "Contingencias comunes (6,35%)", ss_trabajador)
    y = fila(y, "Desempleo (1,55%)", desempleo)
    y = fila(y, "Formación profesional (0,10%)", formacion)
    y = fila(y, "TOTAL DEDUCCIONES", total_deducciones, bold=True)

    y -= 10 * mm

    # ── Líquido a percibir ─────────────────────────────────────────────
    c.setFillColor(AZUL_OSCURO)
    c.rect(15 * mm, y - 12 * mm, w - 30 * mm, 14 * mm, fill=True, stroke=False)
    c.setFillColor(BLANCO)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(20 * mm, y - 7 * mm, "LÍQUIDO A PERCIBIR")
    c.drawRightString(w - 22 * mm, y - 7 * mm, f"{liquido:,.2f} €")

    # ── Pie de página ──────────────────────────────────────────────────
    c.setFillColor(GRIS_LINEA)
    c.setFont("Helvetica", 7)
    c.drawCentredString(w / 2, 12 * mm, f"Documento generado para pruebas — {empresa['nombre']} — Página {page_num}/20")


def main():
    carpeta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "NÓMINAS")
    os.makedirs(carpeta, exist_ok=True)
    ruta_salida = os.path.join(carpeta, "nominas_prueba_20.pdf")

    c_pdf = canvas.Canvas(ruta_salida, pagesize=A4)
    c_pdf.setTitle("Nóminas de prueba - Tribulex")

    for i in range(20):
        empresa = EMPRESAS[i % len(EMPRESAS)]
        dibujar_nomina(c_pdf, empresa, NOMBRES[i], EMAILS[i], i + 1)
        if i < 19:
            c_pdf.showPage()

    c_pdf.save()
    print(f"PDF generado con 20 nóminas en:\n  {ruta_salida}")


if __name__ == "__main__":
    main()
