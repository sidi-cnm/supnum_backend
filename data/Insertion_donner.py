import psycopg2
import json
import os
from typing import Dict, Any, List

# --- CONFIGURATION DB ---
DB_CONFIG = {
    'user': os.environ.get('POSTGRES_USER', 'supnum_user'),
    'password': os.environ.get('POSTGRES_PASSWORD', 'supnum_password'),
    'host': os.environ.get('POSTGRES_HOST', 'localhost'),
    'port': os.environ.get('POSTGRES_PORT', '5432'),
    'database': os.environ.get('POSTGRES_DB', 'supnum_data')
}

JSON_FILE_PATH = 'data/specializations_supnum_v0_1.json' 
# Définir explicitement les IDs de spécialisation si le JSON ne les liste pas tous correctement
ALL_SPECIALIZATION_IDS = ['CNM', 'DSI', 'RSS'] 


# --- FONCTION PRINCIPALE ---

def run_data_migration():
    print(f"Démarrage de la migration des données à partir de {JSON_FILE_PATH}...")
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Le fichier JSON fourni n'a qu'un seul objet Specialization, nous utilisons ses sujets
        # pour déterminer les sujets de toutes les spécialisations
        specialization_data = data['specializations'][0] 
        
        # 1. Préparation des données: Extraction de tous les sujets uniques
        unique_subjects: Dict[str, Dict[str, Any]] = {}
        all_links: List[Dict[str, Any]] = []

        for semester_data in specialization_data['semesters']:
            semester_label = semester_data['label']
            
            for subject in semester_data['subjects']:
                code = subject['code']
                title = subject['title']
                credits = subject['credits']
                specialite = subject.get('specialite', 'Commun')
                
                # Enregistrement des sujets uniques (évite les doublons dans la table Subject)
                unique_subjects[code] = {
                    'code': code,
                    'title': title,
                    'credits': credits,
                    # Autres champs à ajouter si nécessaire
                }
                
                # Détermination des IDs de spécialisation pour les liens
                target_specs = []
                if specialite == 'Commun':
                    target_specs = ALL_SPECIALIZATION_IDS
                elif specialite in ALL_SPECIALIZATION_IDS:
                    target_specs = [specialite]
                
                # Création des liens
                for spec_id in target_specs:
                    all_links.append({
                        'spec_id': spec_id,
                        'code': code,
                        'semester': semester_label
                    })

        print(f"-> {len(unique_subjects)} sujets uniques identifiés.")
        print(f"-> {len(all_links)} liens SpecializationSubjects identifiés.")

        # --- ÉTAPE 2: Insertion des Sujets ---
        print("\n[Insertion dans la table Subject]...")
        for sub_data in unique_subjects.values():
            # Conversion du titre en JSONB pour l'insertion
            title_json = json.dumps({'fr': sub_data['title']}) 
            
            insert_subject_query = """
            INSERT INTO Subject (code, title_json, credits) 
            VALUES (%s, %s, %s) 
            ON CONFLICT (code) DO NOTHING;
            """
            cursor.execute(insert_subject_query, (sub_data['code'], title_json, sub_data['credits']))
        conn.commit()
        print("Insertion des sujets terminée.")

        # --- ÉTAPE 3: Insertion des Liens (SpecializationSubjects) ---
        print("\n[Insertion dans la table SpecializationSubjects]...")
        for link in all_links:
            # Récupération de l'ID numérique de la matière par son code stable
            insert_link_query = """
            INSERT INTO SpecializationSubjects (specialization_id, subject_id, semester, primary_language)
            VALUES (
                %s, 
                (SELECT id FROM Subject WHERE code = %s), 
                %s, 
                'fr'
            ) 
            ON CONFLICT DO NOTHING;
            """
            cursor.execute(insert_link_query, (link['spec_id'], link['code'], link['semester']))

        conn.commit()
        print("Insertion des liens terminée.")
        print("\n✅ Migration des données terminée avec succès. Les liaisons sont désormais fiables.")
        
    except Exception as e:
        print(f"❌ Erreur lors de la migration: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            cursor.close()
            conn.close()

if __name__ == '__main__':
    run_data_migration()