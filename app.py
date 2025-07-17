# Import des modules Flask nécessaires pour gérer les routes, formulaires, sessions, redirections, etc.
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session

# Import pour gérer la sécurité des mots de passe (hash)
from werkzeug.security import check_password_hash, generate_password_hash

# Import des modèles de données et fonctions associées (base de données, tables, etc.)
from models import db, create_database, Client, Supplier, Quote, QuoteLine, SupplierPrice, QuoteSupplierInfo, SuiviQuotes

# Gestion des dates et heures
from datetime import datetime

# Import pour gérer l’envoi d’emails via Flask-Mail
from flask_mail import Message, Mail

# Import pour générer et vérifier des tokens sécurisés (ex: pour réinitialisation mot de passe)
from itsdangerous import URLSafeTimedSerializer as Serializer
from flask import current_app
from itsdangerous import SignatureExpired

# Import pour gérer des collections avancées (ex: dictionnaires avec valeurs par défaut)
from collections import defaultdict

# Import de fonctions SQLAlchemy pour requêtes complexes
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload
from sqlalchemy import cast, String
from utils import get_suivi_map
import os
# Liste des différents statuts possibles d’une commande dans le workflow
statut_order = [
    'validate_commande',  # Validation de la commande
    'commande',  # Commande passée
    'reception',  # Réception des marchandises
    'control_reception',  # Contrôle qualité à la réception
    'livraison_client',  # Livraison au client
    'a_facturer',  # À facturer
    'facturation',  # Facturation effectuée
    'cloture'  # Commande clôturée
]

# Création de l’application Flask
app = Flask(__name__)

# Clé secrète utilisée par Flask (session, flash, etc.) => à changer pour un projet réel
app.secret_key = 'b5f9a3408ed34d8a9d8a5bfa7c69598c'

# Configuration de la base de données SQLite locale
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialisation de la base de données avec l'application Flask
db.init_app(app)

# Chargement des configurations supplémentaires depuis un fichier config.py
app.config.from_object('config')

# Initialisation de l’extension Flask-Mail pour l’envoi d’emails
mail = Mail(app)

# Création de la base de données si elle n'existe pas, dans le contexte de l'application
with app.app_context():
    create_database()

# Route principale, affiche la page d’accueil index.html
@app.route('/')
def index():
    return render_template('index.html')

# Route pour ajouter un nouveau client, gère formulaire en GET et POST
@app.route('/add_client', methods=['GET', 'POST'])
def add_client():
    if request.method == 'POST':
        # Création d’un nouvel objet Client à partir des données du formulaire
        client = Client(
            code=request.form['code'],
            civility=request.form['civility'],
            last_name=request.form['last_name'],
            first_name=request.form['first_name'],
            email=request.form['email'],
            job=request.form['job'],
            company=request.form['company'],
            address=request.form['address'],
            city=request.form['city'],
            phone=request.form['phone'],
            mobile=request.form['mobile'],
        )
        # Ajout en base et sauvegarde
        db.session.add(client)
        db.session.commit()
        # Redirection vers la liste des clients après ajout
        return redirect(url_for('list_clients'))
    # Si méthode GET, affichage du formulaire d’ajout client
    return render_template('add_client.html')

# Route pour afficher la liste des clients avec pagination et recherche
@app.route('/clients')
def list_clients():
    # Récupération des paramètres GET : recherche et numéro de page
    search = request.args.get('search', '', type=str)
    page = request.args.get('page', 1, type=int)
    per_page = 5  # Nombre de clients par page

    query = Client.query  # Base de la requête

    if search:
        # Recherche insensible à la casse sur plusieurs colonnes
        like_pattern = f"%{search}%"
        query = query.filter(
            (Client.first_name.ilike(like_pattern)) |
            (Client.last_name.ilike(like_pattern)) |
            (Client.company.ilike(like_pattern)) |
            (Client.city.ilike(like_pattern)) |
            (Client.email.ilike(like_pattern)) |
            (Client.code.ilike(like_pattern))
        )

    # Tri des résultats par nom de famille
    query = query.order_by(Client.last_name)

    # Pagination des résultats
    pagination = query.paginate(page=page, per_page=per_page)

    # Affichage du template avec la liste des clients paginée
    return render_template(
        'list_clients.html',
        clients=pagination,
        search=search,
        page=page,
        total_pages=pagination.pages
    )

