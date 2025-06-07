import streamlit as st
import pandas as pd
import requests
import os

API_KEY = st.secrets["API_KEY"]
DB_PATH = 'series_db.csv'

@st.cache_data
def carregar_generos():
    url = f'https://api.themoviedb.org/3/genre/tv/list?api_key={API_KEY}&language=pt-BR'
    response = requests.get(url)
    if response.status_code == 200:
        genres = response.json().get("genres", [])
        return {g["id"]: g["name"] for g in genres}
    return {}

def buscar_detalhes_serie(nome_serie):
    url = f'https://api.themoviedb.org/3/search/tv?api_key={API_KEY}&query={nome_serie}&language=pt-BR'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data['results']:
            resultado = data['results'][0]
            tv_id = resultado['id']
            poster_path = resultado.get('poster_path')
            imagem_url = f'https://image.tmdb.org/t/p/w500{poster_path}' if poster_path else None
            generos_ids = resultado.get("genre_ids", [])
            generos_nomes = [generos.get(gid, "Desconhecido") for gid in generos_ids]

            url_detalhes = f'https://api.themoviedb.org/3/tv/{tv_id}?api_key={API_KEY}&language=pt-BR'
            response_detalhes = requests.get(url_detalhes)

            if response_detalhes.status_code == 200:
                detalhes = response_detalhes.json()
                
                poster_path = detalhes.get('poster_path')
                num_temporadas = data.get("number_of_seasons", None)
                num_episodios = detalhes.get("number_of_episodes", None)

            return {
                "titulo_original": resultado.get("original_name"),
                "ano": resultado.get("first_air_date", "")[:4],
                "nota_tmdb": resultado.get("vote_average"),
                "generos": ", ".join(generos_nomes),
                "imagem_url": imagem_url,
                "temporadas": num_temporadas,
                "episodios": num_episodios
            }
    return None

def salvar_serie(nome_pesquisa, nota_usuario, detalhes, categoria, temporada, episodio):
    nova_entrada = pd.DataFrame([{
        'pesquisa': nome_pesquisa,
        'titulo_original': detalhes['titulo_original'],
        'ano': detalhes['ano'],
        'generos': detalhes['generos'],
        'nota_tmdb': detalhes['nota_tmdb'],
        'nota_usuario': nota_usuario,
        'imagem': detalhes['imagem_url'],
        'n_temporadas': detalhes['temporadas'],
        'n_episodios': detalhes['episodios'],
        'categoria': categoria,
        'temporada': temporada if categoria == 'Assistindo' else '',
        'episodio': episodio if categoria == 'Assistindo' else ''
    }])
    if os.path.exists(DB_PATH):
        df = pd.read_csv(DB_PATH)
        df = pd.concat([df, nova_entrada], ignore_index=True)
    else:
        df = nova_entrada
    df.to_csv(DB_PATH, index=False)

def nota_input(id_serie):
    sem_nota = st.checkbox("Sem Nota", key=f"sem_nota_{id_serie}")

    if sem_nota:
        nota = None
    else:
        nota = st.slider("Nota", 0.5, 5.0, step = 0.5, key=f"nota_{id_serie}")

    return nota
# ---------------------- INTERFACE PRINCIPAL ----------------------

st.title("📺 Avaliação de Séries")
generos = carregar_generos()

st.header("➕ Adicionar nova série")

nome = st.text_input("Pesquisar nome da série")
categoria = st.selectbox("Categoria", ["Assistindo", "Concluído", "Watchlist", "Abandonado"])
if categoria != "Watchlist":
    nota = nota_input(nome)
else:
    nota = None
temporada = episodio = ""
if categoria == "Assistindo":
    temporada = st.text_input("Temporada atual", placeholder="ex: 2")
    episodio = st.text_input("Episódio atual", placeholder="ex: 5")
if categoria == "Abandonado":
    temporada = st.text_input("Temporada final", placeholder="ex: 2")
    episodio = st.text_input("Episódio final", placeholder="ex: 5")

if st.button("Adicionar série"):
    if nome:
        detalhes = buscar_detalhes_serie(nome)
        if detalhes:
            salvar_serie(nome, nota, detalhes, categoria, temporada, episodio)
            st.success(f"Série '{detalhes['titulo_original']}' adicionada com sucesso!")
        else:
            st.error("Série não encontrada.")
    else:
        st.warning("Digite o nome da série.")

# ---------------------- LISTAGEM E GERENCIAMENTO ----------------------

if os.path.exists(DB_PATH):
    st.header("📚 Suas listas")
    df = pd.read_csv(DB_PATH)

    aba = st.radio("Selecione uma lista:", ["Assistindo", "Concluído", "Abandonado", "Watchlist"])
    df_cat = df[df["categoria"] == aba]

    # Ordenação
    col_ordenar = st.selectbox("🔃 Ordenar por", ["titulo_original", "ano", "nota_tmdb", "nota_usuario"])
    df_cat = df_cat.sort_values(by=col_ordenar, ascending=True)

    if not df_cat.empty:
        for idx, row in df_cat.iterrows():
            with st.expander(f"{row['titulo_original']} ({row['ano']})"):
                st.markdown(f"- **Gêneros**: {row['generos']}")
                st.markdown(f"- **Nota TMDb**: {row['nota_tmdb']}")
                st.markdown(f"- **Número de temporadas**: {row['n_temporadas']}")
                st.markdown(f"- **Número de episódioss**: {row['n_episodios']}")
                st.image(row["imagem"], width=200)

                nova_temp, novo_epi = "", ""
                if aba == "Assistindo":
                    nova_temp = st.text_input("Editar temporada", value=str(row.get("temporada", "")), key=f"temp_{idx}")
                    novo_epi = st.text_input("Editar episódio", value=str(row.get("episodio", "")), key=f"epi_{idx}")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✏️ Editar nota", key=f"editar_{idx}"):
                        sem_nota = st.checkbox("Sem nota", key=f"sem_nota_editar_{idx}")
                        
                        if not sem_nota:
                            nova_nota = st.slider(
                                "Editar sua nota",
                                0.5, 5.0,
                                float(row["nota_usuario"]) if row["nota_usuario"] is not None else 3.0,
                                step=0.5,
                                key=f"nota_{idx}"
                            )
                        else:
                            nova_nota = None

                        if st.button("💾 Salvar nota", key=f"salvar_nota_{idx}"):
                            row["nota_usuario"] = nova_nota
                            st.success("Nota atualizada!")
                            st.rerun()

                with col2:
                    if st.button("🗑️ Remover série", key=f"remover_{idx}"):
                        df = df.drop(index=idx).reset_index(drop=True)
                        df.to_csv(DB_PATH, index=False)
                        st.success("Série removida com sucesso.")
                        st.rerun()
    else:
        st.info(f"Nenhuma série na lista **{aba}** ainda.")
else:
    st.info("Nenhuma série cadastrada.")
