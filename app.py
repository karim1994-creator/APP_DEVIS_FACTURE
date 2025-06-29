from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from werkzeug.security import check_password_hash, generate_password_hash
from models import db, create_database, Client, Supplier, Quote, QuoteLine, SupplierPrice, QuoteSupplierInfo, \
    SuiviQuotes
from datetime import datetime
from flask_mail import Message, Mail
from itsdangerous import URLSafeTimedSerializer as Serializer
from flask import current_app
from itsdangerous import SignatureExpired
from flask import render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash
from models import db, User
from itsdangerous import URLSafeTimedSerializer as Serializer
from flask import current_app
from itsdangerous import SignatureExpired
from collections import defaultdict
from datetime import datetime, date
from sqlalchemy import func, or_
from flask import request
from sqlalchemy.orm import joinedload
from sqlalchemy import or_, func

statut_order = [
    'validate_commande',  # Valider
    'commande',  # Commander
    'reception',  # Réception
    'control_reception',  # Contrôle réception
    'livraison_client',  # Livraison client
    'a_facturer',  # À facturer
    'facturation',  # Facturation
    'cloture'  # cloturé
]

app = Flask(__name__)
app.secret_key = 'b5f9a3408ed34d8a9d8a5bfa7c69598c'  # Change ça avec une vraie clé secrète
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
app.config.from_object('config')
mail = Mail(app)

with app.app_context():
    create_database()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/add_client', methods=['GET', 'POST'])
def add_client():
    if request.method == 'POST':
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
        db.session.add(client)
        db.session.commit()
        return redirect(url_for('list_clients'))
    return render_template('add_client.html')


@app.route('/clients')
def list_clients():
    search = request.args.get('search', '', type=str)
    page = request.args.get('page', 1, type=int)
    per_page = 5

    query = Client.query

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

    # Trier (exemple : par nom)
    query = query.order_by(Client.last_name)

    pagination = query.paginate(page=page, per_page=per_page)

    return render_template(
        'list_clients.html',
        clients=pagination,
        search=search,
        page=page,
        total_pages=pagination.pages
    )


@app.route('/delete-client/<int:client_id>', methods=['POST'])
def delete_client(client_id):
    client = Client.query.get_or_404(client_id)

    # Vérifie si le client a des devis
    if client.quotes:
        quote_numbers = [quote.quote_number for quote in client.quotes]
        quote_list = ', '.join(quote_numbers)
        flash(f"Vous ne pouvez pas supprimer ce client car il est utilisé dans les devis suivants : {quote_list}",
              'danger')
        return redirect(url_for('list_clients'))

        # Sinon, supprimer
    db.session.delete(client)
    db.session.commit()
    flash('Client supprimé avec succès.', 'success')
    return redirect(url_for('list_clients'))


@app.route('/client/edit/<int:client_id>', methods=['GET', 'POST'])
def edit_client(client_id):
    client = Client.query.get_or_404(client_id)
    if request.method == 'POST':
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
    return render_template('edit_client.html', client=client)


@app.route('/suppliers')
def list_suppliers():
    search = request.args.get('search', '', type=str)
    page = request.args.get('page', 1, type=int)
    per_page = 5

    query = Supplier.query

    if search:
        # Recherche insensible à la casse sur plusieurs colonnes
        like_pattern = f"%{search}%"
        query = query.filter(
            (Supplier.first_name.ilike(like_pattern)) |
            (Supplier.last_name.ilike(like_pattern)) |
            (Supplier.company.ilike(like_pattern)) |
            (Supplier.city.ilike(like_pattern)) |
            (Supplier.email.ilike(like_pattern)) |
            (Supplier.code.ilike(like_pattern))
        )

    # Trier (exemple : par nom)
    query = query.order_by(Supplier.last_name)

    pagination = query.paginate(page=page, per_page=per_page)

    return render_template(
        'list_suppliers.html',
        suppliers=pagination,
        search=search,
        page=page,
        total_pages=pagination.pages
    )