# Route pour supprimer un client (via POST) par son ID
@app.route('/delete-client/<int:client_id>', methods=['POST'])
def delete_client(client_id):
    # Recherche du client ou 404 si non trouvé
    client = Client.query.get_or_404(client_id)

    # Vérifie si le client a des devis associés (on ne peut pas supprimer dans ce cas)
    if client.quotes:
        quote_numbers = [quote.quote_number for quote in client.quotes]
        quote_list = ', '.join(quote_numbers)
        flash(f"Vous ne pouvez pas supprimer ce client car il est utilisé dans les devis suivants : {quote_list}", 'danger')
        return redirect(url_for('list_clients'))

    # Si pas de devis liés, suppression du client
    db.session.delete(client)
    db.session.commit()
    flash('Client supprimé avec succès.', 'success')
    return redirect(url_for('list_clients'))

# Route pour éditer les informations d’un client existant
@app.route('/client/edit/<int:client_id>', methods=['GET', 'POST'])
def edit_client(client_id):
    client = Client.query.get_or_404(client_id)  # Recherche client
    if request.method == 'POST':
        # Mise à jour des champs du client à partir du formulaire
        client.code = request.form['code']
        client.civility = request.form['civility']
        client.last_name = request.form['last_name']
        client.first_name = request.form['first_name']
        client.email = request.form['email']
        client.job = request.form['job']
        client.company = request.form['company']
        client.address = request.form['address']
        client.city = request.form['city']
        client.phone = request.form['phone']
        client.mobile = request.form['mobile']
        db.session.commit()
        flash("Client mis à jour avec succès.", "success")
        return redirect(url_for('list_clients'))
    # Si GET, affichage du formulaire pré-rempli
    return render_template('edit_client.html', client=client)

# Route pour afficher la liste des fournisseurs (avec recherche et pagination)
@app.route('/suppliers')
def list_suppliers():
    search = request.args.get('search', '', type=str)
    page = request.args.get('page', 1, type=int)
    per_page = 5

    query = Supplier.query

    if search:
        like_pattern = f"%{search}%"
        query = query.filter(
            (Supplier.first_name.ilike(like_pattern)) |
            (Supplier.last_name.ilike(like_pattern)) |
            (Supplier.company.ilike(like_pattern)) |
            (Supplier.city.ilike(like_pattern)) |
            (Supplier.email.ilike(like_pattern)) |
            (Supplier.code.ilike(like_pattern))
        )

    query = query.order_by(Supplier.last_name)
    pagination = query.paginate(page=page, per_page=per_page)

    return render_template(
        'list_suppliers.html',
        suppliers=pagination,
        search=search,
        page=page,
        total_pages=pagination.pages
    )

# Route pour supprimer un fournisseur (POST) par son ID
@app.route('/delete-supplier/<int:supplier_id>', methods=['POST'])
def delete_supplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)

    # Vérifie si le fournisseur est lié à des prix fournisseurs ou des infos devis fournisseurs
    supplier_price_links = SupplierPrice.query.filter_by(supplier_id=supplier_id).all()
    quote_supplier_info_links = QuoteSupplierInfo.query.filter_by(supplier_id=supplier_id).all()

    if supplier_price_links or quote_supplier_info_links:
        # Récupère les IDs des devis concernés par ces liens
        quote_ids = {link.quote_line.quote_id for link in supplier_price_links}
        quote_ids.update(link.quote_id for link in quote_supplier_info_links)

        # Recherche les devis à partir des IDs
        quotes = Quote.query.filter(Quote.id.in_(quote_ids)).all()
        quote_numbers = [quote.quote_number for quote in quotes]
        quote_list = ', '.join(quote_numbers)

        # Empêche la suppression et affiche un message d’erreur avec les devis concernés
        flash(f"Vous ne pouvez pas supprimer ce fournisseur car il est utilisé dans les devis suivants : {quote_list}", 'danger')
        return redirect(url_for('list_suppliers'))

    # Si pas de liens, suppression du fournisseur possible
    db.session.delete(supplier)
    db.session.commit()
    flash('Fournisseur supprimé avec succès.', 'success')
    return redirect(url_for('list_suppliers'))


