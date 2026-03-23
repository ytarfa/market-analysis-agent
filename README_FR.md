# Agent d'Analyse de Marché

Un système agentique d'intelligence de marché pour le e-commerce. Étant donné un nom de produit ou une requête de marché (par ex. « iPhone 16 Pro »), il effectue de manière autonome des recherches sur le paysage concurrentiel, les prix, le sentiment des consommateurs et les tendances du marché, puis produit un rapport Markdown complet avec des recommandations stratégiques et des graphiques intégrés.

## Comment ça fonctionne

1. **Génération du brief** -- Un LLM convertit votre requête brute en un brief de recherche structuré comprenant le nom du produit, la catégorie de marché, le public cible et les questions de recherche.
2. **Planification et exécution de la recherche** -- Un agent coordinateur décompose le brief en sujets de recherche et lance des agents chercheurs indépendants. Chaque chercheur exécute une boucle ReAct en appelant des outils (recherche web, avis Amazon, Google Trends) pour collecter des données.
3. **Génération du rapport** -- Un LLM analyste senior synthétise toutes les recherches en un rapport Markdown de 2500 à 3000 mots couvrant le résumé exécutif, le paysage concurrentiel, l'analyse des prix, le sentiment des consommateurs, les tendances du marché et les recommandations stratégiques.

## Prérequis

- Python 3.13+
- Gestionnaire de paquets [uv](https://docs.astral.sh/uv/)
- Docker & Docker Compose (optionnel, pour une utilisation conteneurisée)

## Installation

### 1. Cloner le dépôt

```bash
git clone <repo-url>
cd market-analysis-agent-moov-ai
```

### 2. Créer votre fichier d'environnement

```bash
cp .env.example .env
```

Modifiez `.env` et renseignez vos clés API :

```
ANTHROPIC_API_KEY=votre-cle-anthropic
TAVILY_API_KEY=votre-cle-tavily
SERPAPI_API_KEY=votre-cle-serpapi
```

| Variable | Requise | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | **Oui** | Clé API pour les modèles Anthropic Claude (alimente tous les appels LLM) |
| `TAVILY_API_KEY` | **Oui** | Clé API pour la recherche web Tavily |
| `SERPAPI_API_KEY` | Non | Clé API pour SerpAPI (avis Amazon + Google Trends) |

> **Note sur SerpAPI :** La clé `SERPAPI_API_KEY` est optionnelle. Cependant, sans celle-ci, le système se rabat sur des services simulés qui ne retournent que des données en cache. Cela signifie que les sections du rapport concernant les avis Amazon et Google Trends seront basées sur des données obsolètes ou de substitution, ce qui réduira significativement la qualité et la précision du rapport final.

### 3. Installer les dépendances

```bash
uv sync
```

## Lancer le projet

### En local

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

L'API sera disponible à l'adresse `http://localhost:8000`.

### Docker

```bash
docker compose up --build
```

## Utilisation

### Vérification de l'état de santé

```bash
curl http://localhost:8000/health
```

### Lancer une analyse de marché

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"query": "iPhone 16 Pro"}'
```

La réponse contient le brief de recherche, les résultats de recherche individuels et le rapport Markdown final. Les rapports sont également sauvegardés dans le répertoire `reports/` avec un horodatage UTC ajouté au nom du fichier (par ex. `iphone_16_pro_20260323T142530Z.md`).

> **Note :** Des exemples de rapports sont disponibles dans le répertoire `reports/`.

### Télécharger un rapport

Les rapports peuvent être téléchargés par nom via :

```bash
curl -OJ http://localhost:8000/api/reports/iphone_16_pro_20260323T142530Z.md
```

`GET /api/reports/{filename}` retourne le fichier Markdown en pièce jointe. Le nom exact du fichier est inclus dans la réponse de `/analyze` et visible dans le répertoire `reports/`.

> **Note :** Les rapports contiennent des graphiques Mermaid. Tous les lecteurs Markdown ne rendent pas le Mermaid — [markdownviewer.pages.dev](https://markdownviewer.pages.dev/) en est un qui le fait.

## Coût

L'exécution d'un seul rapport d'analyse de marché peut coûter jusqu'à **~1 $ USD** en utilisation d'API entre les appels Anthropic et les API de recherche. Gardez cela à l'esprit lors de l'exécution de multiples analyses.

## Développement

```bash
# Lancer les tests
pytest

# Linter
ruff check .

