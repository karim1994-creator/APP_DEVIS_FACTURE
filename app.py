# Flask
from flask import Flask, current_app
from flask_login import LoginManager, current_user
from flask_mail import Mail
 
from flask_login import login_user

from flask import request, render_template, redirect, url_for, flash
from flask_login import login_user
from werkzeug.security import check_password_hash
from models import User
# Flask
from flask import (
    Flask, render_template, request, jsonify, redirect,
    url_for, flash, session, abort, current_app
)
from flask import Blueprint
# Sécurité mot de passe
from werkzeug.security import check_password_hash, generate_password_hash

# Modèles (base de données)
from models import (
    db, create_database, Client, Supplier, Quote, QuoteLine,
    SupplierPrice, QuoteSupplierInfo,User, SuiviQuotes
)

# Date et heure
from datetime import datetime

# Email via Flask-Mail
from flask_mail import Mail, Message

# Gestion des tokens (ex: reset password)
from itsdangerous import URLSafeTimedSerializer as Serializer, SignatureExpired

# Collections avancées
from collections import defaultdict

# SQLAlchemy : filtres et chargement
from sqlalchemy import func, or_, cast, String
from sqlalchemy.orm import joinedload

# Utilitaires maison
from utils import get_suivi_map

# Système de fichiers
import os
from flask import request, render_template_string
from sqlalchemy import or_, func, cast, String
from sqlalchemy.orm import joinedload
from flask_login import current_user
from flask_login import LoginManager
from flask_login import login_required
from flask_login import logout_user


# Modèles (base de données)
from models import (
    db, create_database, Client, Supplier, Quote, QuoteLine,
    SupplierPrice, QuoteSupplierInfo, User, SuiviQuotes
)

# Système de fichiers
import os

from flask import render_template
from sqlalchemy.orm import joinedload
from flask import jsonify
from flask_login import login_required
from flask import render_template
from sqlalchemy.orm import joinedload

# ---------------------------------------------------------
# 📦 Création de l’application Flask
# ---------------------------------------------------------
app = Flask(__name__)
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True
app.secret_key = 'b5f9a3408ed34d8a9d8a5bfa7c69598c'

# ---------------------------------------------------------
# 🔄 Configuration base de données : MySQL
# ---------------------------------------------------------
# Base MySQL déjà créée :
#   CREATE DATABASE app_devis CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
#
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL',
    'mysql+pymysql://root:root@localhost/app_devis?charset=utf8mb4'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_pre_ping": True,
    "pool_recycle": 280
}

# Initialisation SQLAlchemy
db.init_app(app)

# Chargement de configurations supplémentaires depuis config.py (optionnel)
app.config.from_object('config')

# Initialisation Flask-Mail
mail = Mail(app)

# ---------------------------------------------------------
# 📦 Création des tables si elles n’existent pas
# ---------------------------------------------------------
with app.app_context():
    try:
        db.create_all()  # crée toutes les tables définies dans models.py
        print("✅ Tables créées avec succès dans MySQL !")
    except Exception as e:
        print(f"⚠️ Erreur lors de la création des tables : {e}")

# ---------------------------------------------------------
# 🔐 Initialisation Flask-Login
# ---------------------------------------------------------
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@app.context_processor
def inject_user():
    return dict(current_user=current_user)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------------------------------------------------
# Routes (partie 1)
# ---------------------------------------------------------

@app.route('/')
@login_required
def index():
    return render_template('acceuil.html')


# Route pour ajouter un nouveau client, gère formulaire en GET et POST
@app.route('/add_client', methods=['GET', 'POST'])
@login_required
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
            registred_office=request.form['registred_office'],
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
# -------------------------------
# Routes Client
# -------------------------------

# Liste des clients avec recherche et pagination
@app.route('/clients')
@login_required
def list_clients():
    search = request.args.get('search', '', type=str)
    page = request.args.get('page', 1, type=int)
    per_page = 5

    query = Client.query

    if search:
        like_pattern = f"%{search}%"
        query = query.filter(
            (Client.first_name.ilike(like_pattern)) |
            (Client.last_name.ilike(like_pattern)) |
            (Client.company.ilike(like_pattern)) |
            (Client.registred_office.ilike(like_pattern)) |
            (Client.email.ilike(like_pattern)) |
            (Client.code.ilike(like_pattern)) |
            (Client.phone.ilike(like_pattern)) |
            (Client.mobile.ilike(like_pattern))
        )

    query = query.order_by(Client.last_name)
    pagination = query.paginate(page=page, per_page=per_page)

    return render_template(
        'list_clients.html',
        clients=pagination,
        search=search,
        page=page,
        total_pages=pagination.pages
    )

