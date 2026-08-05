import sqlite3
import os
import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "ofisolve.db")
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "uploads", "clientes")

def main():
    if not os.path.exists(DB_PATH):
        print("Base de datos no encontrada:", DB_PATH)
        return

    # Ensure upload directories exist
    os.makedirs(UPLOADS_DIR, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Obtener workspace (asumiremos el ID 1)
    cursor.execute("SELECT id FROM workspaces LIMIT 1")
    ws_row = cursor.fetchone()
    if not ws_row:
        print("No hay workspace creado.")
        return
    workspace_id = ws_row[0]

    # 2. Insertar Cliente "Tomas Andal"
    cursor.execute(
        """
        INSERT INTO clientes (
            workspace_id, nombre_completo, sexo, tipo_persona, nacionalidad, 
            tipo_documento, dni, estado_familia, cuit, domicilio_calle,
            fecha_creacion, es_pep, riesgo_uif, uif_estado,
            exhibio_documento_idoneo, inscripto_ganancias, union_convivencial,
            domicilio_fiscal_diferente
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """,
        (
            workspace_id, "Tomas Andal", "Masculino", "Fisica", "Argentino",
            "DNI", "29123456", "Soltero", "20-29123456-1", "Av. del Libertador 1234, CABA",
            datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            0, "Bajo", "Aprobado",
            1, 0, 0, 0
        )
    )
    cliente_id = cursor.lastrowid
    print(f"Creado Cliente Tomas Andal (ID: {cliente_id})")

    # Helper function para crear tramite
    def crear_tramite(nombre, tipo):
        cursor.execute(
            """
            INSERT INTO tramites (
                workspace_id, cliente_id, nombre, tipo, estado, fecha_creacion, fecha_actualizacion
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                workspace_id, cliente_id, nombre, tipo, "abierto",
                datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            )
        )
        return cursor.lastrowid

    # 3. Insertar Carpetas y Documentos Reales
    carpetas = [
        ("Sucesión Andal", "sucesion"),
        ("Poder General Amplio", "poder"),
        ("Escritura Compraventa", "compraventa")
    ]

    docs_info = {
        "Sucesión Andal": [
            ("Declaratoria_Herederos.txt", "pdf", "JUZGADO NACIONAL DE PRIMERA INSTANCIA EN LO CIVIL NRO 15...\n\nAUTOS Y VISTOS: Y CONSIDERANDO:\nQue de las constancias de autos surge acreditado el fallecimiento de Juan Carlos Andal, ocurrido el 15 de marzo de 2023. Que el causante se encontraba casado en primeras nupcias con Maria Perez, de cuya unión nacieron dos hijos: Tomas Andal y Luis Andal.\n\nRESUELVO: Declarar, en cuanto ha lugar por derecho, que por el fallecimiento de Juan Carlos Andal le suceden en carácter de universales herederos su cónyuge supérstite Maria Perez y sus hijos Tomas Andal y Luis Andal.\nREGÍSTRESE. NOTIFÍQUESE.\n"),
            ("Testamento_Olografo.txt", "txt", "Yo, Juan Carlos Andal, en mi sano juicio y plena capacidad mental, redacto este testamento ológrafo para manifestar mi última voluntad.\nDeclaro que instituyo como únicos y universales herederos de todos mis bienes a mis hijos Tomas Andal y Luis Andal, en partes iguales.\nEn caso de que alguno no pueda o no quiera heredar, su porción acrecerá a favor del otro.\nLugar y Fecha: Buenos Aires, 10 de octubre de 2020.\nFirma: Juan Carlos Andal\n")
        ],
        "Poder General Amplio": [
            ("Poder_Administracion.txt", "pdf", "ESCRITURA NÚMERO CIENTO DIEZ.- En la Ciudad Autónoma de Buenos Aires, a los 20 días del mes de julio de 2023, ante mí, Escribano Público Titular del Registro Nro 45, comparece TOMAS ANDAL, argentino, mayor de edad, DNI 29.123.456, hábil, a quien identifico.\n\nY EL COMPARECIENTE DICE: Que confiere PODER GENERAL DE ADMINISTRACIÓN Y DISPOSICIÓN a favor de MARIA PEREZ, para que en su nombre y representación actúe en todos sus asuntos comerciales, bancarios y jurídicos sin limitación alguna.\nFacultades: Administrar bienes, percibir alquileres, abrir y cerrar cuentas corrientes, firmar escrituras traslativas de dominio, iniciar juicios.\n\nLEO al otorgante quien asiente y firma por ante mí, doy fe.\n")
        ],
        "Escritura Compraventa": [
            ("Escritura_Departamento.txt", "pdf", "ESCRITURA NÚMERO CIENTO ONCE.- COMPRAVENTA DE INMUEBLE. En Buenos Aires, comparecen: por una parte Carlos Gómez (Vendedor) y por la otra Tomas Andal (Comprador).\n\nPRIMERO: El Vendedor VENDE al Comprador el inmueble sito en Avenida Rivadavia 4500, Piso 5, Dpto B, CABA. Matrícula 12-456.\nSEGUNDO: El precio de la venta es de U$S 120.000 (ciento veinte mil dólares estadounidenses), que el Vendedor manifiesta haber recibido antes de este acto en dinero en efectivo, sirviendo la presente de suficiente recibo y carta de pago.\nTERCERO: El Comprador adquiere el inmueble en el estado en que se encuentra y que declara conocer y aceptar.\n\nEl Escribano autorizante procedió a leer la escritura, la que fue firmada de plena conformidad.\n")
        ]
    }

    for nombre_carpeta, tipo in carpetas:
        tramite_id = crear_tramite(nombre_carpeta, tipo)
        print(f"Creada Carpeta '{nombre_carpeta}' (ID: {tramite_id})")

        # Create physical directory for files
        carpeta_path = os.path.join(UPLOADS_DIR, f"cliente_{cliente_id}", f"tramite_{tramite_id}")
        os.makedirs(carpeta_path, exist_ok=True)

        for file_name, file_type, file_content in docs_info[nombre_carpeta]:
            file_disk_path = os.path.join(carpeta_path, file_name)
            
            with open(file_disk_path, "w", encoding="utf-8") as f:
                f.write(file_content)
                
            # Insert Document in DB
            db_path_relative = f"uploads/clientes/cliente_{cliente_id}/tramite_{tramite_id}/{file_name}"
            
            cursor.execute(
                """
                INSERT INTO documentos_libreria (
                    workspace_id, cliente_id, tramite_id, nombre, tipo, path, is_generated, fecha_subida
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    workspace_id, cliente_id, tramite_id, file_name, file_type, db_path_relative,
                    0, datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                )
            )
            print(f"  - Añadido documento '{file_name}'")

    conn.commit()
    conn.close()
    print("Seed finalizado exitosamente.")

if __name__ == "__main__":
    main()