# Vérification des types
mypy .
```

## Structure du projet

```
app/
├── main.py                  # Point d'entrée FastAPI
├── config.py                # Configuration et paramètres des modèles
├── api/routes.py            # Points de terminaison API
├── agent/                   # Orchestration des agents LangGraph
│   ├── analysis_pipeline.py # Pipeline principal : brief -> recherche -> rapport
│   ├── coordinator.py       # Coordinateur de recherche : planifier -> lancer -> évaluer
│   └── researcher.py        # Sous-graphe chercheur : boucle ReAct d'appel d'outils
├── schemas/                 # Modèles Pydantic
├── services/                # Wrappers d'API externes (SerpAPI, etc.)
├── tools/                   # Outils LangChain (recherche web, avis, tendances)
└── utils/cache.py           # Cache de réponses basé sur des fichiers JSON
```



# Réponses théoriques (Étapes 4-7)

---

## Vue d'ensemble

Architecture LangGraph à trois couches :

1. **AnalysisPipeline** : convertit une requête brute en un brief de recherche structuré, délègue la recherche, synthétise le rapport final.
2. **ResearchCoordinator** : décompose le brief en sujets, lance des agents chercheurs, vérifie si les résultats sont suffisants, relance si nécessaire.
3. **ResearcherSubgraph** : chaque chercheur exécute une boucle ReAct en appelant des outils (recherche web, avis Amazon, Google Trends) jusqu'à avoir suffisamment de données, puis compresse les résultats en un résumé.

## Diagrammes

<table>
  <tr>
    <td align="center"><strong>Pipeline d'analyse</strong></td>
    <td align="center"><strong>Coordinateur</strong></td>
    <td align="center"><strong>Chercheur</strong></td>
  </tr>
  <tr>
    <td><img src="images/analysis_pipeline_diagram.png" width="300" /></td>
    <td><img src="images/coordinator_diagram.png" width="300" /></td>
    <td><img src="images/researcher_diagram.png" width="300" /></td>
  </tr>
</table>


---

## Étapes 1-3 : Décisions techniques

### Pourquoi LangGraph

C'est le framework avec lequel j'ai une expérience pratique. CrewAI ajoute une abstraction basée sur les rôles dont je n'avais pas besoin. Google ADK est étroitement couplé à l'écosystème Google. Faire du Python natif pur aurait signifié reconstruire la gestion d'état, le dispatch d'outils, le routage conditionnel et la logique de retry à partir de zéro. Le temps était mieux investi sur le pipeline lui-même.

### Pourquoi la recherche approfondie

Surtout pour le plaisir. Inspiré par l'article d'Anthropic sur [comment ils ont construit un système de recherche multi-agents](https://www.anthropic.com/engineering/built-multi-agent-research-system) que j'avais lu quelques semaines auparavant : un coordinateur qui planifie les sujets, lance des chercheurs, évalue la suffisance et relance s'il reste des lacunes.

### Des agents plutôt que des outils

L'évaluation mentionne un scraper web, un analyseur de sentiment, un analyseur de tendances de marché et un générateur de rapports. Mon implémentation se découpe différemment :

- **Scraper web → outil de recherche web Tavily.** Fonctionnellement équivalent.
- **Analyseurs de sentiment et de tendances → agents chercheurs.** Ce sont des tâches analytiques qu'un LLM effectue nativement. Le coordinateur décide de ce qui doit être investigué et lance dynamiquement des chercheurs au lieu de coder en dur des rôles d'analystes.
- **Générateur de rapports → nœud du pipeline.** Toujours la dernière étape, pas un point de décision, donc il n'a pas sa place en tant qu'outil.

### Abstractions

- Les services API (recherche Amazon, avis, Google Trends) héritent d'une classe de base partagée `SerpapiService`. Ajouter une nouvelle source de données = étendre la base et définir les paramètres de requête.
- Chaque service a une base abstraite avec une implémentation réelle et une implémentation simulée. Une fonction factory vérifie si la clé API existe et retourne la bonne implémentation.
- `fetch_reviews` utilise un **pattern stratégie** : itère à travers des stratégies de récupération d'avis (Amazon, recherche web en fallback). Ajouter une nouvelle source = nouvelle classe de stratégie, l'ajouter à la liste, l'outil ne change pas.

---

## Étape 4 : Architecture des données et stockage

J'utiliserais **Postgres** pour les données structurées et **Redis** pour le cache.

Tables principales :

- `analyses` : stocke chaque exécution. Requête, statut, le brief généré (jsonb), le rapport final en Markdown, les métadonnées comme le nombre de tokens et la durée, les horodatages.
- `research_results` : FK vers analyses, stocke le sujet et les résultats de chaque chercheur en jsonb.
- `price_snapshots` : nom du produit, source, prix, horodatage. Index sur `(product_name, captured_at)` pour des requêtes rapides par plage et des comparaisons historiques.

Pour le **versionnement des rapports**, chaque exécution crée simplement une nouvelle ligne dans `analyses`. Requêter par nom de produit trié par date pour comparer les versions.

Pour le **cache**, Redis avec des clés à TTL pour les résultats de recherche, les données d'avis et les tendances. Évite les appels API redondants quand le même produit est analysé plusieurs fois dans un court laps de temps.

---

## Étape 5 : Monitoring et observabilité

### Traçage

**LangSmith** puisque le système utilise déjà LangGraph. Il capture le graphe d'exécution complet par exécution : chaque nœud, appel d'outil et invocation LLM. Chaque analyse obtient un identifiant de trace qui se propage à travers les trois couches, permettant de déboguer n'importe quelle exécution depuis un seul lien. Une alternative si l'on n'utilise pas LangGraph pourrait être quelque chose comme OpenTelemetry.

### Métriques

Point de terminaison Prometheus `/metrics` (visualisation avec Grafana). Éléments clés à suivre :

- Durée de bout en bout d'une analyse
- Latence des appels LLM par nœud
- Utilisation des tokens (entrée/sortie) pour le suivi des coûts
- Taux d'erreur des appels d'outils
- Nombre d'itérations ReAct des chercheurs
- Fréquence de replanification du coordinateur
- Analyses actives/en file d'attente actuelles

### Alertes

Alertes Grafana vers Slack ou similaire. Alerter sur les pics de latence, les taux d'erreur élevés des outils, la profondeur de file d'attente croissante ou la dégradation du fournisseur LLM.

### Qualité des résultats

Exécuter une évaluation LLM-juge sur un échantillon de rapports (voir Étape 7), suivre les scores en série temporelle, alerter si la moyenne baisse.

---

## Étape 6 : Mise à l'échelle et optimisation

### Gestion des pics de charge

- Pour une configuration simple : une file de tâches. Le point de terminaison `/analyze` met un job en file d'attente et retourne immédiatement un identifiant. Les workers récupèrent les jobs de la file.
- Pour quelque chose de plus résilient sans gérer l'infrastructure : des fonctions durables (comme Azure Durable Functions) gèrent l'orchestration, les retries et la mise à l'échelle automatiquement.
- Pour un système plus complexe avec de nombreux services : une architecture microservices sur Kubernetes avec des politiques d'auto-scaling.

### Optimisation des coûts LLM

- Utiliser des modèles moins chers/plus rapides pour les tâches simples (génération de brief, compression de résumé). Réserver le modèle coûteux pour la synthèse du rapport final.
- Mettre en cache les réponses LLM pour des prompts identiques.
- Plafonner les boucles d'itération des chercheurs.
- Ingénierie du contexte : élaguer les résultats d'outils avant de les passer au LLM. Supprimer le boilerplate, le bruit HTML et les métadonnées, ne garder que les parties réellement pertinentes pour la question de recherche. Contexte plus court = moins de tokens = coût réduit.

### Cache

Deux couches :

1. **Niveau outil (Redis, TTL court) :** mettre en cache les réponses brutes des API. La même requête de recherche dans l'heure suivante utilise le cache au lieu de rappeler l'API.
2. **Niveau rapport (Postgres) :** si quelqu'un demande une analyse pour une requête récemment complétée, retourner le rapport existant.

---

## Étape 7 : Amélioration continue et tests A/B

### LLM-juge

Définir une grille d'évaluation (précision, exhaustivité, actionnabilité, qualité rédactionnelle, chacune avec un score de 1 à 5). Après chaque analyse, envoyer le rapport + les recherches brutes à un LLM juge. Stocker les scores aux côtés de l'analyse. Suivre les tendances dans le temps.

### Comparer les stratégies de prompts

Versionner tous les prompts. Pour les analyses entrantes, assigner aléatoirement une version de prompt et taguer les résultats. Après suffisamment d'échantillons, comparer les scores moyens du juge. Le gagnant devient la version par défaut.

### Boucle de retour utilisateur

Pouce vers le haut/bas sur les rapports livrés, commentaire libre optionnel. Comparer les évaluations des utilisateurs avec les scores du juge. Réviser périodiquement les rapports mal notés, identifier les patterns, mettre à jour les prompts.

### Évolution des capacités

- Nouveaux outils : le pattern stratégie et les classes de base rendent cela simple.
- Nouveaux modèles et prompts : répartition A/B du même prompt avec différents modèles et prompts, comparer les scores du juge.
