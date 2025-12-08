# Chatbot SupNum - RAG Implementation

## 🚀 Vue d'ensemble

Un système de chatbot intelligent basé sur RAG (Retrieval-Augmented Generation) pour SupNum. Le système combine :
- **PostgreSQL** pour le stockage des documents et métadonnées
- **Qdrant** pour la recherche vectorielle
- **Sentence Transformers** pour les embeddings
- **OpenAI/Claude** pour la génération de réponses
- **FastAPI** pour l'API REST

## 📋 Architecture

```
┌──────────────┐
│   Question   │
└──────┬───────┘
       │
       v
┌──────────────────────┐
│   Query Handler      │
│  - Encode question   │
│  - Search Qdrant     │
│  - Generate answer   │
└──────┬───────────────┘
       │
       ├─────────────────────┐
       │                     │
       v                     v
┌──────────────┐      ┌──────────────┐
│   Qdrant     │      │  PostgreSQL  │
│  (Vectors)   │      │  (Metadata)  │
└──────────────┘      └──────────────┘
       │                     │
       └─────────┬───────────┘
                 │
                 v
          ┌──────────────┐
          │  LLM (GPT)   │
          │  - Context   │
          │  - Generate  │
          └──────────────┘
```

## 🛠️ Installation

### 1. Prérequis
- Python 3.11+
- Docker et Docker Compose
- Git

### 2. Cloner le projet
```bash
git clone <your-repo>
cd chatbot-supnum
```

### 3. Configuration
```bash
# Copier le fichier d'exemple
cp .env.example .env

# Éditer .env avec vos clés API
nano .env
```

### 4. Lancer avec Docker
```bash
# Démarrer tous les services
docker-compose up -d

# Vérifier les logs
docker-compose logs -f app

# Initialiser la base de données
curl -X POST http://localhost:8000/init-db
```

### 5. Installation locale (sans Docker)
```bash
# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt

# Démarrer PostgreSQL et Qdrant (via Docker)
docker-compose up -d postgres qdrant

# Lancer l'application
uvicorn app.main:app --reload
```

## 📚 Utilisation de l'API

### 1. Indexer un document
```bash
curl -X POST "http://localhost:8000/documents" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Guide SupNum",
    "content": "SupNum est une école spécialisée dans le numérique...",
    "source": "https://supnum.mr",
    "doc_type": "text"
  }'
```

### 2. Poser une question
```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Qu'\''est-ce que SupNum?",
    "top_k": 5,
    "score_threshold": 0.5,
    "use_context": true
  }'
```

### 3. Rechercher des chunks
```bash
curl -X POST "http://localhost:8000/search?query=formation&top_k=10"
```

### 4. Lister les documents
```bash
curl "http://localhost:8000/documents?limit=10"
```

### 5. Obtenir les statistiques
```bash
curl "http://localhost:8000/stats"
```

### 6. Vérifier la santé du système
```bash
curl "http://localhost:8000/health"
```

## 🔧 Configuration avancée

### Chunking
Modifier dans `.env`:
```bash
CHUNK_SIZE=500          # Taille des chunks en caractères
CHUNK_OVERLAP=50        # Chevauchement entre chunks
```

### Modèle d'embeddings
```bash
# all-MiniLM-L6-v2 (rapide, 384 dim)
EMBEDDING_MODEL=all-MiniLM-L6-v2
VECTOR_SIZE=384

# all-mpnet-base-v2 (meilleur, 768 dim)
EMBEDDING_MODEL=all-mpnet-base-v2
VECTOR_SIZE=768
```

### LLM Provider
**OpenAI:**
```bash
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-3.5-turbo
# ou
LLM_MODEL=gpt-4
```

**Anthropic Claude:**
```bash
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL=claude-3-haiku-20240307
# ou
LLM_MODEL=claude-3-sonnet-20240229
```

## 📊 Structure du projet

