# APP_DEVIS_FACTURE

Application Flask pour la gestion de devis et factures.

---

## Prérequis

- Python 3.10 ou supérieur
- MySQL
- pip

---

## Installation

### 1. Installer Python

1. Téléchargez Python depuis : [https://www.python.org/downloads/](https://www.python.org/downloads/)  
2. Lancez l’installateur et **cochez `Add Python to PATH`**.  
3. Cliquez sur `Install Now`.  
4. Vérifiez l’installation dans le terminal :
   ```bash
   python --version
   ```
5. Vérifiez que `pip` est installé :
   ```bash
   pip --version
   ```

---

### 2. Installer MySQL

1. Téléchargez MySQL : [https://dev.mysql.com/downloads/installer/](https://dev.mysql.com/downloads/installer/)  
2. Lancez l’installateur et choisissez **Developer Default**.  
3. Configurez l’utilisateur root avec le mot de passe `root`.  
4. Notez le port (par défaut 3306).  

#### Optionnel : Installer HeidiSQL

- Télécharger HeidiSQL : [https://www.heidisql.com/download.php](https://www.heidisql.com/download.php)  
- Connectez-vous à MySQL avec :
  - Hôte : `localhost`
  - Utilisateur : `root`
  - Mot de passe : `root`
  - Port : `3306`  
- Créez une base de données vide : `app_devis`

---

### 3. Installer les dépendances Python

1. Placez-vous dans le dossier du projet :  
   ```bash
   cd chemin/vers/APP_DEVIS_FACTURE
   ```
2. Installez les packages requis :
   ```bash
   pip install -r requirements.txt
   ```

---

### 4. Configurer la base de données

- La base de données est MySQL et s’appelle `app_devis`.  
- Lors du premier lancement, **il suffit de créer une base vide**. L’application créera automatiquement les tables.  
- Vous pouvez modifier les informations de connexion dans `app.py` :
  ```python
  'mysql+pymysql://root:root@localhost/app_devis?charset=utf8mb4'
  ```

---

### 5. Premier compte admin

- Pour créer le premier compte admin, inscrivez-vous avec :  
  ```
f.bertolini@atlantis-evolution.com
  ```
- Ce compte sera automatiquement validé comme admin.  
- **Ne supprimez jamais ce compte pour des raisons de sécurité.**

---

### 6. Lancer l’application

```bash
python app.py
```

- L’application sera disponible sur `http://127.0.0.1:5000/`.

---

### 7. Source

- Projet disponible sur GitHub : [https://github.com/karim1994-creator/APP_DEVIS_FACTURE](https://github.com/karim1994-creator/APP_DEVIS_FACTURE)

