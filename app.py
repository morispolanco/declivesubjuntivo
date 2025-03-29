import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import time
import requests
from bs4 import BeautifulSoup

# Configuración inicial
st.set_page_config(page_title="Análisis del Subjuntivo con Cervantes Virtual", layout="wide")

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

# Función para buscar y extraer textos de Cervantes Virtual
def extraer_datos_cervantes(anio_inicio, anio_fin, max_textos=5):
    base_url = "http://www.cervantesvirtual.com/buscador/"
    resultados = []
    
    # Parámetros de búsqueda (simulación)
    payload = {
        "q": f"fecha:{anio_inicio}-{anio_fin}",  # Búsqueda aproximada por rango de fechas
        "type": "obra",
        "sort": "fecha"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        # Buscar obras en el catálogo
        response = requests.get(base_url, params=payload, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Extraer enlaces a obras (ajusta el selector tras inspeccionar)
        obras = soup.select("ul.resultados li a")  # Hipotético, inspecciona HTML real
        
        if not obras:
            st.error("No se encontraron obras en el rango de fechas especificado.")
            return []
        
        st.info(f"Se encontraron {len(obras)} obras. Procesando...")
        
        for obra in obras[:max_textos]:
            titulo = obra.get_text(strip=True)
            enlace = obra.get("href")
            if not enlace.startswith("http"):
                enlace = "http://www.cervantesvirtual.com" + enlace
            
            # Acceder al texto completo
            texto_response = requests.get(enlace, headers=headers)
            texto_soup = BeautifulSoup(texto_response.text, "html.parser")
            
            # Extraer contenido (ajusta según estructura de la página)
            contenido = texto_soup.select_one("div.texto-obra")  # Hipotético
            if contenido:
                texto = contenido.get_text(strip=True)[:1000]  # Limitar a 1000 caracteres por muestra
                periodo = f"{anio_inicio}-{anio_fin}"
                resultados.append((periodo, texto, "Cervantes Virtual", titulo))
                st.info(f"Texto extraído: {titulo}")
            else:
                st.warning(f"No se pudo extraer el texto de: {titulo}")
            
            time.sleep(2)  # Pausa para evitar sobrecarga
        
        return resultados
    except Exception as e:
        st.error(f"Error al conectar con Cervantes Virtual: {e}")
        return []

# Función para guardar datos en un CSV
def guardar_en_csv(datos, archivo="corpus_cervantes.csv"):
    df = pd.DataFrame(datos, columns=["periodo", "texto", "fuente", "titulo"])
    df.to_csv(archivo, index=False, mode="a", header=not pd.io.common.file_exists(archivo))
    st.success(f"Guardados {len(datos)} registros en el archivo CSV: {archivo}")

# Función para cargar datos desde un CSV
def cargar_desde_csv(archivo="corpus_cervantes.csv"):
    try:
        df = pd.read_csv(archivo)
        return df
    except FileNotFoundError:
        st.warning("No se encontró el archivo CSV. Extrae datos de Cervantes Virtual primero.")
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
st.title("Análisis del Subjuntivo con Cervantes Virtual")

# Extracción de datos desde Cervantes Virtual
st.sidebar.header("Extracción de Cervantes Virtual")
anio_inicio = st.sidebar.slider("Año de inicio", 1500, 1600, 1500, step=20)
anio_fin = anio_inicio + 20
max_textos = st.sidebar.slider("Máximo de textos por período", 1, 10, 5)

if st.sidebar.button("Extraer datos de Cervantes Virtual"):
    with st.spinner("Extrayendo datos de Cervantes Virtual..."):
        datos = extraer_datos_cervantes(anio_inicio, anio_fin, max_textos)
        if datos:
            guardar_en_csv(datos)
            st.success(f"Datos extraídos y guardados para {anio_inicio}-{anio_fin}")
        time.sleep(2)

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
            file_name="resultados_cervantes.csv",
            mime="text/csv"
        )
else:
    st.warning("No hay datos en el archivo CSV. Extrae datos de Cervantes Virtual primero.")

with st.expander("Acerca de esta aplicación"):
    st.write("""
    Esta aplicación extrae textos de la Biblioteca Virtual Miguel de Cervantes y analiza la frecuencia del subjuntivo.
    Los datos se almacenan en un archivo CSV ('corpus_cervantes.csv') y se visualizan con Streamlit.
    Nota: La extracción automática requiere inspeccionar el HTML real y cumplir con los términos de uso.
    """)
