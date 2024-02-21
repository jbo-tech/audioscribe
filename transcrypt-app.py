import streamlit as st
import streamlit.components.v1 as components
import time
import json
import re
from listennotes import podcast_api
import assemblyai as aai
import yt_dlp
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from utils import sanitize_folder_name,convert_time_format,insert_spaces  # Import de la fonction de utils.py

# Page config
st.set_page_config(
    page_title="AudioScribe App : Audio To Text",
    page_icon="./assets/favicon.ico🧊",
    layout="centered",
    #initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': 'https://github.com/soapoperator/audioscribe',
        'About': 'mailto:app@jbo.mozmail.com'
    }
)

def listennotes_get_data_by_id(episode_id):
    response = client.fetch_episode_by_id(
        id=episode_id,
        show_transcript=1,
    )
    data = response.json()
    #ln_audio_url = data['audio']
    return data

def listennotes_get_data_by_search(episode_keyword):
    # Effectue une recherche d'épisode de podcast avec les critères spécifiés
    response = client.search(
        q=episode_keyword,
        sort_by_date=0,
        type='episode',
        offset=0,
        len_min=5,
        len_max=180,
        published_after=0,
        only_in='title,description',
        region='fr',
        safe_mode=0,
        unique_podcasts=1,
        page_size=10,
    )
    data_results = response.json()
    # Vérification et affichage du premier résultat si disponible
    if data_results['results']:
        data = data_results['results'][0]
        #print(json.dumps(data, indent=4))  # Affiche les données formatées
        #ln_audio_url = data['audio']
        #audio_title = data['title_original']
        return data
    else:
        print("Pas de réponse.")
        exit(1)  # Arrête l'exécution si aucun résultat n'est trouvé

def youtube_get_data_by_url(url):
    """
    Extrait l'URL de l'audio au format m4a d'une vidéo YouTube spécifiée par son URL.
    :param URL (str): L'URL de la vidéo YouTube dont on souhaite extraire l'audio.
    """
    with yt_dlp.YoutubeDL() as ydl:
        info = ydl.extract_info(url, download=False)
    url_audio = None
    for format in info["formats"][::-1]:  # Parcours des formats en commençant par la fin
        if format["resolution"] == "audio only" and format["ext"] == "m4a":
            url_audio = format["url"]
            break
    data = {
        'audio': url_audio,
        'audio_length_sec': info["duration"],
    }
    return data

def spotify_get_data_by_id(id):
    info = sp.episode(id,market="FR")
    search_input = f"{info['name']} {info['show']['name']}"
    data = listennotes_get_data_by_search(search_input)
    #print(info)
    return data

def is_an_id(service_code, text):
    if service_code == 'ln':
        # Expression régulière pour un UUID hexadécimal sans tirets
        pattern = r"^[a-f0-9]{32}$"
    elif service_code == 'yt':
        # Expression régulière pour un UUID hexadécimal sans tirets
        pattern = r"^[a-zA-Z0-9_-]{11}$"
    elif service_code == 'sp':
        pattern = r"^[A-Za-z0-9]{22}$"
    # Enlever les espaces avant et après la chaîne
    chaine_sans_espaces = text.strip()
    # Vérifier si la chaîne correspond au pattern
    if re.match(pattern, chaine_sans_espaces):
        return True
    else:
        return False

def simulate_progress(ln_audio_length_sec, progress_bar, progress_messages):
    """
    Simulates progress based on audio length and updates a progress bar with custom messages.
    :param ln_audio_length_sec: Length of the audio in seconds.
    :param progress_bar: The progress bar object to update.
    :param progress_messages: A dictionary containing custom messages for specific progress percentages.
    """
    time_increment = float(ln_audio_length_sec) * 0.08 / 100
    time_total = float(ln_audio_length_sec) * 0.08
    initial_text = progress_messages[0]
    # Run the progress bar
    for percent_complete in range(100):
        time.sleep(time_increment)  # Simulation d'un travail en cours
        # Mise à jour du texte en fonction du pourcentage d'achèvement
        if percent_complete + 1 in progress_messages:
            progress_text = progress_messages[percent_complete + 1]
        else:
            progress_text = initial_text
        initial_text = progress_text
        time_total = time_total - time_increment
        progress_text = f":sparkles: Waiting time : {convert_time_format(time_total)}\n\n{progress_text}"
        st.spinner(progress_text)
        progress_bar.progress(percent_complete + 1, text=progress_text)