@app.route('/supplier/edit/<int:supplier_id>', methods=['GET', 'POST'])
def edit_supplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    if request.method == 'POST':
        supplier.code = request.form['code']
        supplier.civility = request.form['civility']
        supplier.last_name = request.form['last_name']
        supplier.first_name = request.form['first_name']
        supplier.email = request.form['email']
        supplier.job = request.form['job']
        supplier.company = request.form['company']
        supplier.address = request.form['address']
        supplier.city = request.form['city']
        supplier.phone = request.form['phone']
        supplier.mobile = request.form['mobile']
        db.session.commit()
        flash("Fournisseur mis à jour avec succès.", "success")
        return redirect(url_for('list_suppliers'))
    return render_template('edit_supplier.html', supplier=supplier)


@app.route('/add_supplier', methods=['GET', 'POST'])
def add_supplier():
    if request.method == 'POST':
        supplier = Supplier(
            code=request.form['code'],
            civility=request.form['civility'],
            last_name=request.form['last_name'],
            first_name=request.form['first_name'],
            email=request.form['email'],
            job=request.form['job'],
            company=request.form['company'],
            address=request.form['address'],
            city=request.form['city'],
            phone=request.form['phone'],
            mobile=request.form['mobile'],
        )
        db.session.add(supplier)
        db.session.commit()
        return redirect(url_for('list_suppliers'))
    return render_template('add_supplier.html')


@app.route('/create_quote', methods=['GET', 'POST'])
def create_quote():
    if request.method == 'POST':
        today = datetime.today()
        today_str = today.strftime("%d-%m-%Y")

        count_today = Quote.query.filter(func.date(Quote.creation_date) == today.date()).count()
        quote_number = f"DV-{today_str}-{count_today + 1:03d}"

        creation_date = datetime.strptime(request.form['creation_date'], "%d/%m/%Y").date()
        client_id = int(request.form['client_id'])
        delivery_location = request.form['delivery_location']

        quote = Quote(
            quote_number=quote_number,
            creation_date=creation_date,
            client_id=client_id,
            delivery_location=delivery_location
        )
        db.session.add(quote)
        db.session.flush()

        supplier_refs = request.form.getlist("supplier_ref[]")
        descriptions = request.form.getlist("description[]")
        quantities = request.form.getlist("quantity[]")
        client_prices = request.form.getlist("client_price[]")

        supplier_ids = []
        for key in request.form.keys():
            if key.startswith("supplier_price_"):
                sid = key.replace("supplier_price_", "").replace("[]", "")
                if sid not in supplier_ids:
                    supplier_ids.append(sid)

        for i in range(len(supplier_refs)):
            # Calcul du recommended_price (exemple ici : premier discount_percent non vide trouvé)
            recommended_price = 0.0
            for sid in supplier_ids:
                discount_percents = request.form.getlist(f"supplier_discount_percent_{sid}[]")
                if i < len(discount_percents) and discount_percents[i]:
                    try:
                        recommended_price = float(discount_percents[i])
                        break
                    except ValueError:
                        pass

            line = QuoteLine(
                quote_id=quote.id,
                supplier_ref=supplier_refs[i],
                description=descriptions[i],
                quantity=int(quantities[i]),
                client_price=float(client_prices[i]),
                recommended_price=recommended_price
            )
            db.session.add(line)
            db.session.flush()

            for sid in supplier_ids:
                prices = request.form.getlist(f"supplier_price_{sid}[]")
                discount_percents = request.form.getlist(f"supplier_discount_percent_{sid}[]")
                discount_amounts = request.form.getlist(f"supplier_discount_amount_{sid}[]")

                if i < len(prices):
                    db.session.add(SupplierPrice(
                        quote_line_id=line.id,
                        supplier_id=sid,
                        price=float(prices[i]),
                        discount_percent=float(discount_percents[i]) if i < len(discount_percents) and discount_percents[i] else 0.0,
                        discount_amount=float(discount_amounts[i]) if i < len(discount_amounts) and discount_amounts[i] else 0.0
                    ))


        for sid in supplier_ids:
            delay = request.form.get(f"delivery_delay_{sid}")
            fee = request.form.get(f"delivery_fee_{sid}")
            if delay is not None and fee is not None:
                db.session.add(QuoteSupplierInfo(
                    quote_id=quote.id,
                    supplier_id=sid,
                    delivery_delay=int(delay),
                    delivery_fee=float(fee)
                ))

        db.session.commit()
        flash("Devis enregistré avec succès.", "success")
        return redirect(url_for('quote_detail', quote_id=quote.id))

    # GET : préparation du formulaire
    clients = Client.query.all()
    suppliers = Supplier.query.all()
    today = datetime.today()
    today_str = today.strftime("%d-%m-%Y")
    count_today = Quote.query.filter(func.date(Quote.creation_date) == today.date()).count()
    next_num = f"DV-{today_str}-{count_today + 1:03d}"

    selected_client_id = request.args.get('client_id', type=int)

    return render_template(
        "create_quote.html",
        clients=clients,
        suppliers=suppliers,
        quote_number=next_num,
        creation_date=today_str,
        selected_client_id=selected_client_id
    )

