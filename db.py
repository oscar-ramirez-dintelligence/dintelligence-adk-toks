import sqlite3
import os
from datetime import datetime

def init_db():
    """Inicializar la base de datos SQLite"""
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sessions.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Crear tabla de sesiones del agente si no existe
    c.execute('''
        CREATE TABLE IF NOT EXISTS sessions_agent (
            session_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            app_name TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL,
            last_used_at TIMESTAMP NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT 1
        )
    ''')
    
    conn.commit()
    conn.close()

def get_db():
    """Obtener conexión a la base de datos"""
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sessions.db')
    return sqlite3.connect(db_path)

def save_session(session_id, user_id, app_name):
    """Guardar o actualizar una sesión en la base de datos"""
    conn = get_db()
    c = conn.cursor()
    now = datetime.now().isoformat()
    
    try:
        c.execute('''
            INSERT INTO sessions_agent (session_id, user_id, app_name, created_at, last_used_at, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
            ON CONFLICT(session_id) DO UPDATE SET
                last_used_at = ?,
                is_active = 1
        ''', (session_id, user_id, app_name, now, now, now))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error al guardar la sesión: {e}")
        return False
    finally:
        conn.close()

def get_session(session_id):
    """Obtener una sesión de la base de datos"""
    conn = get_db()
    c = conn.cursor()
    
    try:
        c.execute('SELECT * FROM sessions_agent WHERE session_id = ? AND is_active = 1', (session_id,))
        session = c.fetchone()
        return session is not None
    except Exception as e:
        print(f"Error al obtener la sesión: {e}")
        return False
    finally:
        conn.close()

def deactivate_session(session_id):
    """Desactivar una sesión en la base de datos"""
    conn = get_db()
    c = conn.cursor()
    
    try:
        c.execute('UPDATE sessions_agent SET is_active = 0 WHERE session_id = ?', (session_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error al desactivar la sesión: {e}")
        return False
    finally:
        conn.close()
