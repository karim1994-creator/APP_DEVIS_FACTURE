
# APP_DEVIS_FACTURE
Cette application permet la gestion des clenets, fournisseurs et devis
## 🔧 Prérequis
- Python 3.10+ installé
- Git (valeur recommandée)
- (Optionnel) `pipenv` ou `virtualenv`

---

## 🧠 Installation

1. **Clone le dépôt**  
   ```bash
   git clone https://github.com/karim1994-creator/APP_DEVIS_FACTURE.git
   cd APP_DEVIS_FACTURE
   ```

2. **Crée et active un environnement virtuel**  
   Avec `venv` :
   ```bash
   python -m venv venv
   source venv/bin/activate     # Linux/macOS
   venv\Scripts\activate      # Windows
   ```
   Ou avec `pipenv` :
   ```bash
   pip install pipenv
   pipenv shell
   ```

3. **Installe les dépendances**  
   ```bash
   python -m pip install --upgrade pip setuptools wheel
   pip cache purge
   python -m pip install --upgrade pip setuptools wheel
   pip install Flask==3.1.0 Flask-SQLAlchemy==3.1.1 Flask-Migrate==4.1.0
   pip install alembic==1.15.2 blinker==1.9.0 click==8.1.8 colorama==0.4.6 contourpy==1.3.2 cycler==0.12.1 Flask-Mail==0.9.1 fonttools==4.58.0 greenlet==3.2.1 itsdangerous==2.2.0 Jinja2==3.1.6 kiwisolver==1.4.8 lxml==5.4.0 Mako==1.3.10 MarkupSafe==3.0.2 matplotlib==3.10.3 networkx==3.4.2 numpy==2.2.5 packaging==25.0 pandas==2.2.3 pdfkit==1.0.0 pillow==11.2.1 pyparsing==3.2.3 python-dateutil==2.9.0.post0 python-docx==1.1.2 pytz==2025.2 scipy==1.15.2 six==1.17.0 SQLAlchemy==2.0.40 typing_extensions==4.13.2 tzdata==2025.2 Werkzeug==3.1.3
   pip cache list



## ▶️ Lancement de l’application

```bash
flask run
```
ou
```bash
python app.py
```
Puis ouvre dans le navigateur : http://localhost:5000

---

## 📬 Tests & Email

- Dans `.env`, configure ton serveur SMTP.
- Utilise `/send_quote` ou la route dédiée pour tester l’envoi d’e‑mails.

---

## 📄 Fonctionnalités

- Gestion des clients et fournisseurs (il faut créer la liste des clients et fournissuers avant la création des devis)
- Création et envoi de devis
- Suivi des devis
- Authentification (hashage des mots de passe, inscription)

