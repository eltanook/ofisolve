import os

mock_dir = r"C:\TN\Proyectos\ofisolve\mock"
os.makedirs(mock_dir, exist_ok=True)

files = {
    "Declaratoria_Herederos.txt": """--- DECLARATORIA DE HEREDEROS ---
Juzgado Civil y Comercial N° 5 - Expediente 4521/2023
En la ciudad de Buenos Aires, a los 15 días del mes de mayo de 2024, VISTOS: los autos caratulados "SUCESIÓN AB INTESTATO DE PEREZ, JUAN CARLOS", de los que resulta que el causante falleció el 10 de enero de 2023, y CONSIDERANDO: que se ha probado el vínculo invocado por los presentantes.
FALLO: Declarando que por fallecimiento de D. Juan Carlos Perez le suceden en carácter de universales herederos sus hijos: Tomás Andal y María Perez, y su cónyuge supérstite, Marta Gomez, sin perjuicio de terceros. 
Firma: Dr. Ernesto Silva - Juez.
""",
    "Inventario_Bienes.txt": """--- INVENTARIO Y AVALÚO DE BIENES ---
Sucesión: PEREZ, JUAN CARLOS
Fecha: 20 de mayo de 2024

Bienes que componen el acervo hereditario:
1. Inmueble sito en Calle Falsa 123, CABA. Matrícula 12-4567. Valuación fiscal: $ 15.000.000.
2. Automotor marca Ford, modelo Focus, Dominio AA123BB. Valuación: $ 5.500.000.
3. Cuenta bancaria Banco Nación N° 12345678/9. Saldo: $ 2.300.000.

Total del activo: $ 22.800.000.
Firma: Tomás Andal (Heredero)
""",
    "Poder_Especial_Bancario.txt": """--- PODER ESPECIAL BANCARIO ---
ESCRITURA NÚMERO CIENTO VEINTE (120).
En la Ciudad Autónoma de Buenos Aires, a los 10 días del mes de junio de 2024, ante mí, Escribano Público, comparece el Sr. Tomás Andal, DNI 35.123.456, quien acredita su identidad y expresa: Que confiere PODER ESPECIAL BANCARIO a favor de D. Roberto Sánchez, DNI 25.654.321, para que en su nombre y representación realice todo tipo de trámites, gestiones, depósitos, extracciones, apertura y cierre de cuentas, solicitud de tarjetas de crédito y débito ante cualquier entidad bancaria, oficial o privada.
Leída que le fue, se ratifica y firma por ante mí, doy fe.
""",
    "Documento_Identidad_Constructora_Horizonte_S.A..pdf": """%PDF-1.4
%Mock PDF Content para Documento de Identidad Constructora
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length 120 >>
stream
BT
/F1 12 Tf
70 700 Td
(ESTATUTO SOCIAL - CONSTRUCTORA HORIZONTE S.A. - CUIT: 30-12345678-9 - Representante: Tomas Andal) Tj
ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f
0000000010 00000 n
0000000060 00000 n
0000000117 00000 n
0000000223 00000 n
0000000392 00000 n
trailer
<< /Size 6 /Root 1 0 R >>
startxref
481
%%EOF
""",
    "Estatuto_Social.pdf": """%PDF-1.4
%Mock PDF Content para Estatuto Social
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>
endobj
4 0 obj
<< /Length 130 >>
stream
BT
/F1 12 Tf
70 700 Td
(ESTATUTO DE SOCIEDAD ANONIMA - CONSTRUCTORA HORIZONTE S.A. Constitucion: 05-02-2015. Capital: $50.000.000) Tj
ET
endstream
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 6
0000000000 65535 f
0000000010 00000 n
0000000060 00000 n
0000000117 00000 n
0000000223 00000 n
0000000403 00000 n
trailer
<< /Size 6 /Root 1 0 R >>
startxref
492
%%EOF
"""
}

for filename, content in files.items():
    filepath = os.path.join(mock_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
        print(f"Created {filepath}")

