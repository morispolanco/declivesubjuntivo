import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import requests
from bs4 import BeautifulSoup

# Configuración inicial
st.set_page_config(page_title="Análisis del Subjuntivo con Project Gutenberg", layout="wide")

# Acceso a la API Key desde Secrets
openrouter_api_key = st.secrets["openrouter"]["api_key"]

# Función para llamar a la API de OpenRouter
def analizar_con_openrouter(texto=None, imagen_url=None):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openrouter_api_key}"
    }
    
    # Construir el contenido del mensaje
    messages = []
    if texto:
        messages.append({"role": "user", "content": [{"type": "text", "text": texto}]})
    if imagen_url:
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": "Describe esta imagen:"},
                {"type": "image_url", "image_url": {"url": imagen_url}}
            ]
        })
    
    data = {
        "model": "google/gemini-2.5-pro-exp-03-25:free",
        "messages": messages
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        st.error(f"Error al llamar a la API de OpenRouter: {e}")
        return None

# Función para analizar subjuntivo
@st.cache_data
def analizar_subjuntivo(texto):
    resultado = analizar_con_openrouter(texto=texto)
    if resultado:
        # Supongamos que la respuesta contiene un número que indica la cantidad de subjuntivos
        try:
            subj_count = int(resultado.split()[0])  # Ajusta según la estructura de la respuesta
            verb_count = len([word for word in texto.split() if word.lower().endswith(("ar", "er", "ir"))])
            return subj_count, verb_count
        except ValueError:
            st.error("La respuesta del modelo no tiene el formato esperado.")
            return 0, 0
    return 0, 0

# Función para descargar un libro de Project Gutenberg
def descargar_libro_gutenberg(libro_id):
    url = f"https://www.gutenberg.org/files/{libro_id}/{libro_id}-0.txt"
    try:
        response = requests.get(url)
        response.raise_for_status()
        texto = response.text
        return texto[:10000]  # Limitar a 10,000 caracteres para evitar sobrecarga
    except Exception as e:
        st.error(f"Error al descargar el libro de Project Gutenberg: {e}")
        return None

# Función para guardar datos en un CSV
def guardar_en_csv(datos, archivo="corpus_gutenberg.csv"):
    df = pd.DataFrame(datos, columns=["periodo", "texto", "fuente", "titulo"])
    df.to_csv(archivo, index=False, mode="a", header=not pd.io.common.file_exists(archivo))
    st.success(f"Guardados {len(datos)} registros en el archivo CSV: {archivo}")

# Función para cargar datos desde un CSV
def cargar_desde_csv(archivo="corpus_gutenberg.csv"):
    try:
        df = pd.read_csv(archivo)
        return df
    except FileNotFoundError:
        st.warning("No se encontró el archivo CSV. Extrae datos de Project Gutenberg primero.")
        return pd.DataFrame(columns=["periodo", "texto", "fuente", "titulo"])

# Función para procesar el corpus
@st.cache_data
def procesar_corpus(df):
    resultados = []
    for idx, row in df.iterrows():
        subj_count, verb_count = analizar_subjuntivo(row["texto"])
        frecuencia = (subj_count / verb_count * 100) if verb_count > 0 else 0
        resultados.append({
            "Periodo": row["periodo"],
            "Subjuntivos": subj_count,
            "Verbos": verb_count,
            "Frecuencia": frecuencia,
            "Título": row["titulo"]
        })
    return pd.DataFrame(resultados)

# Interfaz de Streamlit
st.title("Análisis del Subjuntivo con Project Gutenberg")

# Extracción de datos desde Project Gutenberg
st.sidebar.header("Extracción de Project Gutenberg")
libro_ids = st.sidebar.text_input(
    "IDs de libros (separados por comas)",
    value="12345,67890,11111"
).split(",")
libro_ids = [int(id.strip()) for id in libro_ids if id.strip().isdigit()]

if st.sidebar.button("Extraer datos de Project Gutenberg"):
    with st.spinner("Descargando y procesando libros..."):
        datos = []
        for libro_id in libro_ids:
            texto = descargar_libro_gutenberg(libro_id)
            if texto:
                periodo = "general"  # Puedes ajustar esto según la fecha del libro
                titulo = f"Libro {libro_id}"
                datos.append((periodo, texto, "Project Gutenberg", titulo))
                st.info(f"Texto extraído: Libro {libro_id}")
        
        if datos:
            guardar_en_csv(datos)
            st.success("Datos extraídos y guardados.")

# Cargar datos desde el CSV
df_corpus = cargar_desde_csv()
if not df_corpus.empty:
    st.write("Corpus cargado desde el archivo CSV:")
    st.dataframe(df_corpus.head())

    # Filtros
    st.sidebar.header("Filtros")
    periodos_disponibles = sorted(df_corpus["periodo"].unique())
    filtro_inicio = st.sidebar.selectbox("Período de inicio", periodos_disponibles, index=0)
    filtro_fin = st.sidebar.selectbox("Período de fin", periodos_disponibles, index=len(periodos_disponibles)-1)
    mostrar_detalle = st.sidebar.checkbox("Mostrar detalle", value=True)

    # Filtrar corpus
    df_filtrado = df_corpus[
        df_corpus["periodo"].apply(lambda x: x >= filtro_inicio and x <= filtro_fin)
    ]

    # Procesar datos
    if not df_filtrado.empty:
        df_resultados = procesar_corpus(df_filtrado)

        st.subheader("Resultados Generales")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Subjuntivos", df_resultados["Subjuntivos"].sum())
        col2.metric("Total Verbos", df_resultados["Verbos"].sum())
        col3.metric("Frecuencia Media", f"{df_resultados['Frecuencia'].mean():.2f}%")

        if mostrar_detalle:
            st.subheader("Detalles por Período")
            st.dataframe(df_resultados.style.format({"Frecuencia": "{:.2f}%"}))

        st.subheader("Evolución del Subjuntivo")
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(df_resultados["Periodo"], df_resultados["Frecuencia"], marker="o", color="b")
        ax.set_xlabel("Período")
        ax.set_ylabel("Frecuencia (%)")
        ax.set_title("Frecuencia del Subjuntivo")
        plt.xticks(rotation=45)
        st.pyplot(fig)

        st.subheader("Distribución de Subjuntivos y Verbos")
        fig2, ax2 = plt.subplots(figsize=(10, 5))
        bar_width = 0.35
        x = np.arange(len(df_resultados["Periodo"]))
        ax2.bar(x - bar_width/2, df_resultados["Subjuntivos"], bar_width, label="Subjuntivos", color="skyblue")
        ax2.bar(x + bar_width/2, df_resultados["Verbos"], bar_width, label="Verbos Totales", color="lightcoral")
        ax2.set_xlabel("Período")
        ax2.set_ylabel("Cantidad")
        ax2.set_xticks(x)
        ax2.set_xticklabels(df_resultados["Periodo"], rotation=45)
        ax2.legend()
        st.pyplot(fig2)

        csv = df_resultados.to_csv(index=False)
        st.download_button(
            label="Descargar resultados como CSV",
            data=csv,
            file_name="resultados_gutenberg.csv",
            mime="text/csv"
        )
else:
    st.warning("No hay datos en el archivo CSV. Extrae datos de Project Gutenberg primero.")

with st.expander("Acerca de esta aplicación"):
    st.write("""
    Esta aplicación extrae textos de Project Gutenberg y analiza la frecuencia del subjuntivo.
    Los datos se almacenan en un archivo CSV ('corpus_gutenberg.csv') y se visualizan con Streamlit.
    Nota: La extracción automática requiere inspeccionar el HTML real y cumplir con los términos de uso.
    """)