# Route de recherche
@app.route('/search_quotes')
def search_quotes():
    query = request.args.get('q', '').strip().lower()

    if query:
        results = Quote.query \
            .join(Client, Quote.client_id == Client.id) \
            .outerjoin(QuoteLine, Quote.id == QuoteLine.quote_id) \
            .options(joinedload(Quote.client), joinedload(Quote.lines)) \
            .filter(
                or_(
                    func.lower(Quote.quote_number).like(f"%{query}%"),
                    func.lower(Client.first_name).like(f"%{query}%"),
                    func.lower(Client.last_name).like(f"%{query}%"),
                    func.lower(Client.company).like(f"%{query}%"),
                    func.lower(QuoteLine.description).like(f"%{query}%"),
                    cast(Quote.creation_date, String).like(f"%{query}%"),
                )
            ).all()
    else:
        results = Quote.query \
            .options(joinedload(Quote.client), joinedload(Quote.lines)) \
            .all()

    suivi_map = get_suivi_map(results)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Si c'est une requête AJAX, on renvoie juste le tableau mis à jour
        return render_template('partials/quote_table.html', quotes=results, suivi_map=suivi_map)
    else:
        # Sinon, tu peux renvoyer la page complète ou la même chose (à adapter si besoin)
        return render_template('partials/quote_table.html', quotes=results, suivi_map=suivi_map)