# Supprimer un client
@app.route('/delete-client/<string:client_code>', methods=['POST'])
@login_required
def delete_client(client_code):
    client = Client.query.get_or_404(client_code)

    if client.quotes:
        quote_numbers = [quote.quote_number for quote in client.quotes]
        quote_list = ', '.join(quote_numbers)
        flash(f"Vous ne pouvez pas supprimer ce client car il est utilisé dans les devis suivants : {quote_list}", 'danger')
        return redirect(url_for('list_clients'))

    db.session.delete(client)
    db.session.commit()
    flash('Client supprimé avec succès.', 'success')
    return redirect(url_for('list_clients'))

# Éditer un client
@app.route('/client/edit/<string:client_code>', methods=['GET', 'POST'])
@login_required
def edit_client(client_code):
    client = Client.query.get_or_404(client_code)

    if request.method == 'POST':
        client.code = request.form['code']
        client.civility = request.form['civility']
        client.last_name = request.form['last_name']
        client.first_name = request.form['first_name']
        client.email = request.form['email']
        client.job = request.form['job']
        client.company = request.form['company']
        client.address = request.form['address']
        client.registred_office = request.form['registred_office']
        client.phone = request.form['phone']
        client.mobile = request.form['mobile']
        db.session.commit()
        flash("Client mis à jour avec succès.", "success")
        return redirect(url_for('list_clients'))

    return render_template('edit_Client.html', client=client)

# Route pour afficher la liste des fournisseurs (avec recherche et pagination)
@app.route('/suppliers')
@login_required
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
            (Supplier.email.ilike(like_pattern)) |
            (Supplier.code.ilike(like_pattern)) |
            (Supplier.phone.ilike(like_pattern)) |     # ✅ Ajouté
            (Supplier.mobile.ilike(like_pattern))      # ✅ Ajouté
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


# ---------------------------------------------------------
# Fournisseurs
# ---------------------------------------------------------

# Route pour supprimer un fournisseur (POST) par son ID
@app.route('/delete-supplier/<int:supplier_id>', methods=['POST'])
@login_required
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

        flash(f"Vous ne pouvez pas supprimer ce fournisseur car il est utilisé dans les devis suivants : {quote_list}", 'danger')
        return redirect(url_for('list_suppliers'))

    db.session.delete(supplier)
    db.session.commit()
    flash('Fournisseur supprimé avec succès.', 'success')
    return redirect(url_for('list_suppliers'))


@app.route('/supplier/edit/<int:supplier_id>', methods=['GET', 'POST'])
@login_required
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
        supplier.phone = request.form['phone']
        supplier.mobile = request.form['mobile']
        db.session.commit()
        flash("Fournisseur mis à jour avec succès.", "success")
        return redirect(url_for('list_suppliers'))
    return render_template('edit_supplier.html', supplier=supplier)


@app.route('/add_supplier', methods=['GET', 'POST'])
@login_required
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
            phone=request.form['phone'],
            mobile=request.form['mobile'],
        )
        db.session.add(supplier)
        db.session.commit()
        flash("Fournisseur ajouté avec succès.", "success")
        return redirect(url_for('list_suppliers'))
    return render_template('add_supplier.html')


# ---------------------------------------------------------
# Devis
# ---------------------------------------------------------