@app.route('/delete-supplier/<int:supplier_id>', methods=['POST'])
def delete_supplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)

    # Vérifie si le supplier est référencé dans SupplierPrice ou QuoteSupplierInfo
    supplier_price_links = SupplierPrice.query.filter_by(supplier_id=supplier_id).all()
    quote_supplier_info_links = QuoteSupplierInfo.query.filter_by(supplier_id=supplier_id).all()

    if supplier_price_links or quote_supplier_info_links:
        # Récupère les numéros de devis concernés
        quote_ids = {link.quote_line.quote_id for link in supplier_price_links}
        quote_ids.update(link.quote_id for link in quote_supplier_info_links)
        quotes = Quote.query.filter(Quote.id.in_(quote_ids)).all()
        quote_numbers = [quote.quote_number for quote in quotes]
        quote_list = ', '.join(quote_numbers)
        flash(f"Vous ne pouvez pas supprimer ce fournisseur car il est utilisé dans les devis suivants : {quote_list}",
              'danger')
        return redirect(url_for('list_suppliers'))

    # Suppression possible
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
            line = QuoteLine(
                quote_id=quote.id,
                supplier_ref=supplier_refs[i],
                description=descriptions[i],
                quantity=int(quantities[i]),
                client_price=float(client_prices[i])
            )
            db.session.add(line)
            db.session.flush()

            for sid in supplier_ids:
                prices = request.form.getlist(f"supplier_price_{sid}[]")
                if i < len(prices):
                    # Récupère les champs de remise pour ce fournisseur
                    discount_percents = request.form.getlist(f"supplier_discount_percent_{sid}[]")
                    discount_amounts = request.form.getlist(f"supplier_discount_amount_{sid}[]")

                    db.session.add(SupplierPrice(
                        quote_line_id=line.id,
                        supplier_id=sid,
                        price=float(prices[i]),
                        recommended_price=float(discount_percents[i]) if i < len(discount_percents) and
                                                                         discount_percents[i] else 0.0,
                        discount_percent=float(discount_percents[i]) if i < len(discount_percents) and
                                                                        discount_percents[i] else 0.0,
                        discount_amount=float(discount_amounts[i]) if i < len(discount_amounts) and discount_amounts[
                            i] else 0.0
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
                    func.cast(Quote.creation_date, db.String).like(f"%{query}%"),
                )
            ).all()
    else:
        results = Quote.query.options(joinedload(Quote.client), joinedload(Quote.lines)).all()

    return render_template('partials/quote_items.html', quotes=results)


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
                else:
                    # Nouvelle ligne
                    new_line = QuoteLine(
                        quote=quote,
                        description=descriptions[i],
                        quantity=int(quantities[i]),
                        client_price=float(client_prices[i]),
                        supplier_ref=supplier_refs[i]
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
            # Par exemple, pour chaque fournisseur lié au devis
            qsi_ids = request.form.getlist('qsi_id[]')
            qsi_supplier_ids = request.form.getlist('qsi_supplier_id[]')
            qsi_delays = request.form.getlist('qsi_delivery_delay[]')
            qsi_fees = request.form.getlist('qsi_delivery_fee[]')

            existing_qsi = {info.id: info for info in quote.supplier_info}

            for i, qsi_id in enumerate(qsi_ids):
                if qsi_id.isdigit():
                    info = existing_qsi.get(int(qsi_id))
                    if info:
                        info.supplier_id = qsi_supplier_ids[i]
                        info.delivery_delay = int(qsi_delays[i]) if qsi_delays[i] else None
                        info.delivery_fee = float(qsi_fees[i]) if qsi_fees[i] else None
                else:
                    new_info = QuoteSupplierInfo(
                        quote_id=quote.id,
                        supplier_id=qsi_supplier_ids[i],
                        delivery_delay=int(qsi_delays[i]) if qsi_delays[i] else None,
                        delivery_fee=float(qsi_fees[i]) if qsi_fees[i] else None,
                    )
                    db.session.add(new_info)

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
    quote = Quote.query.get_or_404(quote_id)

    if request.method == 'POST':
        # Mise à jour des données du devis (Quote)
        quote_number = request.form.get('quote_number')
        creation_date_str = request.form.get('creation_date')
        client_id = request.form.get('client_id')
        delivery_location = request.form.get('delivery_location')

        if creation_date_str:
            try:
                quote.creation_date = datetime.strptime(creation_date_str, "%d-%m-%Y").date()
            except ValueError:
                pass  # gérer l'erreur selon besoin

        quote.quote_number = quote_number or quote.quote_number
        quote.client_id = int(client_id) if client_id else quote.client_id
        quote.delivery_location = delivery_location or quote.delivery_location

        # Gestion des lignes (QuoteLine)
        # On récupère la liste des ids des lignes existantes soumises
        submitted_line_ids = request.form.getlist('quote_line_id[]')  # ids existantes + '' pour nouvelles

        # Pour garder trace des lignes à garder
        current_line_ids = set()

        for i, line_id in enumerate(submitted_line_ids):
            line_id = line_id.strip()
            supplier_ref = request.form.getlist('supplier_ref[]')[i]
            description = request.form.getlist('description[]')[i]
            quantity = request.form.getlist('quantity[]')[i]
            client_price = request.form.getlist('client_price[]')[i]

            if line_id:  # Ligne existante -> mise à jour
                line = QuoteLine.query.filter_by(id=int(line_id), quote_id=quote.id).first()
                if line:
                    # Si on a un champ pour suppression, gérer ici (exemple : checkbox 'delete_line_<id>')
                    if request.form.get(f'delete_line_{line_id}') == 'on':
                        # Suppression cascade des SupplierPrices liés
                        SupplierPrice.query.filter_by(quote_line_id=line.id).delete()
                        db.session.delete(line)
                        continue  # passe à la ligne suivante

                    # Mise à jour de la ligne
                    line.supplier_ref = supplier_ref
                    line.description = description
                    line.quantity = int(quantity) if quantity.isdigit() else 0
                    line.client_price = float(client_price) if client_price else 0.0
                    current_line_ids.add(line.id)

            else:
                # Nouvelle ligne -> création
                new_line = QuoteLine(
                    quote_id=quote.id,
                    supplier_ref=supplier_ref,
                    description=description,
                    quantity=int(quantity) if quantity.isdigit() else 0,
                    client_price=float(client_price) if client_price else 0.0
                )
                db.session.add(new_line)
                db.session.flush()  # flush pour avoir new_line.id

                current_line_ids.add(new_line.id)

            # Gestion des SupplierPrice par ligne
            # On peut avoir un système similaire pour gérer les prix par fournisseur sur chaque ligne
            supplier_ids = request.form.getlist('supplier_ids[]')  # Liste de fournisseurs visibles dans le formulaire

            for sid in supplier_ids:
                price_key = f'supplier_price_{sid}[]'
                discount_percent_key = f'supplier_discount_percent_{sid}[]'
                discount_amount_key = f'supplier_discount_amount_{sid}[]'

                prices = request.form.getlist(price_key)
                discount_percents = request.form.getlist(discount_percent_key)
                discount_amounts = request.form.getlist(discount_amount_key)

                # Correspondance index i dans listes des lignes
                if i < len(prices):
                    price_str = prices[i]
                    discount_percent_str = discount_percents[i] if i < len(discount_percents) else '0'
                    discount_amount_str = discount_amounts[i] if i < len(discount_amounts) else '0'

                    # Trouver SupplierPrice existante ou créer nouvelle
                    sp = SupplierPrice.query.filter_by(
                        quote_line_id=line.id if line_id else new_line.id,
                        supplier_id=sid
                    ).first()

                    if sp is None:
                        sp = SupplierPrice(
                            quote_line_id=line.id if line_id else new_line.id,
                            supplier_id=sid
                        )
                        db.session.add(sp)

                    sp.price = float(price_str) if price_str else 0.0
                    sp.discount_percent = float(discount_percent_str) if discount_percent_str else 0.0
                    sp.discount_amount = float(discount_amount_str) if discount_amount_str else 0.0

        # Supprimer les lignes supprimées (non soumises)
        all_line_ids_in_db = {line.id for line in quote.lines}
        to_delete = all_line_ids_in_db - current_line_ids
        for line_id in to_delete:
            line = QuoteLine.query.get(line_id)
            if line:
                # Suppression des SupplierPrice liés
                SupplierPrice.query.filter_by(quote_line_id=line.id).delete()
                db.session.delete(line)

        # Gestion QuoteSupplierInfo (infos fournisseurs devis)
        supplier_ids = request.form.getlist('supplier_ids[]')
        for sid in supplier_ids:
            delay = request.form.get(f'delivery_delay_{sid}')
            fee = request.form.get(f'delivery_fee_{sid}')

            qsi = QuoteSupplierInfo.query.filter_by(quote_id=quote.id, supplier_id=sid).first()
            if qsi is None:
                qsi = QuoteSupplierInfo(quote_id=quote.id, supplier_id=sid)
                db.session.add(qsi)

            qsi.delivery_delay = int(delay) if delay and delay.isdigit() else None
            qsi.delivery_fee = float(fee) if fee else None

        db.session.commit()
        flash("Devis mis à jour avec succès.", "success")
        return redirect(url_for('quote_detail', quote_id=quote.id))

    # GET : afficher formulaire avec données existantes
    clients = Client.query.all()
    suppliers = Supplier.query.all()

    # Récupérer les infos QuoteSupplierInfo existantes pour pré-remplir
    quote_supplier_info = {qsi.supplier_id: qsi for qsi in quote.supplier_info}

    return render_template(
        'edit_quote.html',
        quote=quote,
        clients=clients,
        suppliers=suppliers,
        quote_supplier_info=quote_supplier_info
    )

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
