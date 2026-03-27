"""
Tribulex - Base de datos de clientes (SQLite).
Gestiona empresas clientes con sus datos de contacto y preferencias de envio.
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clientes.db")


def _get_conn():
    """Devuelve una conexion a la BD y crea la tabla si no existe."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_empresa  TEXT    NOT NULL UNIQUE,
            email_contacto  TEXT    NOT NULL DEFAULT '',
            telefono        TEXT    NOT NULL DEFAULT '',
            preferencia_envio TEXT  NOT NULL DEFAULT 'Enviar a jefe',
            notas           TEXT    NOT NULL DEFAULT '',
            fecha_creacion  TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
            fecha_modificacion TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.commit()
    return conn


# ── CRUD ──────────────────────────────────────────────────────────────

def listar_clientes():
    """Devuelve todos los clientes como lista de dicts."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM clientes ORDER BY nombre_empresa"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def obtener_cliente(cliente_id):
    """Devuelve un cliente por su ID."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM clientes WHERE id = ?", (cliente_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def buscar_por_empresa(nombre_empresa):
    """
    Busca un cliente cuyo nombre_empresa coincida (parcial, case-insensitive).
    Devuelve el primer match o None.
    """
    conn = _get_conn()
    # Primero intenta coincidencia exacta (case-insensitive)
    row = conn.execute(
        "SELECT * FROM clientes WHERE LOWER(nombre_empresa) = LOWER(?)",
        (nombre_empresa,),
    ).fetchone()
    if not row:
        # Luego busca coincidencia parcial (el nombre de la empresa esta contenido)
        row = conn.execute(
            "SELECT * FROM clientes WHERE LOWER(?) LIKE '%' || LOWER(nombre_empresa) || '%'"
            " OR LOWER(nombre_empresa) LIKE '%' || LOWER(?) || '%'",
            (nombre_empresa, nombre_empresa),
        ).fetchone()
    conn.close()
    return dict(row) if row else None


def crear_cliente(nombre_empresa, email_contacto="", telefono="",
                  preferencia_envio="Enviar a jefe", notas=""):
    """Crea un nuevo cliente. Devuelve el ID creado."""
    conn = _get_conn()
    cur = conn.execute(
        """INSERT INTO clientes (nombre_empresa, email_contacto, telefono,
           preferencia_envio, notas)
           VALUES (?, ?, ?, ?, ?)""",
        (nombre_empresa.strip(), email_contacto.strip(), telefono.strip(),
         preferencia_envio.strip(), notas.strip()),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def actualizar_cliente(cliente_id, nombre_empresa, email_contacto, telefono,
                       preferencia_envio, notas):
    """Actualiza un cliente existente."""
    conn = _get_conn()
    conn.execute(
        """UPDATE clientes
           SET nombre_empresa = ?, email_contacto = ?, telefono = ?,
               preferencia_envio = ?, notas = ?,
               fecha_modificacion = datetime('now','localtime')
           WHERE id = ?""",
        (nombre_empresa.strip(), email_contacto.strip(), telefono.strip(),
         preferencia_envio.strip(), notas.strip(), cliente_id),
    )
    conn.commit()
    conn.close()


def eliminar_cliente(cliente_id):
    """Elimina un cliente por su ID."""
    conn = _get_conn()
    conn.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))
    conn.commit()
    conn.close()