@app.route('/update_quote/<int:quote_id>', methods=['GET', 'POST'])
def update_quote(quote_id):
    quote = Quote.query.get_or_404(quote_id)
    clients = Client.query.all()
    suppliers = Supplier.query.all()

    if request.method == 'POST':
        try:
            # Mise à jour des champs de Quote
            quote.quote_number = request.form.get('quote_number', quote.quote_number)
            quote.creation_date = datetime.strptime(request.form.get('creation_date'), '%Y-%m-%d').date()
            quote.client_id = int(request.form.get('client_id'))
            quote.delivery_location = request.form.get('delivery_location')

            # Mise à jour / création des QuoteLine
            line_ids = request.form.getlist('line_id[]')  # ex: ['12', 'new', '13']
            descriptions = request.form.getlist('description[]')
            quantities = request.form.getlist('quantity[]')
            client_prices = request.form.getlist('client_price[]')
            supplier_refs = request.form.getlist('supplier_ref[]')

            existing_lines = {line.id: line for line in quote.lines}

            # Traiter chaque ligne envoyée
            for i, line_id in enumerate(line_ids):
                if line_id.isdigit():
                    # Ligne existante
                    line = existing_lines.get(int(line_id))
                    if line:
                        line.description = descriptions[i]
                        line.quantity = int(quantities[i])
                        line.client_price = float(client_prices[i])
                        line.supplier_ref = supplier_refs[i]
                        line.recommended_price = float(request.form.getlist("recommended_price[]")[i])
                else:
                    # Nouvelle ligne
                    new_line = QuoteLine(
                        quote=quote,
                        description=descriptions[i],
                        quantity=int(quantities[i]),
                        client_price=float(client_prices[i]),
                        supplier_ref=supplier_refs[i],
                        recommended_price=float(request.form.getlist("recommended_price[]")[i])

                    )
                    db.session.add(new_line)

            # Supprimer les lignes supprimées
            ids_posted = set(int(lid) for lid in line_ids if lid.isdigit())
            for line in quote.lines:
                if line.id not in ids_posted:
                    db.session.delete(line)

            # Mise à jour des SupplierPrice par ligne
            # (exemple simple, adapter selon le formulaire)
            # On attend des listes avec des noms comme supplier_price_id[], supplier_id[], price[] etc.
            supplier_price_ids = request.form.getlist('supplier_price_id[]')
            sp_supplier_ids = request.form.getlist('sp_supplier_id[]')
            sp_prices = request.form.getlist('sp_price[]')

            existing_sp = {}
            for line in quote.lines:
                for sp in line.supplier_prices:
                    existing_sp[sp.id] = sp

            for i, sp_id in enumerate(supplier_price_ids):
                if sp_id.isdigit():
                    sp = existing_sp.get(int(sp_id))
                    if sp:
                        sp.supplier_id = sp_supplier_ids[i]
                        sp.price = float(sp_prices[i])
                else:
                    # Création de SupplierPrice si nécessaire
                    # Attention il faut le quote_line_id auquel rattacher
                    # Exemple simple : supposons que tu passes quote_line_id dans un champ caché sp_quote_line_id[]
                    sp_quote_line_ids = request.form.getlist('sp_quote_line_id[]')
                    new_sp = SupplierPrice(
                        quote_line_id=int(sp_quote_line_ids[i]),
                        supplier_id=sp_supplier_ids[i],
                        price=float(sp_prices[i])
                    )
                    db.session.add(new_sp)

            # Mise à jour des QuoteSupplierInfo
            qsi_ids = request.form.getlist('qsi_id[]')
            qsi_supplier_ids = request.form.getlist('qsi_supplier_id[]')
            qsi_delays = request.form.getlist('qsi_delivery_delay[]')
            qsi_fees = request.form.getlist('qsi_delivery_fee[]')

            existing_qsi = {info.id: info for info in quote.supplier_info}

            for i in range(len(qsi_supplier_ids)):
                try:
                    info_id = int(qsi_ids[i])
                    info = existing_qsi.get(info_id)
                    if info:
                        info.supplier_id = qsi_supplier_ids[i]
                        info.delivery_delay = int(qsi_delays[i]) if qsi_delays[i] else None
                        info.delivery_fee = float(qsi_fees[i]) if qsi_fees[i] else None
                except (ValueError, TypeError):
                    # Si qsi_id est vide ou invalide, on crée une nouvelle info
                    new_info = QuoteSupplierInfo(
                        quote_id=quote.id,
                        supplier_id=qsi_supplier_ids[i],
                        delivery_delay=int(qsi_delays[i]) if qsi_delays[i] else None,
                        delivery_fee=float(qsi_fees[i]) if qsi_fees[i] else None,
                    )
                    db.session.add(new_info)

            print("=== Infos fournisseur ===")
            for info in quote.supplier_info:
                print(info.id, info.supplier_id, info.delivery_delay, info.delivery_fee)            
            db.session.commit()
            flash('Devis mis à jour avec succès.', 'success')
            return redirect(url_for('show_quote', quote_id=quote.id))

        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors de la mise à jour du devis : {e}", "danger")

    # GET : afficher le formulaire avec données existantes
    return render_template('update_quote.html',
                           quote=quote,
                           clients=clients,
                           suppliers=suppliers)

# Liste des devis
# Liste des devis avec recherche
@app.route('/quotes')
def list_quotes():
    page = request.args.get('page', 1, type=int)
    per_page = 5
    search = request.args.get('search', '', type=str).strip()

    # Base de la requête
    query = Quote.query

    # Si recherche : filtre par numéro de devis, prénom, nom ou date
    if search:
        search_like = f"%{search}%"
        query = query.join(Client).filter(
            db.or_(
                Quote.quote_number.ilike(search_like),
                Client.first_name.ilike(search_like),
                Client.last_name.ilike(search_like),
                db.cast(Quote.creation_date, db.String).ilike(search_like)
            )
        )

    # Pagination
    pagination = query.order_by(Quote.creation_date.desc()).paginate(page=page, per_page=per_page)
    quotes = pagination.items
    total_pages = pagination.pages

    # Statut de suivi
    suivi_map = {}
    for q in quotes:
        suivi = SuiviQuotes.query.filter_by(id_quote=q.id).order_by(SuiviQuotes.id.desc()).first()
        if not suivi:
            suivi = SuiviQuotes(id_quote=q.id, statut='validate_commande')
            db.session.add(suivi)
            db.session.commit()
        suivi_map[q.id] = suivi.statut

    return render_template(
        'list_quotes.html',
        quotes=quotes,
        page=page,
        total_pages=total_pages,
        suivi_map=suivi_map,
        search=search  # On renvoie aussi la recherche pour la garder dans l'input
    )



