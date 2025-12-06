# chunking.py
import json
import os # Importation de 'os' pour les variables d'environnement

# --- CONFIGURATION CHARGÉE DEPUIS OS.ENVIRON ---
# Variables pour les chemins de fichiers (avec valeurs par défaut)
JSON_FILE_PATH = os.environ.get('JSON_SOURCE_FILE', 'data/specializations_supnum_v0_1.json') 
OUTPUT_FILE_PATH = os.environ.get('CHUNKING_OUTPUT_FILE', 'output.json') 

# Constante de projet (peut être gardée en dur)
ALL_SPECIALIZATION_IDS = ['CNM', 'DSI', 'RSS'] 


def create_chunks(data: dict) -> list:
    """Génère des chunks textuels et leurs métadonnées à partir des données structurées."""
    chunks = []
    
    # ... (Le reste de la logique de chunking reste inchangé) ...
    # Début du reste de la logique (copier/coller le code de la partie 1 précédente)
    for spec in data['specializations']:
        spec_id = spec['id']
        spec_name_fr = spec['name']
        overview_fr = spec['overview']
        overview_ar = spec.get('overview_ar', f"النظرة العامة: {spec_name_fr}") 

        # 1. Chunking des aperçus de spécialisation (FR)
        if overview_fr:
            chunks.append({
                "chunk_text": f"Spécialisation: {spec_id} ({spec_name_fr}). Objectif de la spécialisation: {overview_fr}",
                "metadata": {
                    "type": "specialization_overview",
                    "id": spec_id,
                    "name_fr": spec_name_fr,
                    "lang": "fr"
                }
            })
        
        # 2. Chunking des aperçus de spécialisation (AR)
        if overview_ar:
            chunks.append({
                "chunk_text": f"التخصص: {spec_id}. النظرة العامة: {overview_ar}",
                "metadata": {
                    "type": "specialization_overview",
                    "id": spec_id,
                    "name_fr": spec_name_fr,
                    "lang": "ar"
                }
            })
            
        # 3. Chunking des matières par semestre
        for semester_data in spec['semesters']:
            semester_label = semester_data['label']
            
            for subject in semester_data['subjects']:
                subject_code = subject['code']
                subject_title_fr = subject['title']
                credits = subject['credits']
                specialite = subject.get('specialite', 'Commun') 

                target_specs = []
                if specialite == 'Commun':
                    target_specs = ALL_SPECIALIZATION_IDS
                elif specialite in ALL_SPECIALIZATION_IDS:
                    target_specs = [specialite]
                
                for target_spec_id in target_specs:
                    chunk = {
                        "chunk_text": f"Programme d'études: Spécialisation {target_spec_id} (Semestre {semester_label}). Matière: {subject_code} - {subject_title_fr}. Crédits ECTS: {credits}.",
                        "metadata": {
                            "type": "subject_in_program",
                            "subject_code": subject_code,
                            "subject_title_fr": subject_title_fr,
                            "specialization_id": target_spec_id,
                            "semester": semester_label,
                            "credits": credits
                        }
                    }
                    chunks.append(chunk)

    return chunks
    # Fin de la logique

def main_chunking():
    print(f"Démarrage du chunking. Source: {JSON_FILE_PATH}")
    if not os.path.exists(JSON_FILE_PATH):
        print(f"❌ Erreur : Fichier source non trouvé à {JSON_FILE_PATH}. Vérifiez JSON_SOURCE_FILE.")
        return

    try:
        with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        all_chunks = create_chunks(data)
        
        with open(OUTPUT_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(all_chunks, f, indent=2, ensure_ascii=False)
            
        print(f"🎉 Chunking terminé. {len(all_chunks)} chunks sauvegardés dans {OUTPUT_FILE_PATH}")
        
    except json.JSONDecodeError:
        print(f"❌ Erreur : Le fichier JSON à {JSON_FILE_PATH} est mal formé.")
    except Exception as e:
        print(f"❌ Une erreur inattendue s'est produite lors du chunking : {e}")

if __name__ == '__main__':
    main_chunking()