# models.py
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer
from flask import current_app
from datetime import datetime
from sqlalchemy.orm import relationship
from sqlalchemy import Enum


db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

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


class Client(db.Model):
    __tablename__ = 'clients'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(100))
    civility = db.Column(db.String(20))
    last_name = db.Column(db.String(100))
    first_name = db.Column(db.String(100))
    email = db.Column(db.String(200))
    job = db.Column(db.String(100))
    company = db.Column(db.String(200))
    address = db.Column(db.String(255))
    city = db.Column(db.String(100))
    phone = db.Column(db.String(50))
    mobile = db.Column(db.String(50))

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
    city = db.Column(db.String(100))
    phone = db.Column(db.String(50))
    mobile = db.Column(db.String(50))

class Quote(db.Model):
    __tablename__ = 'quotes'
    id = db.Column(db.Integer, primary_key=True)
    quote_number = db.Column(db.String(50), nullable=False)
    creation_date = db.Column(db.Date, nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    delivery_location = db.Column(db.String(255), nullable=False)

    client = db.relationship('Client', backref='quotes')

class QuoteLine(db.Model):
    __tablename__ = 'quote_lines'
    id = db.Column(db.Integer, primary_key=True)
    quote_id = db.Column(db.Integer, db.ForeignKey('quotes.id'), nullable=False)
    supplier_ref = db.Column(db.String(100))
    description = db.Column(db.String(255))
    quantity = db.Column(db.Integer)
    client_price = db.Column(db.Float)

    quote = db.relationship('Quote', backref='lines')

class SupplierPrice(db.Model):
    __tablename__ = 'supplier_prices'
    id = db.Column(db.Integer, primary_key=True)
    quote_line_id = db.Column(db.Integer, db.ForeignKey('quote_lines.id'), nullable=False)
    supplier_id = db.Column(db.String(100))
    price = db.Column(db.Float)
    recommended_price= db.Column(db.Float, default=0.0)
    discount_percent = db.Column(db.Float, default=0.0)
    discount_amount = db.Column(db.Float, default=0.0)  
    date_validate_promo=db.Column(db.Date, nullable=True)
    qtt_stock =   db.Column(db.Integer, nullable=True)

    quote_line = db.relationship('QuoteLine', backref='supplier_prices')

class QuoteSupplierInfo(db.Model):
    __tablename__ = 'quote_supplier_info'
    id = db.Column(db.Integer, primary_key=True)
    quote_id = db.Column(db.Integer, db.ForeignKey('quotes.id'), nullable=False)
    supplier_id = db.Column(db.String(100))
    delivery_delay = db.Column(db.Integer)
    delivery_fee = db.Column(db.Float)

    quote = db.relationship('Quote', backref='supplier_info')

class SuiviQuotes(db.Model):
    __tablename__ = 'suivi_quotes'
    id = db.Column(db.Integer, primary_key=True)
    id_quote = db.Column(db.Integer, db.ForeignKey('quotes.id'))
    
    statut_enum = ('initiale','validate_commande', 'commande', 'reception', 'control_reception', 'livraison_client', 'a_facturer', 'facturation', 'Terminé','cloture')
    statut = db.Column(Enum(*statut_enum, name='statut_enum'), nullable=False)
   
    quote = db.relationship('Quote', backref='suivi')

def create_database():
    db.create_all()