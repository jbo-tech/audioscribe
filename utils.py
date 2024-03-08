import re
import requests

def upload_file_url(file):
    """
    Uploads a file to a temporary storage service.

    Parameters:
    - file_path (str): The path to the file to be uploaded.

    Returns:
    - str: The response from the upload service.
    """
    # URL de l'API pour l'upload
    url = 'https://tmpfiles.org/api/v1/upload'

    try:
        # Ouvrir le fichier en mode binaire
        files = {'file': (file.name, file, file.type)}
            
        # Faire la requête POST avec le fichier
        response = requests.post(url, files=files)

        # Vérifier que la requête a réussi
        if response.status_code == 200:
            # Convertir la réponse en JSON
            response_json = response.json()
            
            # Accéder à l'URL dans la réponse JSON
            uploaded_file_page = response_json.get('data', {}).get('url', None)
            uploaded_file_url = uploaded_file_page.replace("tmpfiles.org/", "tmpfiles.org/dl/")
            
            return uploaded_file_url
        else:
            print(f"Failed to upload file. Status code: {response.status_code}")
            return None
    except Exception as e:
        # Gérer les exceptions, par exemple si le fichier n'existe pas
        return f"An error occurred: {e}"

def sanitize_folder_name(folder_name):
    return re.sub(r'[<>:"/\\|?*\']+', '_', folder_name)

def convert_time_format(secondes_input):
    """
    Convertit un nombre de secondes en un format précis incluant les heures, minutes et secondes.
    
    Args:
    - secondes (int): Le nombre de secondes à convertir.
    
    Returns:
    - str: Le temps converti en un format "Xh Ymin Zs", en incluant seulement les unités nécessaires.
    """
    # Assurer que l'input est un entier
    secondes = int(secondes_input)

    # Calcul des heures, minutes et secondes
    heures = secondes // 3600
    minutes = (secondes % 3600) // 60
    secondes_restantes = secondes % 60

    # Construction de la chaîne de sortie
    time_format = ""
    if heures > 0:
        time_format += f"{heures} h "
    if minutes > 0 or heures > 0:  # Inclure les minutes si on a des heures même si minutes est 0
        time_format += f"{minutes} min "
    if minutes > 0 or heures > 0 or secondes_restantes > 0:  # Inclure les minutes si on a des heures même si minutes est 0
        time_format += f"{secondes_restantes} s"

    return time_format.strip()

# Fonction pour insérer des espaces dans les mots CamelCase/PascalCase
def insert_spaces(word):
    # Insère un espace avant chaque lettre majuscule sauf si c'est la première lettre ou précédée d'une majuscule
    spaced = re.sub(r'(?<!^)(?<! [A-Z])(?=[A-Z])', ' ', word)
    # Gère les cas où plusieurs majuscules sont consécutives sans minuscules (ex: HTML, UFO)
    spaced = re.sub(r'(?<=[A-Z])(?=[A-Z][a-z])', ' ', spaced)
    # Remplace les caractères '&'
    spaced = spaced.replace('&', ' &')
    return spaced

def youtube_url_is_playlist(url):
    # Regex pour une URL de playlist YouTube
    playlist_pattern = r'https://(www\.)?youtube\.com/playlist\?list=[\w-]+'
    # Regex pour une URL de vidéo YouTube (forme classique)
    video_pattern_classic = r'https://(www\.)?youtube\.com/watch\?v=[\w-]+'
    # Regex pour une URL de vidéo YouTube (forme raccourcie)
    video_pattern_short = r'https://youtu\.be/[\w-]+'

    if re.match(playlist_pattern, url):
        return True
    elif re.match(video_pattern_classic, url) or re.match(video_pattern_short, url):
        return False
    else:
        return False