import os

import streamlit as st
from dotenv import load_dotenv
from groq import Groq
from pydub import AudioSegment
from pytubefix import YouTube


def create_folders(audio_dir: str, summary_dir: str):
    """
    Cria as pastas necessárias se não estiver criada.
    Args:
        audio_dir (str): Diretório dos arquivos de áudio
        summary_dir (str): Diretório dos arquivos do vídeo
    """
    os.makedirs(audio_dir, exist_ok=True)
    os.makedirs(f"{audio_dir}/.temp", exist_ok=True)
    os.makedirs(summary_dir, exist_ok=True)


def download_youtube_audio(
    url: str, audio_dir: str, filename: str = "audio"
) -> dict[str, str]:
    """
    Baixa os áudios dos videos do Youtube com a URL informada.
    Args:
        url (str): Link do video do Youtube
        audio_dir (str): Local para baixar os arquivos de áudio
        filename (str): Nome do arquivo de áudio
    Returns:
        str: Nome do arquivo de áudio
    Raises:
        Exception: Quaiquer erros
        ValueError: Se nenhum áudio for encontrado
    """
    print("Baixando audio...")
    try:
        yt = YouTube(url)
        stream = yt.streams.filter(only_audio=True).order_by("abr").desc().first()
        if not stream:
            raise ValueError("Nenhum áudio do stream foi encontrado")
        stream.download(audio_dir, filename=f"{filename}.mp3")
        return {"title": yt.title, "filename": filename}
    except Exception as err:
        raise Exception(f"Erro ao baixar video: {err}")


def create_audio_chunk(audio_file_path: str, chunk_size: int, temp_dir: str):
    file_name = os.path.splitext(os.path.basename(audio_file_path))[0]
    audio = AudioSegment.from_file(audio_file_path)

    start = 0
    end = chunk_size
    counter = 0
    chunk_files = []

    while start < len(audio):
        chunk = audio[start:end]
        chunk_file_path = os.path.join(temp_dir, f"{counter}_{file_name}.mp3")
        chunk.export(chunk_file_path, format="mp3")
        chunk_files.append(chunk_file_path)

        start += chunk_size
        end += chunk_size
        counter += 1

    return chunk_files


def transcribe_audio(
    audio_file: str,
    audio_dir: str,
    groq_client: Groq,
    model_transcription: str = "whisper-large-v3-turbo",
    language: str = "pt",
) -> str:
    """
    Pega o áudio mp3 de `audio_dir` e transcreve ele.

    Args:
        audio_file (str): Local do arquivo de áudio
        audio_dir (str): Local de armazenamento de áudios
        groq_client (Groq): Cliente do Groq
        model_transcription (str): Nome do modelo de transcrição de áudio
        language (str): Transcreve para `language`
    Returns:
        str: Transcrição do áudio

    """
    print("Transcrevendo audio...")
    transcription = ""
    chunks_files = create_audio_chunk(audio_file, 2 * 60 * 1000, f"{audio_dir}/.temp")
    for chunk in chunks_files:
        with open(chunk, "rb") as file:
            transcription_llm = groq_client.audio.transcriptions.create(
                file=(chunk, file.read()),
                model=model_transcription,
                language=language,
                response_format="verbose_json",
            )
            transcription += f" {transcription_llm.text}"
        os.remove(chunk)
    os.remove(audio_file)
    return transcription


def create_summary(
    transcription: str,
    groq_client: Groq,
    summary_filename: str,
    model_llm: str,
    language_markdown: str = "Portugues-BR",
    out_dir: str = "summary_videos",
):
    """
    Cria um resumo em Markdown e salva na pasta específicada.
    Args:
        transcription (str): O texto para o modelo analizar
        groq_client (Groq): O cliente groq
        summary_filename (str): Nome do arquivo do sumário
        model_llm (str): Nome do modelo que vai ser usado
        language_markdown (str): Em qual idioma vai ser o sumário
        out_dir (str): Pasta onde vai armazenar o áudio
    Returns:
        Arquivo na pasta `out_dir`

    """
    summary_prompt = f"""
        Você é uma IA que pega o roteiro de um video destaca os pontos principais do video, faz uma explicação do video,
        falando sobre o tema, assunto, exemplos, etc.
        E a resposta deve ser em **{language_markdown}**.
        texto:
        {transcription}
    """

    print("Criando a melhor resposta...")
    llm = groq_client.chat.completions.create(
        model=model_llm,
        messages=[{"role": "user", "content": f"{summary_prompt}\n"}],
        temperature=0.6,
        max_completion_tokens=4096,
        top_p=0.95,
        reasoning_effort="default",
        stream=False,
        stop=None,
    )

    summary_response = llm.choices[0].message.content
    with open(f"{out_dir}/{summary_filename}.md", "w", encoding="utf-8") as markdown:
        markdown.write(f"""{summary_response}""")

    print("Tudo Pronto!")
    st.rerun()


def main(audio_dir: str = "videos_audios", summary_dir: str = "summary_videos") -> None:
    create_folders(audio_dir, summary_dir)

    loaded_env = load_dotenv()
    if not loaded_env:
        raise ValueError("Chave Api não encontrada. Defina GROQ_API_KEY no ambiente.")

    llm_model = "qwen/qwen3-32b"
    client = Groq()

    if "markdown_content" not in st.session_state:
        st.session_state.markdown_content = {}

    st.title("Criador de sumário de vídeo")

    with st.form("main_form"):
        url = st.text_input("URL do video")

        if st.form_submit_button("Criar Sumário") and url:
            with st.spinner("Aguarde..."):
                audio = download_youtube_audio(url, audio_dir)
                audio_file = f"{audio_dir}/{audio['filename']}.mp3"

                transcription_data = transcribe_audio(audio_file, audio_dir, client)
                create_summary(transcription_data, client, audio["title"], llm_model)

    with st.sidebar:
        st.subheader("Configurações")

        st.divider()
        if os.listdir("summary_videos"):
            for i, summary in enumerate(os.listdir("summary_videos")):
                col1, col2 = st.columns([0.6, 0.4])

                with col1:
                    st.text(summary.replace(".md", ""))
                with col2:
                    if st.button("Ler arquivo", key=i):
                        with open(
                            f"summary_videos/{summary}", "r", encoding="utf-8"
                        ) as mark:
                            st.session_state["markdown_content"]["Title"] = summary
                            st.session_state["markdown_content"]["Content"] = (
                                mark.read()
                            )
                        st.rerun()
        else:
            st.info("Nenhum arquivo encontrado. Crie um!")

    if st.session_state["markdown_content"]:
        st.divider()
        st.subheader(st.session_state["markdown_content"]["Title"].replace(".md", ""))
        st.markdown(st.session_state["markdown_content"]["Content"])


if __name__ == "__main__":
    main()
