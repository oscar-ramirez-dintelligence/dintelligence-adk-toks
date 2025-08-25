import streamlit as st
import requests
import json
import uuid
from db import init_db, save_session, get_session, deactivate_session

# Configuración de la página para ocultar el botón de deploy
st.set_page_config(
    page_title="Agente de Operaciones de Restaurantes",
    page_icon="🤖",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

# Ocultar el botón de deploy y otros elementos de la interfaz
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Inicializar la base de datos
init_db()

# URLs para los endpoints del ADK
BASE_URL = "http://0.0.0.0:4000"
RUN_URL = f"{BASE_URL}/run"

def create_or_get_session(session_id):
    """Crear una nueva sesión en el ADK o verificar si existe, y guardarla en SQLite"""
    try:
        # Configurar los valores para la URL
        app_name = "multi_tool_agent"
        user_id = "streamlit_user"
        
        # Verificar primero en la base de datos local
        if get_session(session_id):
            print("Sesión encontrada en la base de datos local")
            return True
            
        # Construir la URL específica para esta sesión
        session_specific_url = f"{BASE_URL}/apps/{app_name}/users/{user_id}/sessions/{session_id}"
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Intentar crear la sesión en el ADK
        session_payload = None  # La especificación permite null para el body
        response = requests.post(session_specific_url, json=session_payload, headers=headers)
        
        # Imprimir información de depuración
        print(f"URL de la sesión: {session_specific_url}")
        print(f"Payload enviado: {session_payload}")
        print(f"Código de respuesta: {response.status_code}")
        
        success = False
        
        # Manejar diferentes casos de respuesta
        if response.status_code == 200:
            print("Nueva sesión creada exitosamente")
            success = True
        elif response.status_code == 400 and "Session already exists" in response.text:
            print("La sesión ya existía en el ADK")
            success = True
        else:
            response.raise_for_status()
            
        # Si todo fue exitoso, guardar o actualizar la sesión en la base de datos
        if success and save_session(session_id, user_id, app_name):
            return True
            
        return False
        
    except requests.exceptions.RequestException as e:
        print(f"Error al gestionar la sesión en el ADK: {e}")
        if hasattr(e.response, 'text'):
            print(f"Detalles del error: {e.response.text}")
        return False
    except Exception as e:
        print(f"Error al gestionar la sesión en la base de datos: {e}")
        return False

st.title("Agente de Operaciones de Restaurantes")
st.markdown("¡Hola! Soy tu asistente para consultas sobre políticas y procedimientos. Pregúntame lo que necesites.")


# Inicializar el historial de chat y el ID de la sesión
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4()) # Genera un ID de sesión único

# Mostrar mensajes del historial al recargar la página
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Capturar la entrada del usuario
if prompt := st.chat_input("Escribe tu pregunta aquí..."):
    # Añadir el mensaje del usuario al historial
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Mostrar el mensaje del usuario en la interfaz
    with st.chat_message("user"):
        st.markdown(prompt)

    # Primero, asegurarse de que existe una sesión válida
    if not create_or_get_session(st.session_state.session_id):
        st.error("No se pudo crear o verificar la sesión con el agente")
        st.stop()

    # Preparar la solicitud para la API del agente
    payload = {
        "appName": "multi_tool_agent",
        "userId": "streamlit_user",
        "sessionId": st.session_state.session_id,
        "newMessage": {
            "parts": [
                {"text": prompt}
            ],
            "role": "user"
        },
        "streaming": False
    }

    # Enviar la solicitud al agente ADK
    with st.spinner("Buscando una respuesta..."):
        try:
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            response = requests.post(RUN_URL, json=payload, headers=headers)
            response.raise_for_status()  # Lanza una excepción si hay un error HTTP
            agent_response = response.json()
            
            # Para depuración
            print("Payload enviado:", json.dumps(payload, indent=2))
            print("Respuesta del agente:", json.dumps(agent_response, indent=2))

            # La respuesta del endpoint /run tiene una estructura diferente
            # Buscar el último evento que contenga un mensaje del agente
            agent_message_parts = []
            for event in agent_response:
                # El evento con la respuesta del agente suele tener 'author' como 'model' o el nombre del agente
                if event.get("author") and event["author"] != "user":
                    content = event.get("content")
                    if content and content.get("parts"):
                        for part in content["parts"]:
                            if part.get("text"):
                                agent_message_parts.append(part["text"])

            if agent_message_parts:
                agent_message = "\n".join(agent_message_parts)
            else:
                agent_message = "No pude encontrar una respuesta."

            # Añadir la respuesta del agente al historial
            st.session_state.messages.append({"role": "assistant", "content": agent_message})
            
            # Mostrar la respuesta en la interfaz
            with st.chat_message("assistant"):
                st.markdown(agent_message)
        
        except requests.exceptions.RequestException as e:
            error_message = f"Error al conectar con el agente: {e}"
            st.error(error_message)
            st.session_state.messages.append({"role": "assistant", "content": error_message})
            with st.chat_message("assistant"):
                st.markdown(error_message)