import re

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