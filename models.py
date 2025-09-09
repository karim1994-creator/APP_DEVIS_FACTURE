from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer
from flask import current_app
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy.orm import relationship
from sqlalchemy import Enum
from flask_login import UserMixin

db = SQLAlchemy()

# Fuseau horaire France
def now_paris():
    return datetime.now(ZoneInfo("Europe/Paris"))

# -------------------------------
# Utilisateurs
# -------------------------------
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    is_active = db.Column(db.Boolean, default=False, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    date_heur_creation = db.Column(db.DateTime, default=now_paris, nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_reset_token(self, expires_sec=1800):
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id})

    @staticmethod
    def verify_reset_token(token, expires_sec=1800):
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, max_age=expires_sec)
        except Exception:
            return None
        return User.query.get(data['user_id'])


# -------------------------------
# Clients
# -------------------------------
class Client(db.Model):
    __tablename__ = 'clients'
    code = db.Column(db.String(50), primary_key=True, default='0')
    civility = db.Column(db.String(20))
    last_name = db.Column(db.String(100))
    first_name = db.Column(db.String(100))
    email = db.Column(db.String(200))
    job = db.Column(db.String(100))
    company = db.Column(db.String(200))
    address = db.Column(db.String(255))
    registred_office = db.Column(db.String(100))
    phone = db.Column(db.String(50))
    mobile = db.Column(db.String(50))

    date_heur_creation = db.Column(db.DateTime, default=now_paris, nullable=False)


# -------------------------------
# Fournisseurs
# -------------------------------
class Supplier(db.Model):
    __tablename__ = 'suppliers'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(100))
    civility = db.Column(db.String(20))
    last_name = db.Column(db.String(100))
    first_name = db.Column(db.String(100))
    email = db.Column(db.String(200))
    job = db.Column(db.String(100))
    company = db.Column(db.String(200))
    address = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    mobile = db.Column(db.String(50))

    date_heur_creation = db.Column(db.DateTime, default=now_paris, nullable=False)


# -------------------------------
# Devis
# -------------------------------
class Quote(db.Model):
    __tablename__ = 'quotes'
    id = db.Column(db.Integer, primary_key=True)
    quote_number = db.Column(db.String(50), unique=True, nullable=False)
    creation_date = db.Column(db.Date, nullable=False)
    client_code = db.Column(db.String(50), db.ForeignKey('clients.code'), nullable=False)
    delivery_location = db.Column(db.String(255), nullable=False)

    date_heur_creation = db.Column(db.DateTime, default=now_paris, nullable=False)

    client = db.relationship('Client', backref='quotes')


# -------------------------------
# Lignes de devis
# -------------------------------
class QuoteLine(db.Model):
    __tablename__ = 'quote_lines'
    id = db.Column(db.Integer, primary_key=True)
    quote_id = db.Column(db.Integer, db.ForeignKey('quotes.id'), nullable=False)
    supplier_ref = db.Column(db.String(100))
    description = db.Column(db.String(255))
    quantity = db.Column(db.Integer)
    client_price = db.Column(db.Float)
    recommended_price = db.Column(db.Float, default=0.0)

    date_heur_creation = db.Column(db.DateTime, default=now_paris, nullable=False)

    quote = db.relationship('Quote', backref='lines')


# -------------------------------
# Prix fournisseur
# -------------------------------
class SupplierPrice(db.Model):
    __tablename__ = 'supplier_prices'
    id = db.Column(db.Integer, primary_key=True)
    quote_line_id = db.Column(db.Integer, db.ForeignKey('quote_lines.id'), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    price = db.Column(db.Float)
    discount_percent = db.Column(db.Float, default=0.0)
    discount_amount = db.Column(db.Float, default=0.0)
    date_validate_promo = db.Column(db.Date, nullable=True)
    qtt_stock = db.Column(db.Integer, nullable=True)

    date_heur_creation = db.Column(db.DateTime, default=now_paris, nullable=False)

    quote_line = db.relationship('QuoteLine', backref='supplier_prices')
    supplier = db.relationship('Supplier')


# -------------------------------
# Infos supplémentaires fournisseur / devis
# -------------------------------
class QuoteSupplierInfo(db.Model):
    __tablename__ = 'quote_supplier_info'
    id = db.Column(db.Integer, primary_key=True)
    quote_id = db.Column(db.Integer, db.ForeignKey('quotes.id'), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    delivery_delay = db.Column(db.Integer)
    delivery_fee = db.Column(db.Float)

    date_heur_creation = db.Column(db.DateTime, default=now_paris, nullable=False)

    quote = db.relationship('Quote', backref='supplier_info')
    supplier = db.relationship('Supplier')


# -------------------------------
# Suivi des devis
# -------------------------------
class SuiviQuotes(db.Model):
    __tablename__ = 'suivi_quotes'
    id = db.Column(db.Integer, primary_key=True)
    id_quote = db.Column(db.Integer, db.ForeignKey('quotes.id'))

    statut_enum = ('initiale','validate_commande', 'commande', 'reception', 
                   'control_reception', 'livraison_client', 'a_facturer', 
                   'facturation', 'terminé','cloture')
    statut = db.Column(Enum(*statut_enum, name='statut_enum'), nullable=False)

    date_heur_creation = db.Column(db.DateTime, default=now_paris, nullable=False)

    quote = db.relationship('Quote', backref='suivi')


# -------------------------------
# Création de la BDD
# -------------------------------
def create_database():
    db.create_all()
