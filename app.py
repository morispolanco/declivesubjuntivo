import streamlit as st
import requests
from bs4 import BeautifulSoup
import re

# Configuración de la página
st.set_page_config(page_title="Análisis de Tiempos Verbales Subjuntivos", layout="wide")

# Título de la aplicación
st.title("Análisis de Tiempos Verbales Subjuntivos en Textos del Proyecto Gutenberg")

# Función para buscar el ID del libro en el Proyecto Gutenberg
def get_gutenberg_book_id(title):
    search_url = f"https://www.gutenberg.org/ebooks/search/?query={title}"
    response = requests.get(search_url)
    soup = BeautifulSoup(response.text, "html.parser")
    book_link = soup.find("a", href=re.compile(r"/ebooks/\d+"))
    if book_link:
        book_id = re.search(r"/ebooks/(\d+)", book_link["href"]).group(1)
        return book_id
    return None

# Función para obtener el texto del libro
def get_gutenberg_text(book_id):
    text_url = f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt"
    response = requests.get(text_url)
    if response.status_code == 200:
        return response.text[:100000]  # Extraer los primeros 100,000 caracteres
    return None

# Función para analizar tiempos verbales en modo subjuntivo usando OpenRouter
def analyze_subjunctive_verbs(text):
    api_key = st.secrets["OPENROUTER_API_KEY"]
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    data = {
        "model": "google/gemini-2.5-pro-exp-03-25:free",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Analiza el siguiente texto y encuentra todos los verbos en modo subjuntivo. Proporciona una lista de estos verbos y cuenta cuántas veces aparece cada uno. Texto: {text[:5000]}"  # Limitamos a 5000 caracteres por solicitud
                    }
                ]
            }
        ]
    }
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=data
    )
    
    # Verificar si la solicitud fue exitosa
    if response.status_code == 200:
        try:
            result = response.json()
            
            # Imprimir la respuesta completa para depuración
            print("Respuesta completa de la API:", result)
            
            # Verificar si la estructura esperada existe
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
            else:
                st.error("La respuesta de la API no contiene la clave 'choices'.")
                return None
        except Exception as e:
            st.error(f"Error al procesar la respuesta de la API: {e}")
            return None
    else:
        st.error(f"Error al llamar a la API. Código de estado: {response.status_code}")
        return None

# Interfaz de usuario
title = st.text_input("Introduce el título de una obra del Proyecto Gutenberg:")

if title:
    with st.spinner("Buscando el libro..."):
        book_id = get_gutenberg_book_id(title)
        if book_id:
            st.success(f"Libro encontrado (ID: {book_id}). Descargando texto...")
            text = get_gutenberg_text(book_id)
            if text:
                st.success("Texto descargado exitosamente.")
                st.subheader("Resumen del Análisis")
                st.write(f"Se han extraído los primeros {len(text)} caracteres del texto.")

                with st.spinner("Analizando tiempos verbales en modo subjuntivo..."):
                    analysis_result = analyze_subjunctive_verbs(text)
                    if analysis_result:
                        st.subheader("Resultados del Análisis")
                        st.write(analysis_result)
            else:
                st.error("No se pudo descargar el texto del libro.")
        else:
            st.error("No se encontró ningún libro con ese título.")