def clip(text):
    # Thanks to https://github.com/Aravind-krishnan-g/Streamlit-Clipboard
    js_text = json.dumps(text) # Utilisation de json.dumps pour échapper correctement la chaîne

    html_string = f"""
        <script>window.parent.navigator.clipboard.writeText({js_text});console.log({js_text})</script>
    """
    components.html(html_string,height=0,width=0)

def notify_and_copy(text,title):
    # Copie la dernière transcription ajoutée
    clip(text)
    # Affiche une notification toast
    st.toast(f'{title} copied successfully!', icon='🎉')
    # Ajoute la transcription à la liste des transcriptions copiées
    st.session_state.copied.append(text)

def transc_send(audio_url):
    transcript = transcriber.transcribe(audio_url)
    transcript_id = transcript.id   
    return transcript_id

def transc_get(transcript_id):
    polling_response = aai.Transcript.get_by_id(transcript_id)
    i=0
    while polling_response.status != 'completed':
        time.sleep(3)
        polling_response = aai.Transcript.get_by_id(transcript_id)
    return polling_response

def summary_transcript(transcript):
    prompt = "Summarize key points from this transcript in 5 bullets. Reply in French."
    result = aai.Lemur().task(
        prompt,
        final_model=aai.LemurModel.basic,
        input_text=transcript,
        #answer_format="Reply in French"
        )
    return result

def speaker_transcript(transcript):
    if len(transcript.utterances) > 0: # Vérifier si 'utterances' est présent et contient des éléments
        formatted_utterances = [f"Speaker {utterance.speaker} : {utterance.text}" for utterance in transcript.utterances]
        return "\n\n".join(formatted_utterances)
    else:
        return transcript.text

def topic_transcript(transcript):
    # print(transcript.iab_categories.summary)
    summary = transcript.iab_categories.summary
    if len(summary) > 0: # Vérifier si 'utterances' est présent et contient des éléments
        formatted_topics = [
            f"- {insert_spaces(last_element)} ({value * 100:.0f}%)"
            for key, value in summary.items() if value > 0.4
            for last_element in [key.split(">")[-1]]
        ]        
        return "\n".join(formatted_topics)
    else:
        return ""

def entity_transcript(transcript):
    # print(transcript.entities)
    if len(transcript.entities) > 0:
        #entities_sorted = sorted(transcript.entities, key=lambda x: x["entity_type"])
        entities_sorted = transcript.entities
        # Dictionnaire pour regrouper les entités par type
        grouped_entities = {}
        # Boucle sur chaque entité pour les regrouper et retirer les doublons basés sur `text`
        for entity in entities_sorted:
            entity_type = entity.entity_type
            text = entity.text
            # Si le type d'entité n'existe pas encore, créer une nouvelle entrée avec un ensemble pour suivre les textes uniques
            if entity_type not in grouped_entities:
                grouped_entities[entity_type] = set()
            # Ajouter le texte à l'ensemble des textes uniques pour ce type d'entité
            grouped_entities[entity_type].add(text)
        # Affichage des résultats groupés
        formatted_entities = []
        ignore_list = ["language", "nationality"]
        for entity_type, texts in grouped_entities.items():
            entity = entity_type.split(".")[-1]
            if entity.lower() in ignore_list:
                continue  # Passe à la prochaine itération si entity est à ignorer            
            formatted_entities.append(f"\n**{entity.capitalize()}**:")
            for text in texts:
                formatted_entities.append(f"- {text.capitalize()}")
        return "\n".join(formatted_entities)
    else:
        return ""