# Détail d'un devis
@app.route('/get_today_quote_count')
def get_today_quote_count():
    today_str = datetime.utcnow().strftime('%d_%m_%Y')
    count = Quote.query.filter(
        db.func.strftime('%d_%m_%Y', Quote.creation_date) == today_str
    ).count()
    return jsonify({'count': count})


@app.route('/quote/delete/<int:quote_id>', methods=['POST'])
def delete_quote(quote_id):
    quote = Quote.query.get_or_404(quote_id)

    # Supprimer les SupplierPrice liés aux lignes
    for line in quote.lines:
        SupplierPrice.query.filter_by(quote_line_id=line.id).delete()

    # Supprimer les lignes du devis
    QuoteLine.query.filter_by(quote_id=quote.id).delete()

    # Supprimer les infos fournisseurs liées au devis
    QuoteSupplierInfo.query.filter_by(quote_id=quote.id).delete()

    # Supprimer le devis
    db.session.delete(quote)

    db.session.commit()
    flash("Devis et toutes ses données associées supprimés avec succès.", "success")
    return redirect(url_for('list_quotes'))


@app.route('/quotes/<int:quote_id>/advance_status', methods=['POST'])
def advance_status(quote_id):
    suivi = SuiviQuotes.query.filter_by(id_quote=quote_id).order_by(SuiviQuotes.id.desc()).first()
    if not suivi:
        return jsonify({'success': False, 'message': 'Suivi introuvable'}), 404

    current_statut = suivi.statut
    try:
        index = statut_order.index(current_statut)
    except ValueError:
        return jsonify({'success': False, 'message': 'Statut inconnu'}), 400

    if index == len(statut_order) - 1:
        # Statut final => supprimer ou marquer terminé
        db.session.delete(suivi)
        db.session.commit()
        return jsonify({'success': True, 'new_statut': 'terminé'})

    new_statut = statut_order[index + 1]

    # Insérer un nouveau suivi pour le nouveau statut
    new_suivi = SuiviQuotes(id_quote=quote_id, statut=new_statut)
    db.session.add(new_suivi)
    db.session.commit()

    return jsonify({'success': True, 'new_statut': new_statut})