```
chatbot-supnum/
├── app/
│   ├── db/
│   │   ├── postgres.py          # Configuration PostgreSQL
│   │   └── qdrant_client.py     # Client Qdrant
│   ├── models/
│   │   ├── pg_models.py         # Modèles SQLAlchemy
│   │   └── qdrant_models.py     # Modèles Pydantic
│   ├── services/
│   │   ├── indexing.py          # Service d'indexation
│   │   ├── retrieval.py         # Service de récupération
│   │   └── query_handler.py     # Gestionnaire de requêtes
│   ├── utils/
│   │   ├── chunking.py          # Découpage de texte
│   │   ├── embeddings.py        # Génération d'embeddings
│   │   └── logging.py           # Configuration des logs
│   ├── routes/
│   │   └── api.py               # Routes API
│   └── main.py                  # Application principale
├── requirements.txt
├── .env.example
├── docker-compose.yml
├── Dockerfile
└── README.md
```

## 🧪 Tests

### Test manuel avec curl
```bash
# 1. Indexer un document de test
curl -X POST "http://localhost:8000/documents" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Document",
    "content": "Ceci est un document de test pour vérifier le système RAG.",
    "doc_type": "text"
  }'

# 2. Poser une question
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Qu'\''est-ce qu'\''un document de test?",
    "top_k": 3
  }'
```

### Test avec Python
```python
import requests

# Indexer
response = requests.post(
    "http://localhost:8000/documents",
    json={
        "title": "Python Test",
        "content": "Test content...",
        "doc_type": "text"
    }
)
print(response.json())

# Poser une question
response = requests.post(
    "http://localhost:8000/ask",
    json={"question": "Test question?"}
)
print(response.json())
```

## 🔍 Monitoring

### Logs
```bash
# Logs de l'application
docker-compose logs -f app

# Logs Postgres
docker-compose logs -f postgres

# Logs Qdrant
docker-compose logs -f qdrant
```

### Interface Qdrant
Accéder à l'interface web: http://localhost:6333/dashboard

## 🚨 Dépannage

### Problème: "Connection refused" à Postgres
```bash
# Vérifier que Postgres est démarré
docker-compose ps

# Redémarrer Postgres
docker-compose restart postgres
```

### Problème: Qdrant ne répond pas
```bash
# Vérifier la santé de Qdrant
curl http://localhost:6333/health

# Recréer le conteneur
docker-compose down qdrant
docker-compose up -d qdrant
```

### Problème: Embeddings trop lents
- Utiliser un modèle plus petit (all-MiniLM-L6-v2)
- Augmenter le batch_size dans embeddings.py
- Utiliser un GPU si disponible

### Problème: Réponses non pertinentes
- Réduire score_threshold (ex: 0.3)
- Augmenter top_k (ex: 10)
- Activer use_context=true
- Améliorer le chunking (taille et overlap)

## 📈 Performance

### Benchmarks typiques
- Indexation: ~2-5 docs/sec
- Requête (retrieval): ~50-100ms
- Génération (LLM): ~1-3s
- Total end-to-end: ~1.5-3.5s

### Optimisation
1. **Cache les embeddings** pour les requêtes fréquentes
2. **Batch processing** pour l'indexation massive
3. **Connection pooling** pour PostgreSQL
4. **GPU** pour les embeddings si disponible

## 🔐 Sécurité

- Ne jamais commiter le fichier `.env`
- Utiliser des secrets management en production
- Limiter l'accès API avec authentification
- Valider tous les inputs utilisateur
- Rate limiting sur les endpoints

## 📝 TODO

- [ ] Ajouter l'authentification JWT
- [ ] Implémenter le rate limiting
- [ ] Ajouter des tests unitaires
- [ ] Support pour PDF et documents Office
- [ ] Interface web React/Vue
- [ ] Cache Redis pour les requêtes
- [ ] Monitoring avec Prometheus
- [ ] CI/CD avec GitHub Actions

## 📄 Licence

MIT

## 👥 Contact

Pour toute question: contact@supnum.mr