def process_tab(service_code, service_logo_url, progress_messages, **kwargs):
    """
    Génère le contenu pour un onglet donné en utilisant les spécificités du service.
    :param service_code: Code court pour le service (par ex., 'ln' pour ListenNotes, 'sp' pour Spotify, 'yt' pour YouTube)
    :param service_logo_url: URL du logo du service
    :param service_name: Nom complet du service
    :param **kwargs: Paramètres supplémentaires passés comme dictionnaire
    """
    # Construction des clés dynamiques basées sur le service_code
    form_key = f"{service_code}_form" #
    episode_input_key = f"{service_code}_episode_input" #
    submit_key = f"{service_code}_submit" #
    btn_copy_s1_key = f'{service_code}_btn_copy_s1' #
    btn_copy_t1_key = f'{service_code}_btn_copy_t1' #
    completed_key = f'{service_code}_completed' #
    input_key = f'{service_code}_input'
    summary_key = f'{service_code}_summary'
    topics_key = f'{service_code}_topics'
    entities_key = f'{service_code}_entities'
    transcription_key = f'{service_code}_transcription'
    
    # Layout
    if service_logo_url:
        st.markdown(f'## {messages_title.get(service_code, "Service not recognized")} <img  style="float: inline-end;" src="{service_logo_url}" width="auto" height="50"/>', unsafe_allow_html=True)
    else:
        st.markdown(f'## {messages_title.get(service_code, "Service not recognized")}', unsafe_allow_html=True)
    st.markdown(messages_intro.get(service_code, "Service not recognized"))
    
    # Form
    st.markdown('**Input parameter**')
    with st.form(key=form_key):
        # Création d'un champ de saisie pour l'utilisateur
        episode_input = st.text_input((messages_input.get(service_code, "Service not recognized")).capitalize(), key=f"{episode_input_key}_form")
        # Bouton de soumission
        submit_button = st.form_submit_button(label=':memo: Transcribe', type='primary')
        if submit_button: # Vérifie si le bouton de soumission a été cliqué
            if episode_input:  # Vérifie si ln_episode_input n'est pas vide
                st.session_state[submit_key] = True
                st.session_state[episode_input_key] = episode_input
                st.session_state.pop(btn_copy_s1_key, None)
                st.session_state.pop(btn_copy_t1_key, None)
                st.session_state[completed_key] = False
            else:
                message = messages_input.get(service_code, "Service not recognized")
                st.warning(f":eyes: Please {message}")

    if st.session_state[submit_key] is True:

        if btn_copy_s1_key not in st.session_state and btn_copy_t1_key not in st.session_state:

            episode_input = st.session_state[episode_input_key]

            # step 1 - Extract episode's url from listen notes
            if service_code == 'ln':
                if is_an_id(service_code, episode_input):
                    data = listennotes_get_data_by_id(episode_input)
                else:
                    data = listennotes_get_data_by_search(episode_input)        
            elif service_code == 'yt':
                if is_an_id(service_code, episode_input):
                    data = youtube_get_data_by_url(f"https://www.youtube.com/watch?v={episode_input}")
                else:
                    data = youtube_get_data_by_url(episode_input)        
            elif service_code == 'sp':
                if is_an_id(service_code, episode_input):
                    data = spotify_get_data_by_id(episode_input) 
                else:
                    pattern = r"https://open.spotify.com/episode/([a-zA-Z0-9]+)"
                    match = re.search(pattern, episode_input)
                    episode_id = match.group(1)
                    data = spotify_get_data_by_id(episode_id) 
            elif service_code == 'dt':
                data = {
                    'audio': episode_input,
                    'audio_length_sec': "60",
                }
            audio_length_sec = data['audio_length_sec']
            audio_url = data['audio']

            # step 2 - retrieve id of transcription response from AssemblyAI
            transcript_id = transc_send(audio_url)
            # transcript_id = "bff317dc-102b-4584-825c-3fe12b9d4b1c"

            # step 3 - get the transcription
            transcript = transc_get(transcript_id)

            # step 4 - transcription by speaker
            formatted_transcript = speaker_transcript(transcript)
            formatted_topics_transcript = topic_transcript(transcript)
            formatted_entities_transcript = entity_transcript(transcript)

            # step 5 - session logic
            st.session_state[input_key] = f"**Audio** : {audio_url}\n\n**Transcript ID** : {transcript_id}"
            st.session_state[summary_key] = transcript.summary
            st.session_state[topics_key] = formatted_topics_transcript
            st.session_state[entities_key] = formatted_entities_transcript
            st.session_state[transcription_key] = formatted_transcript
            st.session_state[completed_key] = True 

            # Initialisation de la barre de progression avec le premier message
            progress_bar = st.empty()
            simulate_progress(audio_length_sec, progress_bar, progress_messages)
            time.sleep(1)  # Pause avant de vider la barre de progression
            progress_bar.empty()  # Nettoyage de la barre de progression
            st.balloons()

        if st.session_state[completed_key] is True:  

            # Get the variables
            input = st.session_state[input_key]
            summary = st.session_state[summary_key]
            topics = st.session_state[topics_key]
            entities = st.session_state[entities_key]
            transcription = st.session_state[transcription_key]

            # Build the result
            menu = st.container(border=True)
            menu.markdown("\n\n**Results** -- :package: [Info](#info) -- :compression: [Summary](#summary) -- :memo: [Transcription](#transcription)\n\n")
            st.markdown('### Info')
            st.info(input)
   
            if summary is not None and summary.lower() != "none":
                st.markdown('### Summary')
                st.button(":clipboard: Copier le text", key=btn_copy_s1_key, on_click=notify_and_copy, args=[str(summary),'Summary'])
                st.success(summary)
            else:
                # summary_gpt = summary_transcript(transcription)
                summary = f"**Topics**\n{topics}\n\n{entities}" # f"{summary_gpt}\n\n{topics}\n\n{entities}"
                st.markdown('### Summary')
                st.button(":clipboard: Copier le text", key=btn_copy_s1_key, on_click=notify_and_copy, args=[str(summary),'Summary'])
                st.success(summary)

            st.markdown('### Transcription')
            st.button(":clipboard: Copier le text", key=btn_copy_t1_key, on_click=notify_and_copy, args=[str(transcription),'Transcription'])
            st.success(f"{transcription}\n\n---\n\n")

