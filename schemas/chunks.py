import psycopg2
import json
from typing import List, Dict, Any
import os

# =========================================================================
# Configuration de la base de données (À ADAPTER AVEC os.environ)
# =========================================================================

# NOTE : Dans un environnement de production (comme Docker), il est préférable
# d'utiliser os.environ.get pour récupérer les variables d'environnement.
# Remplacez les valeurs par défaut si nécessaire pour les tests locaux.
DB_CONFIG = {
    'user': os.environ.get('POSTGRES_USER', 'supnum_user'),
    'password': os.environ.get('POSTGRES_PASSWORD', 'supnum_password'),
    'host': os.environ.get('POSTGRES_HOST', 'localhost'),
    'port': os.environ.get('POSTGRES_PORT', '5432'),
    'database': os.environ.get('POSTGRES_DB', 'supnum_data')
}

# =========================================================================
# Fonctions d'accès à la base de données
# (Aucun changement dans ces fonctions)
# =========================================================================

def get_db_connection():
    """Établit et retourne une connexion PostgreSQL."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Erreur de connexion à la base de données: {e}")
        return None

def fetch_specializations(conn) -> List[Dict[str, Any]]:
    """Récupère les données de spécialisation pour le découpage."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name_json, overview_json
        FROM Specialization;
    """)
    records = cursor.fetchall()
    # print("records specialisation : " , records)

    OUTPUT_FILENAME = 'specialization_output.json'
    try:
        with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as f:
                # Utiliser ensure_ascii=False pour sauvegarder correctement les caractères non-ASCII (Français, Arabe)
                json.dump(records, f, indent=2, ensure_ascii=False)
                print(f"✅ Sauvegarde terminée avec succès. Le fichier {OUTPUT_FILENAME} est prêt.")
    except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde du fichier JSON: {e}")
    cursor.close()
    
    specializations = []
    for id, name_json_raw, overview_json_raw in records:
        name_json = name_json_raw if isinstance(name_json_raw, dict) else json.loads(name_json_raw)
        overview_json = overview_json_raw if isinstance(overview_json_raw, dict) else json.loads(overview_json_raw)
        
        specializations.append({
            'id': id,
            'name_fr': name_json.get('fr', 'N/A'),
            'overview_fr': overview_json.get('fr', 'N/A'),
            'overview_ar': overview_json.get('ar', 'N/A')
        })
    return specializations

def fetch_subjects_and_links(conn) -> List[Dict[str, Any]]:
    """Récupère les sujets avec le contexte de spécialisation/semestre."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            s.code,
            s.title_json,
            s.credits,
            ss.specialization_id,
            ss.semester
        FROM
            Subject s
        JOIN
            SpecializationSubjects ss ON s.id = ss.subject_id;
    """)
    records = cursor.fetchall()
    # print("records subject : " , records)
    OUTPUT_FILENAME = 'specialization_subjects_output.json'
    try:
        with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as f:
                # Utiliser ensure_ascii=False pour sauvegarder correctement les caractères non-ASCII (Français, Arabe)
                json.dump(records, f, indent=2, ensure_ascii=False)
                print(f"✅ Sauvegarde terminée avec succès. Le fichier {OUTPUT_FILENAME} est prêt.")
    except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde du fichier JSON: {e}")
    cursor.close()

    subjects = []
    for code, title_json_raw, credits, spec_id, semester in records:
        title_json = title_json_raw if isinstance(title_json_raw, dict) else json.loads(title_json_raw)

        subjects.append({
            'code': code,
            'title_fr': title_json.get('fr', 'N/A'),
            'credits': credits,
            'specialization_id': spec_id,
            'semester': semester
        })
    return subjects

# =========================================================================
# Fonctions de Chunking Sémantique
# (Aucun changement dans cette fonction)
# =========================================================================

def create_chunks(data_type: str, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Crée des chunks sémantiques (texte + métadonnées) à partir des données extraites.
    """
    chunks = []
    
    if data_type == 'specialization':
        for spec in data:
            # Chunk 1: Description en Français
            chunk_fr = {
                "chunk_text": (
                    f"Spécialisation: {spec['id']} ({spec['name_fr']}). "
                    f"Objectif de la spécialisation: {spec['overview_fr']}"
                ),
                "metadata": {
                    "type": "specialization_overview",
                    "id": spec['id'],
                    "name_fr": spec['name_fr'],
                    "lang": "fr"
                }
            }
            chunks.append(chunk_fr)

            # Chunk 2: Description en Arabe
            chunk_ar = {
                "chunk_text": (
                    f"التخصص: {spec['id']}. النظرة العامة: {spec['overview_ar']}"
                ),
                "metadata": {
                    "type": "specialization_overview",
                    "id": spec['id'],
                    "name_fr": spec['name_fr'], 
                    "lang": "ar"
                }
            }
            chunks.append(chunk_ar)
            
    elif data_type == 'subject_link':
        for sub in data:
            # Chunk de matière : inclut le contexte Spécialisation + Semestre
            chunk = {
                "chunk_text": (
                    f"Programme d'études: Spécialisation {sub['specialization_id']} (Semestre {sub['semester']}). "
                    f"Matière: {sub['code']} - {sub['title_fr']}. "
                    f"Crédits ECTS: {sub['credits']}."
                ),
                "metadata": {
                    "type": "subject_in_program",
                    "subject_code": sub['code'],
                    "subject_title_fr": sub['title_fr'],
                    "specialization_id": sub['specialization_id'],
                    "semester": sub['semester'],
                    "credits": sub['credits']
                }
            }
            chunks.append(chunk)

    return chunks

# =========================================================================
# Fonction principale
# =========================================================================

def run_chunking() -> List[Dict[str, Any]]:
    """Fonction principale pour exécuter l'extraction de données et la création de chunks."""
    print("Démarrage du processus de Semantic Chunking...")
    conn = get_db_connection()
    if conn is None:
        return []

    try:
        # 1. Découpage des aperçus des spécialisations
        spec_data = fetch_specializations(conn)
        print(f"-> {len(spec_data)} spécialisations récupérées.")
        spec_chunks = create_chunks('specialization', spec_data)

        # 2. Découpage des liens de matières (avec contexte Spécialisation/Semestre)
        subject_link_data = fetch_subjects_and_links(conn)
        print(f"-> {len(subject_link_data)} liens de matière (contexte) récupérés.")
        subject_link_chunks = create_chunks('subject_link', subject_link_data)

        all_chunks = spec_chunks + subject_link_chunks
        print(f"-> Total de {len(all_chunks)} chunks sémantiques créés.")
        return all_chunks

    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    OUTPUT_FILENAME = 'output.json'
    
    # 1. Exécuter le chunking
    chunks_to_embed = run_chunking()
    
    # 2. Sauvegarder le résultat dans un fichier JSON
    if chunks_to_embed:
        print(f"\nSauvegarde de {len(chunks_to_embed)} chunks dans le fichier {OUTPUT_FILENAME}...")
        try:
            with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as f:
                # Utiliser ensure_ascii=False pour sauvegarder correctement les caractères non-ASCII (Français, Arabe)
                json.dump(chunks_to_embed, f, indent=2, ensure_ascii=False)
            print(f"✅ Sauvegarde terminée avec succès. Le fichier {OUTPUT_FILENAME} est prêt.")
        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde du fichier JSON: {e}")
    else:
        print("\nAucun chunk n'a été généré. Vérifiez la connexion à la base de données et le contenu des tables.")