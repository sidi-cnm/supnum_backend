# indexing.py
import json
import os
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import Distance, VectorParams
from typing import List, Dict, Any
from dotenv import load_dotenv

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# --- CONFIGURATION CHARGÉE DEPUIS OS.ENVIRON ---
# Variables de connexion Qdrant
QDRANT_HOST = os.environ.get('QDRANT_HOST') 
QDRANT_API_KEY = os.environ.get('QDRANT_API_KEY') 

# Variables de configuration de la collection/fichiers
COLLECTION_NAME = os.environ.get('QDRANT_COLLECTION_NAME', 'supnum_curriculum')
INPUT_FILE_PATH = os.environ.get('EMBEDDING_OUTPUT_FILE', 'embeddings_with_payload.json')
# La dimension (1024) DOIT correspondre à celle du modèle 'mistral-embed'
VECTOR_DIMENSION = int(os.environ.get('VECTOR_DIMENSION', 1024)) 

print("QDRANT_HOST:", QDRANT_HOST)
print("QDRANT_API_KEY:", "****" , QDRANT_API_KEY)
print("COLLECTION_NAME:", COLLECTION_NAME)
print("INPUT_FILE_PATH:", INPUT_FILE_PATH)
print("VECTOR_DIMENSION:", VECTOR_DIMENSION)


# --- FONCTION PRINCIPALE ---
def main_indexing():
    print("Démarrage de l'indexation Qdrant...")
    
    # 1. Vérification des variables essentielles
    if not QDRANT_HOST or not QDRANT_API_KEY:
        print("❌ Erreur de configuration : QDRANT_HOST et QDRANT_API_KEY doivent être définis.")
        return
        
    # 2. Connexion à Qdrant
    try:
        # Le client utilise l'URL et la clé API pour se connecter au service Cloud
        qdrant_client = QdrantClient(url=QDRANT_HOST, api_key=QDRANT_API_KEY , timeout=60)
        print(f"Connexion établie à Qdrant Host: {QDRANT_HOST}")
    except Exception as e:
        print(f"❌ Erreur de connexion à Qdrant : {e}")
        return

    # 3. Charger les embeddings et payloads
    try:
        with open(INPUT_FILE_PATH, 'r', encoding='utf-8') as f:
            # all_points_data contient : [{"id": 1, "vector": [...], "payload": {...}}, ...]
            all_points_data: List[Dict[str, Any]] = json.load(f)
        print(f"-> {len(all_points_data)} points chargés depuis {INPUT_FILE_PATH}.")
    except Exception as e:
        print(f"❌ Erreur lors du chargement de {INPUT_FILE_PATH} : {e}. Vérifiez EMBEDDING_OUTPUT_FILE.")
        return
    
    # 4. Création/reconstruction de la Collection Qdrant
    print(f"Tentative de recréer la collection '{COLLECTION_NAME}'...")
    qdrant_client.recreate_collection(
        collection_name=COLLECTION_NAME,
        # La Distance Cosine est standard pour les embeddings Mistral
        vectors_config=VectorParams(size=VECTOR_DIMENSION, distance=Distance.COSINE),
    )
    print(f"Collection '{COLLECTION_NAME}' prête avec dimension {VECTOR_DIMENSION}.")

    # 5. Préparation des PointStructs pour Qdrant
    # Nous itérons sur les données chargées pour créer les objets PointStruct nécessaires à l'API Qdrant.
    points_to_upsert = [
        models.PointStruct(
            id=data['id'], 
            vector=data['vector'], 
            payload=data['payload'] # Le payload contient les métadonnées utiles (spécialité, semestre, etc.)
        )
        for data in all_points_data
    ]
    print(f"Démarrage de l'insertion de {len(points_to_upsert)} points...")

    # 6. Indexation (Upsert)
    # L'Upsert insère de nouveaux points ou met à jour les points existants.
    qdrant_client.upsert(
        collection_name=COLLECTION_NAME,
        wait=True, # Attendre la fin de l'opération
        points=points_to_upsert,

    )
    
    # 7. Vérification finale
    count_result = qdrant_client.count(collection_name=COLLECTION_NAME, exact=True)
    print(f"\n🎉 Indexation complète ! Total de {count_result.count} points stockés dans la collection '{COLLECTION_NAME}' sur Qdrant Cloud.")


if __name__ == '__main__':
    main_indexing()