# API Keys
listennotes_api = st.secrets.listennotes
assemblyai_api = st.secrets.assemblyai
spotify_api_id = st.secrets.spotify.id
spotify_api_secret = st.secrets.spotify.secret

# Configuration du client ListenNotes
client = podcast_api.Client(api_key=listennotes_api)

# Configuration du client AssemblyAI pour la transcription
aai.settings.api_key = assemblyai_api
config = aai.TranscriptionConfig(
    speaker_labels=True, 
    language_detection=True, 
    summarization=True,
    summary_model=aai.SummarizationModel.conversational,
    summary_type=aai.SummarizationType.bullets,
    entity_detection=True,
    iab_categories=True
)
transcriber = aai.Transcriber(config=config)

# Configuration du client Spotify
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=spotify_api_id,client_secret=spotify_api_secret))

# Mapping des messages
progress_messages = {
    0: "Operation in progress. Please wait.",
    10: "Just getting started! Warming up our digital ears.",
    20: "Making headway! The words are beginning to take shape.",
    30: "One-third of the way through! We're in the groove now.",
    40: "Almost halfway!",
    50: "Halfway there! Now, let's see what the other half says.",
    60: "Beyond the halfway mark! It's getting really interesting.",
    70: "Getting closer! Your words are aligning beautifully.",
    80: "Homestretch! The end is near, and it looks text-tacular.",
    90: "So close! Just dotting the i's and crossing the t's.",
    100: "Voilà! Your transcription is ready to amaze."
}
messages_title = {
    'ln': "ListenNotes Podcast",
    'sp': "Spotify Podcast",
    'yt': "YouTube Video",
    'dt': "Direct Link",
}
messages_intro = {
    'ln': "Quickly access your past transcriptions from ListenNotes using the **unique ID** or by **text search**. Relive your podcast audio content through clear, structured transcriptions.",
    'sp': "Your favorite podcasts deserve to be read too. AudioScribe makes transcribing any podcast on Spotify easy, allowing you to access written content in an instant.Enter the URL of your Spotify podcast to receive a detailed and accurate transcription.",
    'yt': "Turn video content into text with precision. Whether it's for study, content, or convenience, AudioScribe makes video transcription seamless and straightforward.Get your YouTube video transcribed in just a few clicks. Simply paste the URL below.",
    'dt': "Turn audio content into text with precision. Whether it's for study, content, or convenience, AudioScribe makes audio transcription seamless and straightforward. Simply paste the URL below.",
}
messages_input = {
    'ln': "insert ID or keyword...",
    'sp': "insert Spotify podcast URL or ID...",
    'yt': "insert YouTube video URL or ID...",
    'dt': "insert audio URL...",
}

