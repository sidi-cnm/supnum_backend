# embeddings.py
import json
import os
import requests
import time # NOUVEL IMPORT NÉCESSAIRE
from typing import List, Dict, Any
from dotenv import load_dotenv

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# --- CONFIGURATION CHARGÉE DEPUIS OS.ENVIRON ---
MISTRAL_API_KEY = os.environ.get('MISTRAL_API_KEY')
MISTRAL_EMBED_MODEL = os.environ.get('MISTRAL_EMBED_MODEL', 'mistral-embed') 
EMBED_URL = os.environ.get('EMBED_URL', 'https://api.mistral.ai/v1/embeddings')

INPUT_FILE_PATH = os.environ.get('CHUNKING_OUTPUT_FILE', 'output.json')
OUTPUT_FILE_PATH = os.environ.get('EMBEDDING_OUTPUT_FILE', 'embeddings_with_payload.json')
VECTOR_DIMENSION = int(os.environ.get('VECTOR_DIMENSION', 1024)) 


# --- FONCTION D'EMBEDDING VIA MISTRAL API ---
def get_mistral_embeddings(texts: List[str]) -> List[List[float]]:
    """Génère des embeddings en utilisant l'API Mistral."""
    
    if not MISTRAL_API_KEY or not EMBED_URL:
        raise ValueError("Les variables MISTRAL_API_KEY et EMBED_URL doivent être définies dans l'environnement.")
        
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": MISTRAL_EMBED_MODEL,
        "input": texts
    }
    
    response = requests.post(EMBED_URL, headers=headers, json=data)
    # response.raise_for_status() va maintenant lever une exception HTTPError pour le code 429
    response.raise_for_status() 
    
    response_json = response.json()
    return [item['embedding'] for item in response_json['data']]


# --- FONCTION PRINCIPALE AVEC LOGIQUE DE RETRY ---
def main_embeddings():
    print("Démarrage de la génération des Embeddings (via Mistral API)...")
    
    if not MISTRAL_API_KEY:
        print("❌ Erreur de configuration : MISTRAL_API_KEY n'est pas définie.")
        return

    try:
        with open(INPUT_FILE_PATH, 'r', encoding='utf-8') as f:
            chunks: List[Dict[str, Any]] = json.load(f)
        print(f"-> {len(chunks)} chunks chargés depuis {INPUT_FILE_PATH}.")
    except Exception as e:
        print(f"❌ Erreur lors du chargement de {INPUT_FILE_PATH} : {e}. Vérifiez CHUNKING_OUTPUT_FILE.")
        return

    all_points_data = []
    batch_size = 50 
    max_retries = 5         # Nombre maximum de tentatives
    initial_delay = 5       # Délai de base en secondes

    i = 0
    while i < len(chunks):
        batch = chunks[i:i + batch_size]
        texts_to_embed = [item['chunk_text'] for item in batch]
        
        current_retry = 0
        batch_processed = False
        
        while not batch_processed and current_retry < max_retries:
            try:
                print(f"  -> Génération des embeddings pour le lot {i//batch_size + 1} (Tentative {current_retry + 1}/{max_retries})...")
                vectors = get_mistral_embeddings(texts_to_embed)
                
                # Succès : Traitement des données et sortie de la boucle de retry
                for j, item in enumerate(batch):
                    all_points_data.append({
                        "id": i + j + 1, 
                        "vector": vectors[j],
                        "payload": item['metadata'] 
                    })
                
                batch_processed = True
                
            except requests.exceptions.HTTPError as http_err:
                if http_err.response.status_code == 429:
                    current_retry += 1
                    # Backoff exponentiel : 5s, 10s, 20s, 40s, etc.
                    delay = initial_delay * (2 ** (current_retry - 1)) 
                    print(f"  ⚠️ Erreur 429 (Trop de requêtes). Attente de {delay} secondes avant de réessayer...")
                    
                    if current_retry < max_retries:
                        time.sleep(delay)
                    else:
                        # Si max_retries est atteint, on arrête tout
                        print(f"❌ Échec de la tentative après {max_retries} essais. Arrêt.")
                        return
                else:
                    # Gérer les autres erreurs HTTP (400, 403, 500, etc.)
                    print(f"❌ Erreur HTTP inattendue pour le lot {i//batch_size + 1}: {http_err}")
                    print("Vérifiez la validité de votre MISTRAL_API_KEY ou l'URL.")
                    return
            except requests.exceptions.RequestException as req_err:
                # Gérer les erreurs de connexion (DNS, timeout, etc.)
                print(f"❌ Erreur de connexion pour le lot {i//batch_size + 1}: {req_err}")
                return

        if batch_processed:
            i += batch_size # Passer au lot suivant uniquement en cas de succès
        
    # Sauvegarder les embeddings
    with open(OUTPUT_FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(all_points_data, f, indent=2)
        
    print(f"\n🎉 Génération terminée. {len(all_points_data)} embeddings sauvegardés dans {OUTPUT_FILE_PATH}.")

if __name__ == '__main__':
    main_embeddings()