@app.route('/quote/<int:quote_id>')
def quote_detail(quote_id):
    quote = Quote.query.get_or_404(quote_id)
    lines = []

    cheapest_supplier_ids = set()

    for line in quote.lines:
        if line.supplier_prices:
            min_sp = min(line.supplier_prices, key=lambda sp: sp.price)
            best_price = {
                'supplier_id': min_sp.supplier_id,
                'price': min_sp.price,
                'recommended_price': getattr(min_sp, 'recommended_price', None)
            }
            cheapest_supplier_ids.add(min_sp.supplier_id)
        else:
            best_price = None

        lines.append({
            'supplier_ref': line.supplier_ref,
            'description': line.description,
            'quantity': line.quantity,
            'client_price': line.client_price,
            'best_price': best_price
        })

    supplier_info = [
        info for info in quote.supplier_info
        if info.supplier_id in cheapest_supplier_ids
    ]

    return render_template('quote_detail.html', quote=quote, lines=lines, supplier_info=supplier_info)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']  # Récupérer l'email
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Les mots de passe ne correspondent pas.')
            return render_template('register.html')

        if User.query.filter_by(username=username).first():
            flash('Ce nom d\'utilisateur est déjà pris.')
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('Cet email est déjà enregistré.')
            return render_template('register.html')

        new_user = User(username=username, email=email)  # Ajouter l'email ici
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('Compte créé avec succès. Connectez-vous.')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/edit_quote/<int:quote_id>', methods=['GET', 'POST'])
def edit_quote(quote_id):
    quote = Quote.query.options(
        joinedload(Quote.lines).joinedload(QuoteLine.supplier_prices),
        joinedload(Quote.supplier_info)
    ).get_or_404(quote_id)

    if request.method == 'POST':
        quote.creation_date = datetime.strptime(request.form['creation_date'], "%d/%m/%Y").date()
        quote.client_id = int(request.form['client_id'])
        quote.delivery_location = request.form['delivery_location']

        # --- LIGNES ---
        posted_line_ids = [int(x) for x in request.form.getlist('line_id[]') if x]
        existing_line_ids = {line.id for line in quote.lines}

        # Supprimer les lignes retirées
        for line in quote.lines[:]:
            if line.id not in posted_line_ids:
                db.session.delete(line)

        # Mettre à jour ou créer les lignes
        refs = request.form.getlist("supplier_ref[]")
        descs = request.form.getlist("description[]")
        qtys = request.form.getlist("quantity[]")
        cprices = request.form.getlist("client_price[]")
        pvcs = request.form.getlist("recommended_price[]")

        line_id_list = request.form.getlist('line_id[]')
        for i, ref in enumerate(refs):
            line_id = int(line_id_list[i]) if i < len(line_id_list) and line_id_list[i] else None
            if line_id:
                line = QuoteLine.query.get(line_id)
            else:
                line = QuoteLine(quote_id=quote.id)
                db.session.add(line)

            line.supplier_ref = ref
            line.description = descs[i]
            line.quantity = int(qtys[i])
            line.client_price = float(cprices[i])
            line.recommended_price = float(pvcs[i] or 0)

            # --- SUPPLIER PRICES ---
            supplier_ids = [k.replace("supplier_price_", "").replace("[]", "")
                            for k in request.form if k.startswith("supplier_price_")]

            for sid in supplier_ids:
                price_list = request.form.getlist(f"supplier_price_{sid}[]")
                dp_list = request.form.getlist(f"supplier_discount_percent_{sid}[]")
                da_list = request.form.getlist(f"supplier_discount_amount_{sid}[]")
                date_list = request.form.getlist(f"supplier_date_validate_promo_{sid}[]")
                qtt_list = request.form.getlist(f"supplier_qtt_stock_{sid}[]")

                if i < len(price_list):
                    sp = SupplierPrice.query.filter_by(quote_line_id=line.id, supplier_id=sid).first()
                    if not sp:
                        sp = SupplierPrice(quote_line_id=line.id, supplier_id=sid)
                        db.session.add(sp)

                    sp.price = float(price_list[i])
                    sp.discount_percent = float(dp_list[i] or 0)
                    sp.discount_amount = float(da_list[i] or 0)
                    sp.date_validate_promo = datetime.strptime(date_list[i], "%Y-%m-%d").date() if date_list[i] else None
                    sp.qtt_stock = int(qtt_list[i]) if qtt_list[i] else None

        # SUPPRIMER LES SupplierPrices si ligne supprimée ou fournisseur supprimé
        posted_supplier_ids = [k.replace("delivery_delay_", "") for k in request.form if k.startswith("delivery_delay_")]
        SupplierPrice.query.filter(SupplierPrice.quote_line_id.in_(existing_line_ids), ~SupplierPrice.supplier_id.in_(posted_supplier_ids)).delete(synchronize_session=False)

        # --- INFOS FOURNISSEUR ---
        existing_infos = {info.supplier_id: info for info in quote.supplier_info}
        form_supplier_ids = set(posted_supplier_ids)

        # Supprimer ceux retirés
        for sid in list(existing_infos):
            if sid not in form_supplier_ids:
                db.session.delete(existing_infos[sid])

        # Ajouter / Mettre à jour ceux du formulaire
        for sid in form_supplier_ids:
            delay = request.form.get(f"delivery_delay_{sid}")
            fee = request.form.get(f"delivery_fee_{sid}")

            info = existing_infos.get(sid)
            if not info:
                info = QuoteSupplierInfo(quote_id=quote.id, supplier_id=sid)
                db.session.add(info)

            info.delivery_delay = int(delay or 0)
            info.delivery_fee = float(fee or 0)

        db.session.commit()
        flash("Devis mis à jour.", "success")
        return redirect(url_for('quote_detail', quote_id=quote.id))

    # --- GET ---
    clients = Client.query.all()
    suppliers = Supplier.query.all()

    used_suppliers = (
        db.session.query(Supplier)
        .filter(Supplier.code.in_({sp.supplier_id for sp in SupplierPrice.query
                                   .join(QuoteLine, SupplierPrice.quote_line_id==QuoteLine.id)
                                   .filter(QuoteLine.quote_id==quote.id)}))
        .all()
    )
    initial_suppliers = [{'id': s.code, 'name': s.company} for s in used_suppliers]

    initial_lines = []
    for l in quote.lines:
        initial_lines.append({
            'id': l.id,
            'supplier_ref': l.supplier_ref,
            'description': l.description,
            'quantity': l.quantity,
            'client_price': l.client_price,
            'recommended_price': l.recommended_price or 0,
            'supplier_prices': [
                {
                    'supplier_id': sp.supplier_id,
                    'price': sp.price,
                    'discount_percent': sp.discount_percent,
                    'discount_amount': sp.discount_amount,
                    'date_validate_promo': sp.date_validate_promo.isoformat() if sp.date_validate_promo else '',
                    'qtt_stock': sp.qtt_stock
                } for sp in l.supplier_prices
            ]
        })

    initial_infos = [
        {
            'id': i.id,
            'supplier_id': i.supplier_id,
            'delivery_delay': i.delivery_delay,
            'delivery_fee': i.delivery_fee
        } for i in quote.supplier_info
    ]

    return render_template('edit_quote.html',
                           quote=quote,
                           clients=clients,
                           suppliers=suppliers,
                           initial_suppliers=initial_suppliers,
                           initial_lines=initial_lines,
                           initial_infos=initial_infos)




