import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import click # Adicionado para criar comandos

# --- Configuração Inicial ---

# Cria a aplicação Flask
app = Flask(__name__)

# Habilita o CORS para permitir que o seu front-end (em outra URL) se comunique com esta API
CORS(app)

# Configura o caminho do banco de dados.
# Ele usa a variável de ambiente DATABASE_URL se estiver no Render,
# ou cria um arquivo local 'taskflex.db' se estiver rodando no seu computador.
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///taskflex.db').replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializa a extensão do banco de dados
db = SQLAlchemy(app)


# --- Modelos do Banco de Dados (As "Tabelas") ---

# Modelo para a tabela de Usuários
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        """Cria um hash seguro para a senha."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verifica se a senha fornecida corresponde ao hash armazenado."""
        return check_password_hash(self.password_hash, password)

# Modelo para a tabela de Tarefas
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    due_date = db.Column(db.String(20))
    priority = db.Column(db.String(20), default='medium')
    completed = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # Chave estrangeira

    # Relacionamento para que se possa acessar o usuário dono da tarefa
    user = db.relationship('User', backref=db.backref('tasks', lazy=True))

    def to_dict(self):
        """Converte o objeto Task para um dicionário, facilitando a conversão para JSON."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'dueDate': self.due_date,
            'priority': self.priority,
            'completed': self.completed,
            'userId': self.user_id
        }


# --- Rotas da API (Os "Endpoints") ---

# Rota para cadastrar um novo usuário
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return jsonify({'message': 'Faltam dados obrigatórios'}), 400

    if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
        return jsonify({'message': 'Usuário ou e-mail já existe'}), 409

    new_user = User(username=username, email=email)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'Usuário criado com sucesso'}), 201

# Rota para fazer login
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        return jsonify({'message': 'Login bem-sucedido', 'userId': user.id, 'username': user.username}), 200
    
    return jsonify({'message': 'Credenciais inválidas'}), 401

# Rota para obter todas as tarefas de um usuário específico
@app.route('/api/users/<int:user_id>/tasks', methods=['GET'])
def get_user_tasks(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': 'Usuário não encontrado'}), 404
    
    tasks = Task.query.filter_by(user_id=user_id).all()
    return jsonify([task.to_dict() for task in tasks]), 200

# Rota para criar uma nova tarefa
@app.route('/api/tasks', methods=['POST'])
def add_task():
    data = request.get_json()
    
    if not data or 'title' not in data or 'userId' not in data:
        return jsonify({'message': 'Dados incompletos'}), 400

    user = User.query.get(data['userId'])
    if not user:
        return jsonify({'message': 'Usuário não encontrado'}), 404

    new_task = Task(
        title=data['title'],
        description=data.get('description', ''),
        due_date=data.get('dueDate'),
        priority=data.get('priority', 'medium'),
        user_id=data['userId']
    )
    db.session.add(new_task)
    db.session.commit()
    return jsonify(new_task.to_dict()), 201

# Rota para atualizar uma tarefa existente
@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    task = Task.query.get(task_id)
    if not task:
        return jsonify({'message': 'Tarefa não encontrada'}), 404

    data = request.get_json()
    task.title = data.get('title', task.title)
    task.description = data.get('description', task.description)
    task.due_date = data.get('dueDate', task.due_date)
    task.priority = data.get('priority', task.priority)
    task.completed = data.get('completed', task.completed)
    
    db.session.commit()
    return jsonify(task.to_dict()), 200

# Rota para deletar uma tarefa
@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    task = Task.query.get(task_id)
    if not task:
        return jsonify({'message': 'Tarefa não encontrada'}), 404

    db.session.delete(task)
    db.session.commit()
    return jsonify({'message': 'Tarefa deletada com sucesso'}), 200


# --- Comandos Especiais para o Servidor ---

@app.cli.command("init-db")
def init_db_command():
    """Limpa os dados existentes e cria novas tabelas."""
    db.create_all()
    click.echo("Base de dados inicializada.")

# O bloco abaixo não é mais necessário para o deploy, mas é bom para testes locais.
if __name__ == '__main__':
    app.run(debug=True)