# Custom CSS to inject
tabs_font_css = """
<style>
html, body, h1, h2, h3, [class*="css"]  {
  font-family: courier, monospace !important;
}
button[data-baseweb="tab"] p {
    font-size: 1.2rem !important;
}
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stNotificationContentSuccess"] > div > div > p {
    margin-bottom:0;
}
</style>
"""
st.write(tabs_font_css, unsafe_allow_html=True)

# Variable de test : 
# ln_episode_input = c9af1e9a2cf7425c9bb60b9b15b0fd4e
# ln_episode_input = Comment rater un recrutement en 5 phases 
# ln_audio_length_sec = '481'
# ln_audio_url = 'https://www.listennotes.com/e/p/c9af1e9a2cf7425c9bb60b9b15b0fd4e/'
# ln_transcript_id = "c37b581d-791f-4d67-9402-80217eab7b37"
# https://youtu.be/gxHBAM-ww-w
# https://open.spotify.com/episode/2Jg3DWJ7LLNePNRM4SotDk?si=c99b94ee1ee741ad

# Session init
if "copied" not in st.session_state: 
    st.session_state.copied = []
if "ln_submit" not in st.session_state:
    st.session_state["ln_submit"] = False
if "yt_submit" not in st.session_state:
    st.session_state["yt_submit"] = False
if "sp_submit" not in st.session_state:
    st.session_state["sp_submit"] = False
if "dt_submit" not in st.session_state:
    st.session_state["dt_submit"] = False

# App
st.image('./assets/logo.png', width=200)
st.markdown('# Welcome to AudioScribe')
st.subheader("Bringing your audios to text")
st.markdown("AudioScribe turns your podcasts, YouTube videos, and audio into accurate, shareable text. Discover a new way to capture and utilize information. :studio_microphone:")

st.write(st.session_state)

con = st.container()
tab1, tab2, tab3, tab4 = con.tabs(["ListenNotes", "Spotify", "Youtube", "Direct"])
with tab3:
    process_tab('yt', "https://upload.wikimedia.org/wikipedia/commons/b/b8/YouTube_Logo_2017.svg", progress_messages, audio_length_sec_key='yt_audio_length_sec', audio_url_key='yt_audio_url')
with tab2:
    process_tab('sp', "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9b/Spotify_1.png/235px-Spotify_1.png", progress_messages, audio_length_sec_key='sp_audio_length_sec', audio_url_key='sp_audio_url')
    # st.warning('We are working on it!', icon="⚠️")
with tab1:
    process_tab('ln', "https://brand-assets-cdn.listennotes.com/brand-assets-listennotes-com/production/media/image-89a6b237f0974f5c13b8b8b65816c2b7.png", progress_messages, audio_length_sec_key='ln_audio_length_sec', audio_url_key='ln_audio_url')
with tab4:
    process_tab('dt', "", progress_messages, audio_length_sec_key='dt_audio_length_sec', audio_url_key='dt_audio_url')

