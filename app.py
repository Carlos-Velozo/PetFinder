from flask import Flask, render_template, request, redirect, url_for, flash
from flask import jsonify
from werkzeug.utils import secure_filename
from models import db, PetDesaparecido, Avistamento  
from datetime import datetime
import os
import secrets

app = Flask(__name__)

# Configurações IMPORTANTES
app.secret_key = 'sua_chave_secreta_muito_segura_aqui'  # Substitua por uma chave real
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Inicialização do banco de dados
db.init_app(app)
with app.app_context():
    db.create_all()
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Funções auxiliares
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Rotas principais
@app.route('/')
def index():
    pets = PetDesaparecido.query.filter_by(encontrado=False).all()
    return render_template('index.html', pets=pets)

# Atualize a rota /cadastrar para lidar com JSON e formulário
@app.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar_pet():
    if request.method == 'GET':
        return render_template('cadastro.html')  # Se quiser uma página específica
        
    # Processar POST (tanto para formulário quanto para JSON)
    try:
        if 'foto' not in request.files and not request.is_json:
            return redirect(request.url)

        # Obter dados do formulário ou JSON
        if request.is_json:
            data = request.get_json()
            filename = None  # Ou implemente upload via base64 se necessário
        else:
            data = request.form
            file = request.files['foto']
            filename = None

            if file.filename != '':
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                else:
                    return "Tipo de arquivo não permitido", 400

        novo_pet = PetDesaparecido(
            nome=data['nome'],
            especie=data['especie'],
            raca=data.get('raca', ''),
            data_desaparecimento=data.get('data_desaparecimento'),
            local_desaparecimento=data['local_desaparecimento'],
            descricao=data.get('descricao', ''),
            contato=data['contato'],
            foto=filename,
            codigo_baixa='123456'  # Código padrão como solicitado
        )

        db.session.add(novo_pet)
        db.session.commit()

        # Resposta adequada ao tipo de requisição
        if request.is_json:
            return jsonify({
                'success': True,
                'message': 'Pet cadastrado com sucesso',
                'codigo_baixa': '123456'
            }), 201
        else:
            flash('Pet cadastrado com sucesso! Código de baixa: 123456', 'success')
            return redirect(url_for('index', success='true'))

    except Exception as e:
        if request.is_json:
            return jsonify({'success': False, 'error': str(e)}), 400
        else:
            flash(f'Erro ao cadastrar pet: {str(e)}', 'danger')
            return redirect(request.url)

@app.route('/descricao/<int:id>')
def descricao_pet(id):
    pet = PetDesaparecido.query.get_or_404(id)
    return {
        'id': pet.id,
        'nome': pet.nome,
        'especie': pet.especie,
        'raca': pet.raca,
        'data_desaparecimento': pet.data_desaparecimento,
        'local_desaparecimento': pet.local_desaparecimento,
        'descricao': pet.descricao,
        'contato': pet.contato,
        'foto': pet.foto
    }

# Rotas para status dos pets
@app.route('/encontrado', methods=['POST'])
def marcar_encontrado():
    try:
        pet_id = request.form['petId']
        codigo = request.form['codigo_baixa']
        
        pet = PetDesaparecido.query.get(pet_id)
        if not pet:
            raise ValueError("Pet não encontrado")
            
        if codigo != '123456':  # Verificação do código padrão
            raise ValueError("Código de baixa inválido")
            
        pet.encontrado = True
        pet.data_encontrado = request.form['dataEncontrado']
        pet.local_encontrado = request.form['localEncontrado']
        db.session.commit()
        
        flash('Pet marcado como encontrado com sucesso!', 'success')
        return redirect(url_for('index'))
        
    except Exception as e:
        flash(f'Erro: {str(e)}', 'danger')
        return redirect(url_for('gerenciar_encontrados'))

@app.route('/pets_desaparecidos')
def pets_desaparecidos():
    search = request.args.get('search', '')
    status = request.args.get('status', 'desaparecido')  # Mudei o padrão para 'desaparecido'
    
    query = PetDesaparecido.query
    
    # Filtro por status
    if status == 'desaparecido':
        query = query.filter_by(encontrado=False, avistado=False)
    elif status == 'avistado':
        query = query.filter_by(avistado=True, encontrado=False)
    elif status == 'encontrado':
        query = query.filter_by(encontrado=True)
    # Removi o 'all' para simplificar
    
    # Filtro por pesquisa
    if search:
        query = query.filter(
            PetDesaparecido.nome.ilike(f'%{search}%') | 
            PetDesaparecido.local_desaparecimento.ilike(f'%{search}%') | 
            PetDesaparecido.raca.ilike(f'%{search}%')
        )
    
    pets = query.order_by(PetDesaparecido.data_desaparecimento.desc()).all()
    
    return render_template('index.html', 
                         pets=pets, 
                         search_term=search,
                         status_filter=status)

# Rota para visualização de pet
@app.route('/pet/<int:id>')
def ver_pet(id):
    pet = PetDesaparecido.query.get_or_404(id)
    # Ordena os avistamentos por data (do mais recente para o mais antigo)
    avistamentos = sorted(pet.avistamentos, key=lambda x: x.data_avistamento, reverse=True)
    return render_template('pet.html', pet=pet, avistamentos=avistamentos)

@app.route('/pet/<int:pet_id>/avistamento', methods=['POST'])
def reportar_avistamento(pet_id):
    try:
        pet = PetDesaparecido.query.get_or_404(pet_id)
        
        # Verifica se as coordenadas foram enviadas
        if not request.form.get('coordenadas'):
            raise ValueError("Localização no mapa é obrigatória")
        
        # Processar upload da foto
        foto_avistamento = None
        if 'foto_avistamento' in request.files:
            file = request.files['foto_avistamento']
            if file.filename != '':
                if file and allowed_file(file.filename):
                    # Garante que o diretório existe
                    avistamentos_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'avistamentos')
                    os.makedirs(avistamentos_dir, exist_ok=True)
                    
                    # Gera um nome único para o arquivo
                    filename = secure_filename(f"avist_{pet_id}_{datetime.now().timestamp()}.{file.filename.split('.')[-1]}")
                    file.save(os.path.join(avistamentos_dir, filename))
                    foto_avistamento = f"avistamentos/{filename}"
                else:
                    raise ValueError("Tipo de arquivo não permitido")

        # Criar novo avistamento
        novo_avistamento = Avistamento(
            pet_id=pet_id,
            data_avistamento=request.form['data_avistamento'],
            local_avistamento=request.form['local_avistamento'],
            coordenadas=request.form['coordenadas'],
            foto_avistamento=foto_avistamento,
            observacoes=request.form.get('observacoes', '')
        )

        # Atualizar status do pet
        pet.avistado = True
        pet.data_avistamento = request.form['data_avistamento']
        pet.local_avistamento = request.form['local_avistamento']
        pet.foto_avistamento = foto_avistamento

        db.session.add(novo_avistamento)
        db.session.commit()

        flash('Avistamento registrado com sucesso!', 'success')
        return redirect(url_for('ver_pet', id=pet_id))

    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Erro ao registrar avistamento: {str(e)}', exc_info=True)
        flash(f'Erro ao registrar avistamento: {str(e)}', 'danger')
        return redirect(url_for('ver_pet', id=pet_id))
    
@app.route('/mapa_avistamento/<int:avistamento_id>')
def mapa_avistamento(avistamento_id):
    avistamento = Avistamento.query.get_or_404(avistamento_id)
    return render_template('mapa_avistamento.html', avistamento=avistamento)

if __name__ == '__main__':
    app.run(debug=True)