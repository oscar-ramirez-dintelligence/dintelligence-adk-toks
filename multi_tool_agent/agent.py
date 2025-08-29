# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import logging
import json
from typing import Any, Dict

from google.adk.agents import Agent
from google.adk.tools.retrieval.vertex_ai_rag_retrieval import VertexAiRagRetrieval
from vertexai.preview import rag
from google.api_core import retry
from google.api_core import exceptions as google_exceptions
import google.generativeai as genai

from dotenv import load_dotenv
from .prompts import return_instructions_root

# Configurar logging con formato detallado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

class CustomVertexAiRagRetrieval(VertexAiRagRetrieval):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    @retry.Retry(
        predicate=retry.if_exception_type(
            google_exceptions.ResourceExhausted,
            google_exceptions.ServiceUnavailable,
            google_exceptions.DeadlineExceeded
        )
    )
    async def _arun(self, query: str) -> Dict[str, Any]:
        """Ejecuta la búsqueda RAG con reintentos automáticos"""
        try:
            # Configurar el cliente RAG
            corpus = rag.RAGCorpus(
                project=os.getenv("GOOGLE_CLOUD_PROJECT"),
                location="us-central1",
                corpus_id="dintelligence-knowledge-base"
            )

            # Realizar la búsqueda
            result = await corpus.search_async(
                query=query,
                max_results=5,  # Ajustar según necesidades
                vectorize_query=True
            )

            # Procesar y retornar resultados
            return {
                "matches": [
                    {
                        "text": chunk.text,
                        "metadata": chunk.metadata,
                        "score": chunk.semantic_similarity_score
                    }
                    for chunk in result.chunks
                ]
            }

        except Exception as e:
            logger.error(f"Error en RAG retrieval: {str(e)}")
            raise
        try:
            # Registrar la consulta que se está enviando
            logger.info(f"Enviando consulta a RAG: {query}")
            
            result = await super()._arun(query)
            
            # Registrar la respuesta exitosa
            logger.info("Consulta RAG exitosa")
            return result
            
        except google_exceptions.InvalidArgument as e:
            logger.error("Error de argumento inválido en RAG: " + str(e))
            logger.error("Detalles de la solicitud: " + json.dumps({'query': query}))
            raise
        except Exception as e:
            logger.error("Error inesperado en RAG: " + str(e))
            raise

class ProcessorAgent(Agent):
    """Agente principal para procesar documentos y responder consultas"""
    
    def __init__(self):
        try:
            # Configurar el retrieval RAG
            retrieval_tool = CustomVertexAiRagRetrieval(
                name='document_retrieval',
                description='Herramienta para recuperar documentación y materiales de referencia del corpus RAG',
                rag_resources=[rag.RagResource(
                rag_corpus="projects/com-next-toks/locations/us-central1/ragCorpora/6917529027641081856"

                )],
                similarity_top_k=20,
                vector_distance_threshold=1
            )
            logger.info("RAG retrieval configurado exitosamente")
            
            # Inicializar el agente base
            super().__init__(
                name="processor_agent",
                description="Agente experto en procesar y analizar documentos y procesos empresariales",
                model="gemini-2.5-flash",
                instruction=return_instructions_root(),
                tools=[retrieval_tool]
            )
            logger.info("Agente configurado exitosamente")
            logger.info("Modelo configurado: gemini-2.5-flash")
            
        except Exception as e:
            logger.error(f"Error al configurar el agente: {str(e)}")
            logger.error("Detalles de configuración: " + json.dumps({
                'model': 'gemini-2.5-flash',
                'name': 'processor_agent'
            }))
            raise

# Instanciar el agente principal
try:
    root_agent = ProcessorAgent()
    logger.info("Agente principal instanciado correctamente")
except Exception as e:
    logger.error(f"Error al instanciar el agente principal: {str(e)}")
    raise