 🐾 Chaton - Assistant IA

Assistant conversationnel intelligent avec support RAG (Retrieval-Augmented Generation), multi-modal et export de documents.

## Fonctionnalités

### LLM Flexible
- **Mode OpenAI** : Connexion à une API compatible OpenAI (Albert, OpenAI, etc.). C'est son mode de fonctionnement nominal, vous devez posséder une clé pour l'API Albert de la DiNum.
- **Mode Ollama** : Utilisation de modèles locaux via Ollama (GPU fortement recommandé)
- Support multi-modal : texte, images, code
- Streaming des réponses

### RAG (Retrieval-Augmented Generation)
- **Collections locales** : Via Qdrant (base vectorielle locale)
- **Collections distantes** : Via API Albert
- Recherche avancée
- Reranking avec modèle BGE
- Extension automatique du contexte avec chunks adjacents

###  Gestion de documents
- Upload multiple de PDFs
- Extraction de contenu web (URLs)
- Upload d'images pour analyse visuelle
- Support LaTeX dans les réponses

###  Export de documents
- **Word (DOCX)** : Export formaté des conversations
- **Excel (XLSX)** : Export de tableaux et données structurées (version préliminaire alpha)
- **PowerPoint (PPTX)** : Génération de présentations à partir d'un prompt, d'un document PDF ou du RAG

### Profils intégrés
- Plusieurs profils (rôles) intégrés via un fichier de configuration des prompts systèmes pour s'adapter au contexte ou à la mission de l'assistant.

###  Interface utilisateur
- Interface Streamlit responsive
- Affichage des sources RAG
- Configuration avancée dans la sidebar

## Prérequis

- Python 3.9+ (testé avec 3.12.8)
- (Optionnel) Qdrant pour les collections locales
- (Optionnel) Ollama pour les modèles locaux

##  Installation

### 1. Créer un environnement virtuel

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

### 2. Installer les dépendances

**Important** : L'installation dépend de votre configuration matérielle.

#### Option A : GPU NVIDIA avec CUDA 11.8 (typiquement pour architecture Pascal, non supportée par les versions de CUDA > 11.8)

```bash
# Installer les dépendances de base
pip install -r requirements.txt

# Installer PyTorch avec CUDA 11.8
pip install -r requirements-cuda11.txt
```

#### Option B : GPU NVIDIA avec CUDA 12.x (architectures post-Pascal)

```bash
# Installer les dépendances de base
pip install -r requirements.txt

# Installer PyTorch avec CUDA 12.x
pip install -r requirements-cuda12.txt
```

#### Option C : CPU uniquement (sans GPU, adapté au fonctionnement Albert API, sinon bonne chance si vous utilisez des LLM locaux)

```bash
# Installer les dépendances de base
pip install -r requirements.txt

# Installer PyTorch CPU
pip install -r requirements-cpu.txt
```

#### Vérifier l'installation CUDA

```bash
# Vérifier la version CUDA disponible
python -c "import torch; print(f'CUDA disponible: {torch.cuda.is_available()}'); print(f'Version CUDA: {torch.version.cuda}')"
```

### 3. Configuration

Copiez le fichier d'exemple et configurez vos paramètres :

```bash
cp .env.example .env
```

Éditez `.env` avec vos paramètres :
