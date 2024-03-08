import streamlit as st
import streamlit.components.v1 as components
from streamlit import session_state as ss
import time
import re
import json
from datetime import datetime
from listennotes import podcast_api
import assemblyai as aai
import yt_dlp
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from utils import (
    upload_file_url,
    sanitize_folder_name,
    convert_time_format,
    insert_spaces,
    youtube_url_is_playlist
)

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

def determine_service_to_data(text):
    # Enlever les espaces avant et après la chaîne
    text = text.strip() 
    # Patterns pour identifier les IDs de service
    listen_notes_id_pattern = r"^[a-f0-9]{32}$"
    youtube_id_pattern = r"^[a-zA-Z0-9_-]{11}$"
    spotify_id_pattern = r"^[A-Za-z0-9]{22}$"
    # YouTube et Spotify dans l'URL
    youtube_url_pattern = r"(youtu\.be\/|youtube\.com\/watch\?v=)([a-zA-Z0-9_-]{11})"
    spotify_url_pattern = r"spotify\.com\/episode\/([A-Za-z0-9]{22})"
    # Vérification des URLs YouTube et Spotify
    youtube_match = re.search(youtube_url_pattern, text)
    spotify_match = re.search(spotify_url_pattern, text)

    # Listen Notes
    if re.match(listen_notes_id_pattern, text):
        data = listennotes_get_data_by_id(text)
        service_code = "ln"
    # YouTube direct ID
    elif re.match(youtube_id_pattern, text):
        data = youtube_get_data_by_url(f"https://www.youtube.com/watch?v={text}")
        service_code = "yt"        
    # Spotify direct ID
    elif re.match(spotify_id_pattern, text):
        data = spotify_get_data_by_id(text)
        service_code = "sp"
    # YouTube URL
    elif youtube_match:
        data = youtube_get_data_by_url(text)
        service_code = "yt"
    # Spotify URL
    elif spotify_match:
        spotify_id = spotify_match.group(1)
        data = spotify_get_data_by_id(spotify_id) 
        service_code = "sp"    
    # Direct link
    elif text.startswith("http") and not youtube_match and not spotify_match:
        data = {
            'title': 'Not available',
            'link': 'Not available',
            'audio': text,
            'audio_length_sec': "60",
        }
        service_code = "dt"
    # Par défaut, considérez tout autre texte comme une recherche Listen Notes
    else:
        data = listennotes_get_data_by_search(text)
        service_code = "ln"

    return (service_code, data)

def listennotes_get_data_by_id(episode_id):
    response = client.fetch_episode_by_id(
        id=episode_id,
        show_transcript=1,
    )
    data = response.json()
    #ln_audio_url = data['audio']
    data = {
        'title': data['title'],
        'link': data['link'],
        'audio': data['audio'],
        'audio_length_sec': data['audio_length_sec'],
    }
    return data