@app.route('/create_quote', methods=['GET', 'POST'])
@login_required
def create_quote():
    if request.method == 'POST':
        try:
            today = datetime.today()
            today_str = today.strftime("%Y-%m-%d")

            # Numérotation auto si champ vide
            quote_number = request.form.get('quote_number')
            if not quote_number:
                count_today = Quote.query.filter(func.date(Quote.creation_date) == today.date()).count()
                quote_number = f"DV-{today_str}-{count_today + 1:03d}"

            # Date de création
            creation_date = datetime.strptime(request.form['creation_date'], "%Y-%m-%d").date()
            client_code = request.form['client_code']
            delivery_location = request.form['delivery_location']

            # Création du devis
            quote = Quote(
                quote_number=quote_number,
                creation_date=creation_date,
                client_code=client_code,
                delivery_location=delivery_location
            )
            db.session.add(quote)
            db.session.flush()

            # Données des lignes
            supplier_refs = request.form.getlist("supplier_ref[]")
            descriptions = request.form.getlist("description[]")
            quantities = request.form.getlist("quantity[]")
            client_prices = request.form.getlist("client_price[]")
            recommended_prices = request.form.getlist("recommended_price[]")

            # Identifiants fournisseurs dynamiques (codes comme F1, F2…)
            supplier_codes = []
            for key in request.form.keys():
                if key.startswith("supplier_price_"):
                    code = key.replace("supplier_price_", "").replace("[]", "")
                    if code not in supplier_codes:
                        supplier_codes.append(code)

            # Création des lignes de devis
            for i in range(len(supplier_refs)):
                line = QuoteLine(
                    quote_id=quote.id,
                    supplier_ref=supplier_refs[i],
                    description=descriptions[i],
                    quantity=int(quantities[i]) if quantities[i] else 0,
                    client_price=float(client_prices[i]) if client_prices[i] else 0.0,
                    recommended_price=float(recommended_prices[i]) if i < len(recommended_prices) and recommended_prices[i] else 0.0
                )
                db.session.add(line)
                db.session.flush()

                # Prix fournisseurs liés à cette ligne
                for code in supplier_codes:
                    supplier_obj = Supplier.query.filter_by(code=code).first()
                    if not supplier_obj:
                        continue

                    prices = request.form.getlist(f"supplier_price_{code}[]")
                    discount_percents = request.form.getlist(f"supplier_discount_percent_{code}[]")
                    discount_amounts = request.form.getlist(f"supplier_discount_amount_{code}[]")
                    validity_dates = request.form.getlist(f"supplier_validity_date_{code}[]")
                    stock_quantities = request.form.getlist(f"supplier_stock_{code}[]")

                    if i < len(prices) and prices[i]:
                        promo_date = None
                        if i < len(validity_dates) and validity_dates[i]:
                            try:
                                promo_date = datetime.strptime(validity_dates[i], "%Y-%m-%d").date()
                            except ValueError:
                                promo_date = None

                        db.session.add(SupplierPrice(
                            quote_line_id=line.id,
                            supplier_id=supplier_obj.id,
                            price=float(prices[i]),
                            discount_percent=float(discount_percents[i]) if i < len(discount_percents) and discount_percents[i] else 0.0,
                            discount_amount=float(discount_amounts[i]) if i < len(discount_amounts) and discount_amounts[i] else 0.0,
                            date_validate_promo=promo_date,
                            qtt_stock=int(stock_quantities[i]) if i < len(stock_quantities) and stock_quantities[i] else None
                        ))

            # Infos fournisseurs (délai + frais livraison)
            for code in supplier_codes:
                supplier_obj = Supplier.query.filter_by(code=code).first()
                if not supplier_obj:
                    continue
                delay = request.form.get(f"delivery_delay_{code}")
                fee = request.form.get(f"delivery_fee_{code}")
                if delay or fee:
                    db.session.add(QuoteSupplierInfo(
                        quote_id=quote.id,
                        supplier_id=supplier_obj.id,
                        delivery_delay=int(delay) if delay else None,
                        delivery_fee=float(fee) if fee else None
                    ))

            db.session.commit()
            flash("Devis enregistré avec succès.", "success")
            return redirect(url_for('quote_detail', quote_id=quote.id))

        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors de la création du devis : {e}", "danger")

    # GET : préparation du formulaire
    clients = Client.query.all()
    suppliers = Supplier.query.all()
    today = datetime.today()
    today_str = today.strftime("%Y-%m-%d")
    count_today = Quote.query.filter(func.date(Quote.creation_date) == today.date()).count()
    next_num = f"DV-{today_str}-{count_today + 1:03d}"

    selected_client_code = request.args.get('client_code', type=int)

    return render_template(
        "create_quote.html",
        clients=clients,
        suppliers=suppliers,
        quote_number=next_num,
        creation_date=today_str,
        selected_client_code=selected_client_code
    )



