# Criador de sumário com Groq

## O que é isso?

É uma aplicação onde você coloca o link do vídeo do youtube, e o modelo transcreve o vídeo, e faz uma análise dele
mostrando tópicos interessantes, um resumo, etc.

## Instalação

- Instalar aplicação:

```bash
git clone https://github.com/Junior-2103/Summary_video_creator.git
cd Summary_video_creator
```

- Instalar pacotes:

```bash
pip install -r requirements.txt
# ou
uv sync
```

- Declarar variáveis de ambiente:

Crie um arquivo *.env* com a variável de ambiente GROQ_API_KEY.
Veja um exemplo em *.env.example*

## Executar código

```bash
streamlit run main.py
# ou
uv streamlit run main.py
```
