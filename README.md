# NextStep Maroc 🧭

Plateforme **gratuite** et **multilingue** (fr / ar / en) d'aide à l'orientation
après le baccalauréat au Maroc : catalogue d'écoles et de formations, critères
d'admission sourcés, préparation aux concours (QCM), favoris, profil candidat et
espace de modération communautaire.

Application **Streamlit** (Python 3.11), base **SQLite** via **SQLAlchemy**,
validation **Pydantic**, tests **pytest** (+ `streamlit.testing.v1.AppTest`).

> ⚠️ **Projet MVP pédagogique.** Les données de démonstration sont explicitement
> étiquetées (`demo`) et ne constituent **pas** un catalogue officiel. Aucune
> date, aucun critère, aucune statistique et aucun frais de scolarité n'ont été
> inventés : les informations non confirmées s'affichent
> **« Information à vérifier »**.

---

## 1. Prérequis

| Élément   | Version testée                            |
| --------- | ----------------------------------------- |
| Python    | **3.11.9** (3.11.x recommandé)            |
| OS        | Windows / macOS / Linux                   |
| Navigateur| Chrome, Edge, Firefox, Safari (récent)    |
| Réseau    | Aucun requis pour fonctionner en local    |

Vérifier :

```bash
python --version    # doit afficher Python 3.11.x
```

---

## 2. Installation

```bash
# 1. (recommandé) environnement virtuel
python -m venv .venv

# 2. activation
#    Windows PowerShell :
.venv\Scripts\Activate.ps1
#    Windows CMD :
.venv\Scripts\activate.bat
#    macOS / Linux :
source .venv/bin/activate

# 3. dépendances (versions épinglées)
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

`requirements.txt` épingle les versions réellement testées :
`streamlit==1.66.0`, `SQLAlchemy==2.1.5`, `pydantic==2.14.1`, `pandas==3.0.6`,
`plotly==7.1.0`, `pytest==9.1.1`, `python-dotenv==1.2.4`, `bcrypt==5.0.0`.

---

## 3. Configuration

```bash
# 1. copier l'exemple (le fichier .env est ignoré par git)
copy .env.example .env        # Windows
cp .env.example .env          # macOS / Linux

# 2. éditer .env et remplacer les valeurs d'exemple
```

### Variables d'environnement

| Variable                       | Rôle                                             | Défaut                                  |
| ------------------------------ | ------------------------------------------------ | --------------------------------------- |
| `NEXTSTEP_ENV`                 | `development` ou `production`                     | `development`                            |
| `NEXTSTEP_DATABASE_URL`        | Chaîne SQLAlchemy (SQLite ou PostgreSQL)          | `sqlite:///data/nextstep.db`             |
| `NEXTSTEP_SECRET_KEY`          | **Réservée** aux évolutions (non lue par le MVP)  | valeur d'exemple                         |
| `NEXTSTEP_ADMIN_EMAIL`         | E-mail du premier administrateur (CLI)            | — (aucune valeur codée en dur)           |
| `NEXTSTEP_ADMIN_PASSWORD`      | Mot de passe du premier administrateur (CLI)      | — (aucune valeur codée en dur)           |
| `NEXTSTEP_ADMIN_LANGUAGE`      | Langue du compte créé (`fr`/`ar`/`en`)            | `fr`                                     |
| `NEXTSTEP_SEED_DEMO_DATA`      | `true` => charge le jeu de démonstration          | `false`                                  |
| `NEXTSTEP_MAX_LOGIN_ATTEMPTS`  | Tentatives de connexion échouées avant blocage    | `5`                                      |
| `NEXTSTEP_LOGIN_LOCK_SECONDS`  | Durée du blocage                                 | `300`                                    |

Aucun identifiant administrateur n'est codé dans le dépôt : le compte est créé
par la CLI (voir §5) à partir de ces variables ou d'une saisie interactive.

---

## 4. Lancer l'application

```bash
python -m streamlit run app.py
```

Puis ouvrir <http://localhost:8501> (le port est affiché dans le terminal).