@app.route('/update_quote/<int:quote_id>', methods=['GET', 'POST'])
@login_required
def update_quote(quote_id):
    quote = Quote.query.get_or_404(quote_id)
    clients = Client.query.all()
    suppliers = Supplier.query.all()

    if request.method == 'POST':
        try:
            # Mise à jour des champs de Quote
            quote.quote_number = request.form.get('quote_number', quote.quote_number)
            quote.creation_date = datetime.strptime(request.form.get('creation_date'), '%Y-%m-%d').date()
            quote.client_code = int(request.form.get('client_code'))
            quote.delivery_location = request.form.get('delivery_location')

            # Mise à jour / création des QuoteLine
            line_ids = request.form.getlist('line_id[]')
            descriptions = request.form.getlist('description[]')
            quantities = request.form.getlist('quantity[]')
            client_prices = request.form.getlist('client_price[]')
            supplier_refs = request.form.getlist('supplier_ref[]')
            recommended_prices = request.form.getlist("recommended_price[]")

            existing_lines = {line.id: line for line in quote.lines}

            for i, line_id in enumerate(line_ids):
                if line_id.isdigit():
                    line = existing_lines.get(int(line_id))
                    if line:
                        line.description = descriptions[i]
                        line.quantity = int(quantities[i]) if quantities[i] else 0
                        line.client_price = float(client_prices[i]) if client_prices[i] else 0.0
                        line.supplier_ref = supplier_refs[i]
                        line.recommended_price = float(recommended_prices[i]) if i < len(recommended_prices) and recommended_prices[i] else 0.0
                else:
                    new_line = QuoteLine(
                        quote=quote,
                        description=descriptions[i],
                        quantity=int(quantities[i]) if quantities[i] else 0,
                        client_price=float(client_prices[i]) if client_prices[i] else 0.0,
                        supplier_ref=supplier_refs[i],
                        recommended_price=float(recommended_prices[i]) if i < len(recommended_prices) and recommended_prices[i] else 0.0
                    )
                    db.session.add(new_line)

            # Supprimer les lignes supprimées
            ids_posted = set(int(lid) for lid in line_ids if lid.isdigit())
            for line in quote.lines:
                if line.id not in ids_posted:
                    db.session.delete(line)

            # TODO : même logique à appliquer pour SupplierPrice et QuoteSupplierInfo
            # en fonction des champs envoyés par ton formulaire update.

            db.session.commit()
            flash('Devis mis à jour avec succès.', 'success')
            return redirect(url_for('show_quote', quote_id=quote.id))

        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors de la mise à jour du devis : {e}", "danger")

    return render_template('update_quote.html',
                           quote=quote,
                           clients=clients,
                           suppliers=suppliers)
@app.route('/quotes')
@login_required
def list_quotes():
    page = request.args.get('page', 1, type=int)
    per_page = 5
    search = request.args.get('search', '', type=str).strip()

    query = Quote.query

    if search:
        search_like = f"%{search}%"
        query = query.join(Client).filter(
            db.or_(
                Quote.quote_number.ilike(search_like),
                Client.first_name.ilike(search_like),
                Client.last_name.ilike(search_like),
                db.cast(Quote.date_heur_creation, db.String).ilike(search_like)
            )
        )

    # ✅ Ordonné par date_heur_creation (la plus récente en premier)
    pagination = query.order_by(Quote.date_heur_creation.desc()).paginate(page=page, per_page=per_page)
    quotes = pagination.items
    total_pages = pagination.pages

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
        search=search
    )



# ✅ Adapté pour MySQL
@app.route('/get_today_quote_count')
@login_required
def get_today_quote_count():
    today_str = datetime.utcnow().strftime('%d_%m_%Y')
    count = Quote.query.filter(
        db.func.date_format(Quote.creation_date, '%d_%m_%Y') == today_str
    ).count()
    return jsonify({'count': count})