@app.route('/quotes/<int:quote_id>/update_supplier_info', methods=['POST'])
def update_supplier_info(quote_id):
    total_rows = int(request.form.get('total_rows', 0))
    for i in range(1, total_rows + 1):
        supplier_id = request.form.get(f'supplier_id_{i}')
        delivery_delay = request.form.get(f'delivery_delay_{i}')
        delivery_fee = request.form.get(f'delivery_fee_{i}')

        # Ici, tu mets à jour la base de données avec supplier_id, delivery_delay et delivery_fee
        # Exemple (SQLAlchemy) :
        info = SupplierInfo.query.filter_by(quote_id=quote_id, supplier_id=supplier_id).first()
        if info:
            info.delivery_delay = int(delivery_delay)
            info.delivery_fee = float(delivery_fee)
            db.session.commit()

    flash('Informations livraison mises à jour avec succès.', 'success')
    return redirect(url_for('quote_detail', quote_id=quote_id))
    
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            return redirect(url_for('index'))
        else:
            flash('Nom d\'utilisateur ou mot de passe incorrect')

    return render_template('login.html')


# Route pour afficher le formulaire de réinitialisation
@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.verify_reset_token(token)
    if not user:
        flash('Le lien de réinitialisation a expiré ou est invalide.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        password = request.form.get('password')
        user.set_password(password)
        db.session.commit()
        flash('Votre mot de passe a été réinitialisé avec succès.', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password.html', token=token)


# Route pour envoyer l'email avec le token de réinitialisation
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            token = user.get_reset_token()
            # Envoi de l'email avec le lien de réinitialisation
            send_reset_email(user, token)
            flash('Un email de réinitialisation a été envoyé.', 'success')
            return redirect(url_for('login'))
        else:
            flash('L\'email ne correspond à aucun utilisateur.', 'danger')
    return render_template('forgot_password.html')


# Fonction pour envoyer l'email (utilise Flask-Mail ici)
def send_reset_email(user, token):
    msg = Message('Réinitialisation de votre mot de passe',
                  sender='noreply@exemple.com',  # Adresse d'envoi
                  recipients=[user.email])
    msg.body = f'''Pour réinitialiser votre mot de passe, cliquez sur le lien suivant:
{url_for('reset_password', token=token, _external=True)}

Si vous n'avez pas demandé de réinitialisation, ignorez ce message.
'''
    mail.send(msg)


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