Options utiles :

```bash
python -m streamlit run app.py --server.port 8502
python -m streamlit run app.py --server.headless false
```

Configuration Streamlit : `.streamlit/config.toml` (thème bleu marine / bleu /
vert, protection XSRF activée, détails d'erreur masqués pour les visiteurs).

---

## 5. Base de données, administrateur et données de démonstration

La CLI `manage.py` réalise les opérations d'exploitation. Elle crée le schéma
**sans jamais supprimer** une base existante (`create_all` idempotent, aucun
`drop`).

```bash
# a) créer / mettre à jour le schéma
python manage.py init-db

# b) créer le premier administrateur (jamais codé en dur)
python manage.py create-admin --email moi@exemple.ma
#    -> invite interactif pour le mot de passe (politique : 8 caractères min.)
#    ou, non interactif :
NEXTSTEP_ADMIN_PASSWORD='...' python manage.py create-admin --email moi@exemple.ma

# c) charger le jeu de démonstration (étiqueté « demo »)
python manage.py seed-demo

# d) vérifier
python manage.py stats
python manage.py list-users     # n'affiche jamais de mot de passe
```

Charger le seed automatiquement au démarrage (optionnel) :

```bash
NEXTSTEP_SEED_DEMO_DATA=true python -m streamlit run app.py
```

> **Idempotence** : relancer `init-db` ou `seed-demo` n'écrase ni ne duplique
> les données existantes (les entités de démonstration sont détectées).

### Migration vers PostgreSQL

Rien d'autre à changer que l'URL (le schéma n'utilise aucun type propre à SQLite) :

```bash
NEXTSTEP_DATABASE_URL=postgresql+psycopg2://utilisateur:motdepasse@localhost:5432/nextstep
python manage.py init-db
```

Le pilote `psycopg2` n'est pas épinglé dans `requirements.txt` : à installer
volontairement lors de la migration.

---

## 6. Tests

```bash
python -m pytest
```

- `pytest.ini` limite la collecte au dossier `tests/` ;
- **chaque test crée sa propre base SQLite temporaire** : aucune donnée réelle
  n'est lue, modifiée ou supprimée ;
- les tests d'interface utilisent `streamlit.testing.v1.AppTest` et exécutent
  réellement l'application (accueil, langue, pages catalogue/orientation,
  garde de la page d'administration).

Couverture par critère d'acceptation :

| Critère                                                | Fichier de test                        |
| ------------------------------------------------------ | -------------------------------------- |
| Initialisation de la base (idempotence, FK, index)     | `tests/test_database.py`               |
| Validation du profil candidat                          | `tests/test_profile_validation.py`     |
| Hachage des mots de passe + limitation des tentatives  | `tests/test_security_auth.py`          |
| Rôles et permissions (métier, pas seulement l'UI)      | `tests/test_permissions.py`            |
| Recherche / filtrage des écoles                        | `tests/test_schools_catalog.py`        |
| Critères d'admission inconnus → « à vérifier »         | `tests/test_schools_catalog.py`, `tests/test_orientation.py` |
| Recommandations d'orientation déterministes            | `tests/test_orientation.py`            |
| Correction et score des QCM                            | `tests/test_quizzes.py`                |
| Enregistrement des tentatives                          | `tests/test_quizzes.py`                |
| Favoris                                                | `tests/test_schools_catalog.py`        |
| Validation des ressources communautaires               | `tests/test_resources.py`              |
| Empêcher les modifications non autorisées             | `tests/test_permissions.py`, `tests/test_resources.py` |
| Échéances (dates inconnues, sources)                   | `tests/test_deadlines_rules.py`        |
| Interface (AppTest)                                    | `tests/test_ui_app.py`                 |

---

## 7. Architecture

```
app.py                    # entrypoint : cadre commun (sidebar, langue, navigation) + accueil
manage.py                 # CLI : init-db, create-admin, seed-demo, stats, list-users
pages/                    # pages Streamlit (st.navigation)
  0_Tableau_de_bord.py    # tableau de bord candidat / invité
  1_Orientation.py        # questionnaire multi-étapes + recommandations
  2_Ecoles_Formations.py  # catalogue, filtres, détail, favoris, échéances
  3_Preparation_Concours.py  # QCM, correction, progression, fiches, signalements
  4_Mes_Favoris.py        # favoris
  5_Mon_Profil.py         # profil, compte, suppression des données
  6_Administration.py     # modération / administration (staff uniquement)
database/
  models.py               # entités, contraintes, index, horodatages
  connection.py           # engine, PRAGMA foreign_keys, init idempotente
  repositories.py         # requêtes ORM (jamais de SQL concaténé)
  seed.py                 # jeu de démonstration (étiqueté demo)
services/                 # logique métier + contrôles de rôle
components/               # mise en page, navigation, cartes, formulaires
utils/                    # traductions (fr/ar/en), validation Pydantic, sécurité, aides
assets/styles.css         # thème (classes ns-*, sans hacks DOM fragiles)
data/demo_data.json       # données de démonstration
tests/                    # suites pytest + AppTest
```

### Logique de recommandation (déterministe, sans IA)

Documentée en tête de `services/orientation_service.py` :

1. le questionnaire produit des réponses symboliques stables ;
2. chaque parcours déclare des **signaux** (question, réponse, pondération) ;
3. la contribution par question est **plafonnée** au poids maximal du parcours ;
4. `indice = 100 × contribution obtenue / contribution maximale` (0–100).

Mêmes réponses ⇒ mêmes résultats, aucune randomisation, **aucun modèle
apprenti**. Cet indice est un **indice d'intérêt** : il n'est **jamais** présenté
comme une probabilité d'admission ni comme un classement.

Compatibilité formation/profil : `ok`, `ko`, `unknown` (« Vérification
nécessaire »), `no_rule` (aucun critère publié). Un critère n'est évalué que si
son statut est `official_verified` ou `demo`.

---

## 8. Limites connues (SQLite, Streamlit, sécurité)

**SQLite**

- un seul processus en écriture : performances limitées en cas de forte
  concurrence (convient à un MVP / usage pédagogique) ;
- pas de contrôle d'accès par utilisateur en base : le chiffrement du fichier
  n'est pas activé ;
- migration possible vers PostgreSQL en changeant uniquement l'URL (voir §5).

**Streamlit**

- `st.session_state` appartient au **processus** : ce n'est **pas** une
  frontière de sécurité. Les autorisations sont donc vérifiées dans les
  services (`ensure_role`) **et** au niveau des requêtes ;
- chaque rerun ré-exécute le script : les données lourdes sont mises en cache
  (`st.cache_data`) ;
- pas de gestion de sessions multi-serveurs : une mise en échelle horizontale
  exigerait un stockage d'état partagé ;
- l'application est responsive (colonnes, conteneurs, barre latérale) mais ce
  n'est **pas** une application mobile native ;
- le RTL pour l'arabe est appliqué via une surcharge CSS : correct dans les
  limites de Streamlit, à revérifier si le thème par défaut change.

**Sécurité appliquée**

- mots de passe hachés avec **bcrypt** (12 tours) — jamais en clair, jamais
  journalisés ;
- limitation des tentatives de connexion **par processus** (mémoire) : pour une
  production multi-instances, prévoir Redis/PostgreSQL ou un service d'identité ;
- requêtes uniquement via l'ORM SQLAlchemy (requêtes paramétrées) ;
- contrôles de rôle dans la couche métier **et** cachette masquée côté UI ;
- `.env` ignoré par git, aucun secret en dur, `.streamlit/secrets.toml` ignoré ;
- journal d'audit sans secret (actions, entité, acteur, détails non sensibles) ;
- suppression des données personnelles (profil, favoris, tentatives, résultats ;
  l'audit est anonymisé) via le bouton de la page « Mon profil » ;
- validation systématique Pydantic côté serveur avant toute écriture.

---

## 9. Données personnelles — loi 09-08 / CNDP

- Les données collectées sont volontairement **minimales** (e-mail, série,
  moyenne, préférences) : c'est le principe de minimisation de la **loi
  n° 09-08** relative à la protection des personnes physiques à l'égard du
  traitement des données à caractère personnel.
- Avant toute mise en production réelle, une déclaration/de demande d'**avis**
  auprès de la **CNDP** est à prévoir, ainsi qu'une politique de confidentialité
  lisible par l'utilisateur (finalités, durée de conservation, droits d'accès,
  de rectification et d'effacement).
- Le droit à l'effacement est implémenté côté applicatif ; la suppression
  définitive des sauvegardes (backups) reste un processus d'exploitation.
- L'application n'utilise ni traceur publicitaire ni service tiers d'analytics
  (`gatherUsageStats = false`).

---

## 10. Prudence avant mise en ligne

1. **Données** : re-sourcer et re-vérifier chaque école, formation, critère,
   échéance et frais ; ne passer en `official_verified` qu'avec une source
   datée. Le statut `demo` doit rester lisible par l'utilisateur.
2. **Comptes** : créer l'administrateur via CLI, mot de passe fort, puis
   révoquer tout compte de test ; ne jamais réutiliser `admin@example.com`.
3. **Configuration** : `NEXTSTEP_ENV=production`, HTTPS obligatoire (reverse
   proxy : nginx/Caddy), `.env` protégé en lecture (600) et hors dépôt.
4. **Base** : migrer vers PostgreSQL si plusieurs utilisateurs simultanés ;
   mettre en place des sauvegardes chiffrées et un plan de restauration.
5. **Rate limiting** : passer d'un compteur mémoire à un stockage partagé.
6. **Pénétration / revue** : revue du code sécurité, test de charge, contrôle
   des en-têtes HTTP (HSTS, CSP, cookies `Secure`/`HttpOnly` via le proxy).
7. **Juridique** : mentions légales, politique de confidentialité (§9),
   hébergement au Maroc ou déclaration CNDP adaptée.
8. **Accessibilité** : tests clavier/mobile réels sur les trois langues.

---

## 11. Dépannage

| Symptôme                                   | Cause probable / solution                                             |
| ------------------------------------------ | --------------------------------------------------------------------- |
| `ModuleNotFoundError: streamlit`           | mauvais environnement virtuel -> réactiver puis réinstaller les deps   |
| `database is locked`                       | un autre processus tient la base -> fermer les sessions ouvertes        |
| Page blanche                               | regarder le terminal Streamlit ; `showErrorDetails = "none"` masque les traces côté navigateur |
| Seed non chargé                            | vérifier `NEXTSTEP_SEED_DEMO_DATA=true` ou lancer `python manage.py seed-demo` |
| `permission refusée` pour un staff         | vérifier le rôle en base : `python manage.py list-users`                |
| Tests échouent sur une base existante      | les tests utilisent leur propre base temporaire : vérifier les droits du répertoire temporaire |

---

## 12. Palette et interface

- **Bleu marine** (structure, en-têtes), **bleu** (actions, liens), **vert**
  (succès, indicateurs positifs) ; fonds clairs, contrastes élevés.
- Styles regroupés dans `assets/styles.css` avec des classes `ns-*` : pas de
  sélecteurs DOM fragiles ni de manipulation de la structure Streamlit.
- Composants natifs utilisés : `set_page_config`, `st.navigation` / `st.Page`,
  barre latérale, colonnes, onglets, formulaires, `session_state`,
  `dataframe`, `metric`, `st.dialog`, `st.page_link`.

---

## 13. Aller plus loin (hors périmètre MVP)

- Espace étudiant ENCG (hors périmètre du MVP).
- Comptes professionnels (écoles) avec processus de vérification des sources.
- Export PDF du profil et des recommandations.
- Mode hors-ligne (PWA) et tests d'accessibilité automatisés.
- CI (lint + tests) et migrations Alembic pour PostgreSQL.
