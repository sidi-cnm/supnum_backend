import os
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# --- CONFIGURATION ---
QDRANT_HOST = os.environ.get('QDRANT_HOST') 
QDRANT_API_KEY = os.environ.get('QDRANT_API_KEY') 
COLLECTION_NAME = os.environ.get('QDRANT_COLLECTION_NAME', 'supnum_curriculum')
VECTOR_DIMENSION = int(os.environ.get('VECTOR_DIMENSION', 1024))
TOP_K = 5 # Nombre de documents (chunks) à récupérer

# --- SIMULATION DU MODÈLE D'EMBEDDING ---
# ATTENTION : Remplacez ceci par l'appel réel à votre modèle Mistral (par exemple, via un service d'API).
def get_query_embedding(query_text: str) -> list:
    """
    Génère l'embedding de la requête en utilisant le modèle 'mistral-embed'.
    
    Vous DEVEZ remplacer le corps de cette fonction par l'appel à votre modèle.
    Ici, nous simulons la création d'un vecteur de dimension 1024 (pour tester le client Qdrant).
    """
    print(f"\n[INFO] Génération de l'embedding pour: '{query_text}'...")
    # Simulation d'un vecteur aléatoire de 1024 dimensions
    # Vous DEVEZ remplacer ceci par l'appel réel à l'API du modèle!
    return np.random.rand(VECTOR_DIMENSION).tolist() 


# --- FONCTION DE RECHERCHE PRINCIPALE ---
def search_documents(query_text: str):
    """Effectue la recherche vectorielle dans Qdrant."""
    
    # 1. Vérification des variables essentielles
    if not QDRANT_HOST or not QDRANT_API_KEY:
        print("❌ Erreur de configuration : QDRANT_HOST et QDRANT_API_KEY doivent être définis.")
        return
    
    # 2. Connexion à Qdrant (ajustez le timeout si besoin)
    try:
        qdrant_client = QdrantClient(url=QDRANT_HOST, api_key=QDRANT_API_KEY, timeout=30)
        print(f"[INFO] Connexion établie à Qdrant Host: {QDRANT_HOST}")
    except Exception as e:
        print(f"❌ Erreur de connexion à Qdrant : {e}")
        return

    # 3. Obtenir l'embedding de la requête
    query_vector = get_query_embedding(query_text)
    
    if len(query_vector) != VECTOR_DIMENSION:
        print(f"❌ Erreur : Dimension de l'embedding ({len(query_vector)}) incorrecte. Attendue : {VECTOR_DIMENSION}.")
        return

    # 4. Recherche Vectorielle (k-Nearest Neighbors)
    print(f"[INFO] Démarrage de la recherche des {TOP_K} plus proches voisins...")
    
    try:
        search_result = qdrant_client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            limit=TOP_K,             # Nombre de résultats souhaités
            with_payload=True,       # Inclure les métadonnées (payload)
            with_vectors=False,      # N'inclure pas les vecteurs complets dans le résultat
        )
        
        print("\n--- 🎯 Résultats de la Recherche dans Qdrant ---")
        if not search_result:
            print("Aucun résultat trouvé.")
            return

        for i, hit in enumerate(search_result):
            # Le 'payload' contient la métadonnée et le 'chunk_text'
            chunk_text = hit.payload.get('chunk_text', 'N/A')
            metadata = {k: v for k, v in hit.payload.items() if k != 'chunk_text'}
            
            print(f"\n#{i+1} (Score: {hit.score:.4f})")
            print(f"Contenu (Chunk): {chunk_text}")
            print(f"Métadonnées: {metadata}")
            
    except Exception as e:
        print(f"❌ Erreur lors de la recherche Qdrant : {e}")


# --- EXÉCUTION ---
if __name__ == '__main__':
    # Exemple de requête :
    test_query = "Quels sont les objectifs de la spécialisation en Cybersécurité et Réseaux ?"
    
    search_documents(test_query)