@app.route('/quote/delete/<int:quote_id>', methods=['POST'])
@login_required
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
@login_required
def advance_status(quote_id):
    try:
        # Récupérer le devis
        quote = Quote.query.get_or_404(quote_id)

        # Récupérer le suivi le plus récent
        suivi = SuiviQuotes.query.filter_by(id_quote=quote_id).order_by(SuiviQuotes.id.desc()).first()
        if not suivi:
            suivi = SuiviQuotes(id_quote=quote_id, statut='validate_commande')
            db.session.add(suivi)
            db.session.commit()

        # Ordre des statuts
        statut_order = [
            'validate_commande',
            'commande',
            'reception',
            'control_reception',
            'livraison_client',
            'a_facturer',
            'facturation'
        ]
        try:
            current_index = statut_order.index(suivi.statut)
            new_statut = statut_order[current_index + 1] if current_index + 1 < len(statut_order) else 'Terminé'
        except ValueError:
            new_statut = 'Terminé'

        # Traduction des statuts en français
        statut_labels = {
            'validate_commande': 'Devis validé',
            'commande': 'Commandé',
            'reception': 'Réception',
            'control_reception': 'Contrôle de réception',
            'livraison_client': 'Livraison client',
            'a_facturer': 'Préparer la facture',
            'facturation': 'Facturation',
            'Terminé': 'Terminé'
        }
        new_statut_label = statut_labels.get(new_statut, new_statut)

        # Créer un nouveau suivi
        new_suivi = SuiviQuotes(id_quote=quote_id, statut=new_statut)
        db.session.add(new_suivi)
        db.session.commit()

        # Préparer les lignes du devis
        lines = []
        for line in quote.lines:
            suppliers = []
            for sp in line.supplier_prices:
                supplier_name = "Inconnu"
                if sp.supplier:
                    supplier_name = f"{sp.supplier.first_name or ''} {sp.supplier.last_name or ''}".strip() or "Inconnu"
                suppliers.append({
                    'supplier_name': supplier_name,
                    'price': sp.price or 0,
                    'discount_percent': sp.discount_percent or 0,
                    'discount_amount': sp.discount_amount or 0
                })
            lines.append({
                'supplier_ref': line.supplier_ref or "Réf inconnue",
                'description': line.description or "Produit inconnu",
                'quantity': line.quantity or 0,
                'client_price': line.client_price or 0,
                'recommended_price': line.recommended_price or 0,
                'total': (line.quantity or 0) * (line.client_price or 0),
                'suppliers': suppliers
            })

        # Nom, société et adresse de livraison
        client_name = "Client inconnu"
        client_company = ""
        delivery_address = quote.delivery_location or "Adresse inconnue"
        if quote.client:
            client_name = f"{quote.client.first_name or ''} {quote.client.last_name or ''}".strip() or "Client inconnu"
            client_company = quote.client.company or ""

        # Retour JSON pour JS
        return jsonify({
            'success': True,
            'new_statut': new_statut,               # valeur interne
            'new_statut_label': new_statut_label,   # valeur lisible
            'quote_number': quote.quote_number,
            'client_name': client_name,
            'client_company': client_company,
            'delivery_location': delivery_address,  
            'lines': lines
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500








@app.route('/quote/<int:quote_id>')
@login_required
def quote_detail(quote_id):
    quote = Quote.query.get_or_404(quote_id)

    supplier_totals = {}
    for line in quote.lines:
        for sp in line.supplier_prices:
            sid = sp.supplier_id
            if not sid:
                continue
            # prix fournisseur brut * quantité
            supplier_totals[sid] = supplier_totals.get(sid, 0) + sp.price * line.quantity

    # Recherche du fournisseur le moins cher
    cheapest_supplier = None
    cheapest_supplier_id = None
    cheapest_supplier_name = "NA"

    if supplier_totals:
        cheapest_supplier_id = min(supplier_totals, key=supplier_totals.get)
        cheapest_supplier = Supplier.query.filter_by(code=cheapest_supplier_id).first()
        cheapest_supplier_name = (
            cheapest_supplier.company
            if (cheapest_supplier and cheapest_supplier.company)
            else f"Fournisseur {cheapest_supplier_id}"
        )

    filtered_lines = []
    total_client = total_recommended = total_fournisseur = total_marge = 0

    # Parcours des lignes de devis
    for line in quote.lines:
        sp = None
        if cheapest_supplier_id:
            sp = next(
                (sp for sp in line.supplier_prices if sp.supplier_id == cheapest_supplier_id),
                None,
            )

        client_price = line.client_price or 0
        sp_price = sp.price if sp else 0
        discount_percent = sp.discount_percent if sp else 0
        discount_amount = sp.discount_amount if sp else 0

        # ✅ Calcul correct du prix fournisseur net
        net_price = (
            sp_price - (sp_price * discount_percent / 100) - discount_amount if sp else 0
        )

        # Calcul des marges et totaux
        margin = round(client_price - net_price, 2)
        fournisseur_total = net_price * (line.quantity or 0)
        recommended_total = (line.recommended_price or 0) * (line.quantity or 0)
        client_total = client_price * (line.quantity or 0)
        marge_total = margin * (line.quantity or 0)

        # Envoi des données au template
        filtered_lines.append({
            'supplier_ref': line.supplier_ref,
            'description': line.description,
            'quantity': line.quantity,
            'client_price': line.client_price,
            'recommended_price': line.recommended_price,
            'best_price': {
                'date_validate_promo': sp.date_validate_promo if sp else None,
                'qtt_stock': sp.qtt_stock if sp else None,
                'price': net_price if sp else None,
                'company': cheapest_supplier_name
            },
            'margin': margin
        })

        total_client += client_total
        total_recommended += recommended_total
        total_fournisseur += fournisseur_total
        total_marge += marge_total

    # Informations de livraison fournisseur
    supplier_info = []
    total_delivery_fee = 0.0
    total_with_delivery = total_client
    total_fournisseur_with_delivery = total_fournisseur

    if cheapest_supplier_id:
        supplier_info = QuoteSupplierInfo.query.filter_by(
            quote_id=quote_id, supplier_id=cheapest_supplier_id
        ).all()
        total_delivery_fee = sum(info.delivery_fee for info in supplier_info) if supplier_info else 0
        total_with_delivery = total_client + total_delivery_fee
        total_fournisseur_with_delivery = total_fournisseur + total_delivery_fee

    return render_template(
        'quote_detail.html',
        quote=quote,
        lines=filtered_lines,
        total_client=total_client,
        total_recommended=total_recommended,
        total_fournisseur=total_fournisseur,
        total_marge=total_marge,
        supplier_info=supplier_info,
        supplier_name=cheapest_supplier_name,
        total_delivery_fee=total_delivery_fee,
        total_with_delivery=total_with_delivery,
        total_fournisseur_with_delivery=total_fournisseur_with_delivery
    )


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Les mots de passe ne correspondent pas.', "danger")
            return render_template('register.html')

        if User.query.filter_by(username=username).first():
            flash('Ce nom d\'utilisateur est déjà pris.', "danger")
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('Cet email est déjà enregistré.', "danger")
            return render_template('register.html')

        # Vérifier si c'est l'admin
        is_admin = (email == "f.bertolini@atlantis-evolution.com")

        new_user = User(
            username=username,
            email=email,
            is_active=is_admin,   # l'admin est actif immédiatement
            is_admin=is_admin
        )
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        if is_admin:
            flash('Compte administrateur créé avec succès.', "success")
        else:
            flash('Compte créé avec succès. En attente de validation par l’administrateur.', "info")

        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Les mots de passe ne correspondent pas.', "danger")
            return render_template('add_user.html')

        if User.query.filter_by(username=username).first():
            flash('Ce nom d\'utilisateur est déjà pris.', "danger")
            return render_template('add_user.html')

        if User.query.filter_by(email=email).first():
            flash('Cet email est déjà enregistré.', "danger")
            return render_template('add_user.html')

        new_user = User(
            username=username,
            email=email,
            is_active=False,   # en attente de validation par défaut
            is_admin=False     # pas admin sauf si tu veux ajouter une case à cocher
        )
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        flash('Utilisateur ajouté avec succès. Il doit être validé avant de se connecter.', "success")

        return redirect(url_for('admin_users'))  # retour à l’espace admin

    return render_template('add_user.html')

@app.route('/edit_quote/<int:quote_id>', methods=['GET', 'POST'])
@login_required
def edit_quote(quote_id):
    quote = Quote.query.options(
        joinedload(Quote.lines).joinedload(QuoteLine.supplier_prices),
        joinedload(Quote.supplier_info)
    ).get_or_404(quote_id)

    if request.method == 'POST':
        # Mise à jour du numéro de devis (modification possible)
        new_quote_number = request.form.get('quote_number', '').strip()
        if new_quote_number:
            quote.quote_number = new_quote_number

        quote.creation_date = datetime.strptime(request.form['creation_date'], "%Y-%m-%d").date()
        quote.client_code = request.form['client_code']
        quote.delivery_location = request.form['delivery_location']

        # --- LIGNES ---
        posted_line_ids = [int(x) for x in request.form.getlist('line_id[]') if x]
        existing_line_ids = {line.id for line in quote.lines}

        # Supprimer les lignes retirées + leurs supplier_prices
        for line in quote.lines[:]:
            if line.id not in posted_line_ids:
                for sp in line.supplier_prices:
                    db.session.delete(sp)
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

        # SUPPRIMER LES SupplierPrices si fournisseur retiré
        posted_supplier_ids = [int(k.replace("delivery_delay_", "")) for k in request.form if k.startswith("delivery_delay_")]
        SupplierPrice.query.filter(
            SupplierPrice.quote_line_id.in_(existing_line_ids),
            ~SupplierPrice.supplier_id.in_(posted_supplier_ids)
        ).delete(synchronize_session=False)

        # --- INFOS FOURNISSEUR ---
        existing_infos = {info.supplier_id: info for info in quote.supplier_info}
        form_supplier_ids = set(posted_supplier_ids)

        for sid in list(existing_infos):
            if sid not in form_supplier_ids:
                db.session.delete(existing_infos[sid])

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

    # Fournisseurs utilisés dans le devis
    used_suppliers = (
        db.session.query(Supplier)
        .filter(Supplier.id.in_(
            db.session.query(SupplierPrice.supplier_id)
            .join(QuoteLine, SupplierPrice.quote_line_id == QuoteLine.id)
            .filter(QuoteLine.quote_id == quote.id)
        ))
        .all()
    )
    initial_suppliers = [{'id': s.id, 'name': s.company} for s in used_suppliers]

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

    selected_client = Client.query.get(quote.client_code)

    return render_template(
        'edit_quote.html',
        quote=quote,
        clients=clients,
        suppliers=suppliers,
        initial_suppliers=initial_suppliers,
        initial_lines=initial_lines,
        initial_infos=initial_infos,
        selected_client=selected_client
    )




@app.route('/view_quote/<int:quote_id>')
@login_required
def view_quote(quote_id):
    quote = Quote.query.options(
        joinedload(Quote.lines).joinedload(QuoteLine.supplier_prices),
        joinedload(Quote.client),
        joinedload(Quote.supplier_info)
    ).get_or_404(quote_id)

    suppliers = Supplier.query.all()
    supplier_dict = {s.id: s.company for s in suppliers}

    used_supplier_ids = {
        sp.supplier_id for line in quote.lines for sp in line.supplier_prices
    }

    supplier_totals = {sid: 0 for sid in used_supplier_ids}
    total_vente_client = 0

    for line in quote.lines:
        qty = line.quantity
        total_vente_client += line.client_price * qty

        for sp in line.supplier_prices:
            net_price = sp.price
            if sp.discount_percent:
                net_price *= (1 - sp.discount_percent / 100)
            if sp.discount_amount:
                net_price -= sp.discount_amount
            if net_price < 0:
                net_price = 0
            supplier_totals[sp.supplier_id] += net_price * qty

    # ✅ Si aucun prix fournisseur : affichage message + bouton
    quote_incomplete = False
    best_supplier_id = None
    best_supplier_name = "Inconnu"
    best_supplier_total = 0
    initial_suppliers = []
    initial_lines = []
    total_marge = 0

    if not supplier_totals:
        quote_incomplete = True
    else:
        best_supplier_id = min(supplier_totals, key=supplier_totals.get)
        best_supplier_name = supplier_dict.get(best_supplier_id, "Inconnu")
        best_supplier_total = supplier_totals[best_supplier_id]

        initial_suppliers = [{'id': best_supplier_id, 'name': best_supplier_name}]

        for line in quote.lines:
            qty = line.quantity
            vente_client_total = line.client_price * qty

            sp = next((sp for sp in line.supplier_prices if sp.supplier_id == best_supplier_id), None)

            if sp:
                net_price = sp.price
                if sp.discount_percent:
                    net_price *= (1 - sp.discount_percent / 100)
                if sp.discount_amount:
                    net_price -= sp.discount_amount
                if net_price < 0:
                    net_price = 0
                vente_fournisseur_total = net_price * qty
            else:
                vente_fournisseur_total = 0

            marge = vente_client_total - vente_fournisseur_total
            total_marge += marge if marge is not None else 0

            initial_lines.append({
                'supplier_ref': line.supplier_ref,
                'description': line.description,
                'quantity': qty,
                'client_price': line.client_price,
                'marge': marge,
            'supplier_prices': [
                {
                    'supplier_id': sp.supplier_id,
                    'price': sp.price or 0,
                    'discount_percent': sp.discount_percent or 0,
                    'discount_amount': sp.discount_amount or 0,
                    'date_validate_promo': sp.date_validate_promo.isoformat() if sp.date_validate_promo else '',
                    'qtt_stock': sp.qtt_stock or 0
                } for sp in line.supplier_prices  # <-- corrigé


                ]
            })

    initial_infos = [
        {
            'supplier_id': info.supplier_id,
            'delivery_delay': info.delivery_delay,
            'delivery_fee': info.delivery_fee
        } for info in quote.supplier_info
    ]

    def get_supplier_name_by_id(supplier_id):
        return supplier_dict.get(supplier_id, supplier_id)

    return render_template('view_quote.html',
                           quote=quote,
                           initial_suppliers=initial_suppliers,
                           initial_lines=initial_lines,
                           initial_infos=initial_infos,
                           total_vente_client=total_vente_client,
                           total_marge=total_marge,
                           get_supplier_name_by_id=get_supplier_name_by_id,
                           quote_incomplete=quote_incomplete)



@app.route('/quotes/<int:quote_id>/update_supplier_info', methods=['POST'])
@login_required
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
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username).first()

        if user:
            if not user.is_active:
                flash("Votre compte est en attente de validation par l'administrateur.", "warning")
                return redirect(url_for('login'))

            if check_password_hash(user.password_hash, password):
                login_user(user)
                flash(f"Bienvenue {user.username} !", "success")
                return redirect(url_for('index'))
            else:
                flash("Nom d'utilisateur ou mot de passe incorrect", "danger")
        else:
            flash("Nom d'utilisateur ou mot de passe incorrect", "danger")

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
@login_required
def logout():
    logout_user()  # déconnecte l'utilisateur via Flask-Login
    return redirect(url_for('login'))


@app.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        flash("Accès interdit.", "danger")
        return redirect(url_for('index'))

    pending_users = User.query.filter_by(is_active=False).all()
    active_users = User.query.filter_by(is_active=True).all()

    return render_template(
        'espace_admin.html',
        pending_users=pending_users,
        active_users=active_users
    )


@app.route('/admin/validate/<int:user_id>', methods=['POST'])
@login_required
def validate_user(user_id):
    if not current_user.is_admin:
        flash("Accès interdit.", "danger")
        return redirect(url_for('index'))

    user = User.query.get_or_404(user_id)
    user.is_active = True
    db.session.commit()
    flash(f"Utilisateur {user.username} validé avec succès.", "success")
    return redirect(url_for('admin_users'))


@app.route('/admin/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        flash("Accès interdit.", "danger")
        return redirect(url_for('index'))

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash(f"Utilisateur {user.username} supprimé.", "warning")
    return redirect(url_for('admin_users'))


@app.route('/admin/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if not current_user.is_admin:
        flash("Accès interdit.", "danger")
        return redirect(url_for('index'))

    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form.get('password')  # mot de passe optionnel

        # Vérifications uniques
        if User.query.filter(User.username == username, User.id != user.id).first():
            flash("Ce nom d'utilisateur est déjà pris.", "danger")
            return redirect(url_for('edit_user', user_id=user.id))
        if User.query.filter(User.email == email, User.id != user.id).first():
            flash("Cet email est déjà utilisé.", "danger")
            return redirect(url_for('edit_user', user_id=user.id))

        user.username = username
        user.email = email
        if password:
            user.set_password(password)

        db.session.commit()
        flash(f"Utilisateur {user.username} mis à jour.", "success")
        return redirect(url_for('admin_users'))

    return render_template('edit_user.html', user=user)

@app.route("/quotes/<int:quote_id>/suppliers_infos")
@login_required
def get_suppliers_infos(quote_id):
    # Récupérer le devis
    quote = Quote.query.get_or_404(quote_id)

    # Récupérer les fournisseurs liés à ce devis
    supplier_infos = QuoteSupplierInfo.query.filter_by(quote_id=quote_id).all()
    suppliers = []
    for info in supplier_infos:
        s = Supplier.query.get(info.supplier_id)
        if s:
            suppliers.append({
                "id": s.id,
                "company": s.company or f"Fournisseur {s.id}",
                "email": s.email or ""
            })

    # Récupérer les lignes du devis
    lines = []
    for l in QuoteLine.query.filter_by(quote_id=quote_id).all():
        lines.append({
            "supplier_ref": l.supplier_ref,
            "description": l.description,
            "quantity": l.quantity,
            "client_price": l.client_price,
            "recommended_price": l.recommended_price
        })

    return jsonify({
        "suppliers": suppliers,
        "lines": lines
    })

@app.route('/contact')
@login_required
def contact():
    clients = Client.query.all()
    suppliers = Supplier.query.all()
    return render_template('contact.html', clients=clients, suppliers=suppliers)


if __name__ == '__main__':
    app.run(debug=True)
