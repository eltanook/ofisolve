import sqlite3
import os

DB_PATH = os.path.join("backend", "ofisolve.db")

def migrate():
    print(f"Migrating database at {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print("Database not found. Skipping migration.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get current columns for usuarios
    cursor.execute("PRAGMA table_info(usuarios)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if "avatar_url" not in columns:
        print("Adding 'avatar_url' to 'usuarios'")
        cursor.execute("ALTER TABLE usuarios ADD COLUMN avatar_url VARCHAR(255)")
    else:
        print("'avatar_url' already exists in 'usuarios'")

    # Get current columns for workspaces
    cursor.execute("PRAGMA table_info(workspaces)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if "moneda_defecto" not in columns:
        print("Adding 'moneda_defecto' to 'workspaces'")
        cursor.execute("ALTER TABLE workspaces ADD COLUMN moneda_defecto VARCHAR(10) DEFAULT 'ARS'")
    else:
        print("'moneda_defecto' already exists in 'workspaces'")
        
    if "iva_defecto" not in columns:
        print("Adding 'iva_defecto' to 'workspaces'")
        cursor.execute("ALTER TABLE workspaces ADD COLUMN iva_defecto NUMERIC DEFAULT 21.0")
    else:
        print("'iva_defecto' already exists in 'workspaces'")
        
    if "modelo_ia" not in columns:
        print("Adding 'modelo_ia' to 'workspaces'")
        cursor.execute("ALTER TABLE workspaces ADD COLUMN modelo_ia VARCHAR(100)")
    else:
        print("'modelo_ia' already exists in 'workspaces'")

    conn.commit()
    conn.close()
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
