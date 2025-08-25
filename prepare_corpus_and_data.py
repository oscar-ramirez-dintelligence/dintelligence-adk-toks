from google.auth import default
import vertexai
from vertexai.preview import rag
import os


# --- Please fill in your configurations ---
# Retrieve the PROJECT_ID from the environmental variables.
PROJECT_ID = "com-next-toks"
LOCATION = "us-central1"
CORPUS_DISPLAY_NAME = "procesos_Corpus"
CORPUS_DESCRIPTION = "Corpus containing data from JSONL files"
JSONL_DIR_PATH = "data/outputs"
ENV_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))


# --- Start of the script ---
def initialize_vertex_ai():
    credentials, _ = default()
    vertexai.init(
        project=PROJECT_ID, location=LOCATION, credentials=credentials
    )


def create_or_get_corpus():
    """Creates a new corpus or retrieves an existing one."""
    embedding_model_config = rag.EmbeddingModelConfig(
        publisher_model="publishers/google/models/text-embedding-004"
    )
    existing_corpora = rag.list_corpora()
    corpus = None
    for existing_corpus in existing_corpora:
        if existing_corpus.display_name == CORPUS_DISPLAY_NAME:
            corpus = existing_corpus
            print(f"Found existing corpus with display name '{CORPUS_DISPLAY_NAME}'")
            break
    if corpus is None:
        corpus = rag.create_corpus(
            display_name=CORPUS_DISPLAY_NAME,
            description=CORPUS_DESCRIPTION,
            embedding_model_config=embedding_model_config,
        )
        print(f"Created new corpus with display name '{CORPUS_DISPLAY_NAME}'")
    return corpus


def upload_jsonl_to_corpus(corpus_name, jsonl_path, display_name, description):
    """Uploads a JSONL file to the specified corpus."""
    print(f"Uploading {display_name} to corpus...")
    try:
        rag_file = rag.upload_file(
            corpus_name=corpus_name,
            path=jsonl_path,
            display_name=display_name,
            description=description,
        )
        print(f"Successfully uploaded {display_name} to corpus")
        return rag_file
    except Exception as e:
        print(f"Error uploading file {display_name}: {e}")
        return None


def upload_all_jsonl_files(corpus_name):
    """Uploads all JSONL files from the specified directory to the corpus."""
    successful_uploads = 0
    failed_uploads = 0
    
    try:
        # Obtener lista de archivos JSONL en el directorio
        jsonl_files = [f for f in os.listdir(JSONL_DIR_PATH) if f.endswith('.jsonl')]
        total_files = len(jsonl_files)
        print(f"\nEncontramos {total_files} archivos JSONL para cargar...")
        
        # Cargar cada archivo JSONL
        for jsonl_file in jsonl_files:
            file_path = os.path.join(JSONL_DIR_PATH, jsonl_file)
            result = upload_jsonl_to_corpus(
                corpus_name=corpus_name,
                jsonl_path=file_path,
                display_name=jsonl_file,
                description=f"Data from {jsonl_file}"
            )
            if result:
                successful_uploads += 1
            else:
                failed_uploads += 1
        
        print(f"\nResumen de carga:")
        print(f"- Archivos cargados exitosamente: {successful_uploads}")
        print(f"- Archivos con error: {failed_uploads}")
        print(f"- Total de archivos procesados: {total_files}")
        
    except Exception as e:
        print(f"Error al procesar el directorio de archivos JSONL: {e}")


def list_corpus_files(corpus_name):
    """Lists files in the specified corpus."""
    files = list(rag.list_files(corpus_name=corpus_name))
    print(f"Total files in corpus: {len(files)}")
    for file in files:
        print(f"File: {file.display_name} - {file.name}")


def test_rag_functionality(corpus_name):
    """Verifica que el RAG funciona correctamente haciendo una consulta de prueba."""
    try:
        # Crear una consulta de prueba
        print("\nProbando funcionalidad RAG...")
        query = "¿Qué es un proceso de abastecimiento?"
        
        # Configurar el motor de RAG
        rag_engine = rag.RetrievalAutomation(
            project=PROJECT_ID,
            location=LOCATION,
        )
        
        # Realizar la consulta
        response = rag_engine.query(
            corpus_name=corpus_name,
            query=query,
            max_documents=3
        )
        
        # Imprimir resultados
        print(f"\nConsulta de prueba: {query}")
        print("\nRespuesta:")
        print(response.answer)
        print("\nDocumentos relevantes encontrados:")
        for chunk in response.relevant_chunks:
            print(f"- Documento: {chunk.document_display_name}")
            print(f"  Fragmento: {chunk.chunk_text[:200]}...\n")
        
        return True
    except Exception as e:
        print(f"Error al probar el RAG: {e}")
        return False


def main():
    initialize_vertex_ai()
    corpus = create_or_get_corpus()
    
    # Cargar todos los archivos JSONL del directorio
    upload_all_jsonl_files(corpus_name=corpus.name)
    
    # List all files in the corpus
    list_corpus_files(corpus_name=corpus.name)
    
    # Verificar la funcionalidad del RAG
    test_rag_functionality(corpus_name=corpus.name)

if __name__ == "__main__":
    main()