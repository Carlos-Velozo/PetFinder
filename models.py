from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class PetDesaparecido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    especie = db.Column(db.String(50), nullable=False)
    raca = db.Column(db.String(50))
    data_desaparecimento = db.Column(db.String(20))
    local_desaparecimento = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text)
    contato = db.Column(db.String(100), nullable=False)
    foto = db.Column(db.String(100))
    encontrado = db.Column(db.Boolean, default=False)
    data_encontrado = db.Column(db.String(20))
    local_encontrado = db.Column(db.String(200))
    avistado = db.Column(db.Boolean, default=False)
    data_avistamento = db.Column(db.String(20))
    local_avistamento = db.Column(db.String(200))
    foto_avistamento = db.Column(db.String(100))
    codigo_baixa = db.Column(db.String(10), default='123456')  # Código padrão
    confirmado_dono = db.Column(db.Boolean, default=False)
    avistamentos = db.relationship('Avistamento', backref='pet', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Pet {self.nome}>'

class Avistamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pet_id = db.Column(db.Integer, db.ForeignKey('pet_desaparecido.id'), nullable=False)
    data_avistamento = db.Column(db.String(20), nullable=False)
    local_avistamento = db.Column(db.String(200), nullable=False)
    coordenadas = db.Column(db.String(100))  # Formato: "latitude,longitude"
    foto_avistamento = db.Column(db.String(100))
    observacoes = db.Column(db.Text)

    def __repr__(self):
        return f'<Avistamento {self.id} do Pet {self.pet_id}>'