def listennotes_get_data_by_search(episode_keyword):
    # Effectue une recherche d'épisode de podcast avec les critères spécifiés
    response = client.search(
        q=episode_keyword,
        sort_by_date=0,
        type='episode',
        offset=0,
        len_min=3,
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
        data = {
            'title': data['title'],
            'link': data['link'],
            'audio': data['audio'],
            'audio_length_sec': data['audio_length_sec'],
        }
        return data
    else:
        print("Pas de réponse.")
        exit(1)  # Arrête l'exécution si aucun résultat n'est trouvé

def youtube_get_data_by_url(url):
    """
    https://github.com/yt-dlp/yt-dlp/blob/5fb450a64c300056476cfef481b7b5377ff82d54/yt_dlp/YoutubeDL.py
    Extrait l'URL de l'audio au format m4a d'une vidéo YouTube spécifiée par son URL.
    :param URL (str): L'URL de la vidéo YouTube dont on souhaite extraire l'audio.
    """
    try:
        with yt_dlp.YoutubeDL() as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        print("Erreur lors de l'extraction des informations de la vidéo:", e)
        print ("caught: {}".format(error))
        return "stop"  # Retourne "stop" si une erreur est capturée

    url_audio = None
    #print(json.dumps(info, indent=4))
    for format in info["formats"][::-1]:  # Parcours des formats en commençant par la fin
        if format["resolution"] == "audio only" and format["ext"] == "m4a":
            url_audio = format["url"]
            break
    data = {
        'title': info['title'],
        'link': url,
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
    ss.copied.append(text)

def disabled_submit_button_step_2():
    ss.disable_button_step_2 = not(ss.disable_button_step_2)

def process_step_3_playlist(audio_url, **kwargs):
    print("playlist")

def simulate_progress(audio_length_sec, progress_bar, progress_messages):
    """
    Simulates progress based on audio length and updates a progress bar with custom messages.
    :param ln_audio_length_sec: Length of the audio in seconds.
    :param progress_bar: The progress bar object to update.
    :param progress_messages: A dictionary containing custom messages for specific progress percentages.
    """
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    print("simulate start " + current_time)
    time_increment = float(audio_length_sec) * 0.08 / 100
    time_total = float(audio_length_sec) * 0.08
    initial_text = progress_messages[0]
    if ss.completed:
        progress_bar.progress(100, text=f":sparkles: Waiting time : 0 s\n\nVoilà! Your transcription is ready!")
    else:
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
        time.sleep(1)  # Pause avant de vider la barre de progression
        #progress_bar.empty()  # Nettoyage de la barre de progression
        st.balloons()

def simulate_progress_time(audio_length_sec):
    time_total = float(audio_length_sec) * 0.08
    while time_total > 0:
        print(time_total)
        time.sleep(1)  # Simulation d'un travail en cours
        ss.audio_length_sec_left = time_total
        time_total = time_total - 1

def process_transcription(audio_url, audio_title, audio_link):
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    print("process start " + current_time)
    # Initialise output
    output = ""
    # Retrieve id of transcription response from AssemblyAI
    transcript_id = transc_send(ss.audio_url)
    # Get the transcription
    transcript = transc_get(transcript_id)
    # Transcription by speaker
    text = speaker_transcript(transcript)
    topics = topic_transcript(transcript)
    entities = entity_transcript(transcript)
    summary = transcript.summary
    # Session logic
    output += f"""
###
Titre:\n
{audio_title.strip()}
###
URL:\n
{audio_link}
###
Summary:\n
{summary if summary is not None else 'Not Available'}
###
Transcription:\n
{text}
###
Topics:\n
{topics if topics is not None else 'Not Available'}
###
Entities:\n
{entities if entities is not None else 'Not Available'}
###
    """
    ss.transcription_result = output
    ss.completed = True

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
    100: "Voilà! Your transcription is ready!"
}
service_title = {
    'ln': "ListenNotes Podcast",
    'sp': "Spotify Podcast",
    'yt': "YouTube Video",
    'dt': "Direct Link",
}
service_intro = {
    'ln': "Quickly access your past transcriptions from ListenNotes using the **unique ID** or by **text search**. Relive your podcast audio content through clear, structured transcriptions.",
    'sp': "Your favorite podcasts deserve to be read too. AudioScribe makes transcribing any podcast on Spotify easy, allowing you to access written content in an instant.Enter the URL of your Spotify podcast to receive a detailed and accurate transcription.",
    'yt': "Turn video content into text with precision. Whether it's for study, content, or convenience, AudioScribe makes video transcription seamless and straightforward.Get your YouTube video transcribed in just a few clicks. Simply paste the URL below.",
    'dt': "Turn audio content into text with precision. Whether it's for study, content, or convenience, AudioScribe makes audio transcription seamless and straightforward. Simply paste the URL below.",
}
service_input = {
    'ln': "insert ID or keyword...",
    'sp': "insert Spotify podcast URL or ID...",
    'yt': "insert YouTube video URL or ID...",
    'dt': "insert audio URL...",
}
service_logo = {
    'ln': "https://brand-assets-cdn.listennotes.com/brand-assets-listennotes-com/production/media/image-89a6b237f0974f5c13b8b8b65816c2b7.png",
    'sp': "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9b/Spotify_1.png/235px-Spotify_1.png",
    'yt': "https://upload.wikimedia.org/wikipedia/commons/b/b8/YouTube_Logo_2017.svg",
    'dt': "",
}
multi = '''
Here are the currently functional services:
- Listen Notes 🎧 : ID, Search
- Spotify 🟢 : ID, URL
- YouTube 📺 : ID, URL
- File  : Upload
'''

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
[data-testid="stHorizontalBlock"] [data-testid="column"] + [data-testid="column"] [data-testid="stVerticalBlockBorderWrapper"] [data-testid="element-container"] > div.row-widget.stButton {
    text-align : right !important;
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

# Initialize session state variables if they don't exist
if 'file_uploaded' not in ss:
    ss.file_uploaded = False
if 'processing' not in ss:
    ss.processing = False
if 'step_1_ok' not in ss:
    ss.step_1_ok = False
if 'step_2_ok' not in ss:
    ss.step_2_ok = False
if "completed" not in ss:
    ss.completed = False
if 'disable_button_step_2'not in ss:
    ss.disable_button_step_2 = True
if 'transcription_result' not in ss:
    ss.transcription_result = ""
if "copied" not in ss: 
    ss.copied = []

# App Header
st.image('./assets/logo.png', width=200)
st.markdown('# Welcome to AudioScribe')
st.subheader("Bringing your audios to text")
st.markdown("AudioScribe turns your podcasts, YouTube videos, and audio into accurate, shareable text. Discover a new way to capture and utilize information. :studio_microphone:")
st.markdown(multi)

# st.write(ss)

# Step 1: Input Field
st.markdown('### Step 1 : Upload or Enter Information')
with st.form(key="input_form"):
    file = st.file_uploader("Drop your file here or click to select.", type=['mp3', 'mp4', 'wav'])
    input = st.text_input("Paste the URL, ID, or search term for your podcast (Listen Notes, Spotify) or video (YouTube) here.")
    step_1_warning = st.empty
    # Handling file or URL input
    if file:
        ss.file_uploaded = True
    else:
        ss.file_uploaded = False
    # Bouton de soumission
    submit_button = st.form_submit_button(label=':memo: Start Transcription', type='primary')
    if submit_button:
        errors = []
        if file is None and input == "":
            errors.append(":eyes: Please upload a file or enter a information to start.")
        if errors:
            for error in errors:
                st.error(error)
        else:
            if file is not None:
                file_details = {
                    "filename":file.name, 
                    "filetype":file.type,          
                    "filesize":file.size
                }
                input = upload_file_url(file)
                #print(input)
            time.sleep(1)
            ss.completed = False
            ss.step_1_ok = True
            ss.input_key = input

# Step 2: Source Confirmation
if ss.step_1_ok:
    st.divider()
    st.markdown('### Step 2 : Source Confirmation')
    if youtube_url_is_playlist(ss.input_key):
        print('Playlist Step 2')
    else:
        analysis = determine_service_to_data(ss.input_key)
        data = analysis[1]
        service_code = analysis[0]
        audio_title = data['title']
        audio_link = data['link']
        audio_length_sec = data['audio_length_sec']
        audio_url = data['audio']
        # Save into state_session
        ss.audio_length_sec = audio_length_sec
        ss.audio_url = audio_url
        ss.audio_title = audio_title
        ss.audio_link = audio_link
        # Layout
        if service_logo[service_code]:
            st.markdown(f'You have selected: {service_title.get(service_code, "Service not recognized")} as source. Is this correct? <img  style="float: inline-end;" src="{service_logo[service_code]}" width="auto" height="25"/>', unsafe_allow_html=True)
        else:
            st.markdown(f'You have selected: {service_title.get(service_code, "Service not recognized")} as source. Is this correct?', unsafe_allow_html=True)
        with st.container(border=True):
            on = st.toggle('Yes',key="input_confirm", on_change=disabled_submit_button_step_2)
            st.warning('Make sure this is the correct data or file before confirming.')            
            button_step_2 = st.button(label='I confirm, start transcription!', type='primary', disabled=ss.disable_button_step_2)
            if button_step_2:
                ss.step_2_ok = True
                ss.processing = True

# Step 3: Start Analysis
if ss.step_2_ok:
    st.divider()
    st.markdown('### Step 3 : Start Analysis')
    #progress_bar = st.empty()
    #simulate_progress(ss.audio_length_sec, progress_bar, progress_messages)
    #simulate_progress_time(ss.audio_length_sec)
    if ss.completed == False:
        with st.spinner(f':sparkles: Waiting time : {convert_time_format(ss.audio_length_sec)}'):
            response = process_transcription(ss.audio_url, ss.audio_title, ss.audio_link)
    
# Step 4: Displaying Results
if ss.completed:
    st.markdown("Voilà! Your transcription is ready!")
    st.divider()
    st.markdown('### Step 4 : Transcription Complete!')
    st.markdown("You can now copy or share your transcription.")
    col1, col2 = st.columns(2)
    with col1:
        btn_copy = st.button(":clipboard: Copy Transcription", key="btn_copy", on_click=notify_and_copy, args=[str(ss.transcription_result),'Transcription'])
        #if btn_copy:
        #    st.write("Functionality to copy the text.")
    with col2:
        btn_share = st.button(":popcorn: Share", key="btn_share", on_click=notify_and_copy, args=[str(ss.transcription_result),'Transcription'])
        #if btn_share:
        #    st.write("Options to share the transcription.")
    st.success(f"{ss.transcription_result}\n\n")

# Reset the app state
if ss.completed:
    if st.button("Reset"):
        for key in ss.keys():
            del ss[key]
        st.experimental_rerun()