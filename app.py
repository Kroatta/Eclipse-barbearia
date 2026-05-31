"""
Barbearia Eclipse - Sistema de Agendamento
TCC - Backend com Flask + SQLite
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
import sqlite3
import os
from datetime import datetime, date, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = 'eclipse_barbearia_tcc_2024_secret_key'

# ─── EMAIL ───────────────────────────────────────────────────────────────────
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'seuemail@gmail.com'      # Troque pelo seu Gmail
app.config['MAIL_PASSWORD'] = 'sua_senha_de_app'        # Senha de App do Google
app.config['MAIL_DEFAULT_SENDER'] = 'seuemail@gmail.com'
mail = Mail(app)
serializer = URLSafeTimedSerializer(app.secret_key)

# ─── DATABASE ───────────────────────────────────────────────────────────────

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'eclipse.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    c = conn.cursor()

    c.executescript('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            telefone TEXT,
            is_admin INTEGER DEFAULT 0,
            criado_em TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS barbeiros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            especialidade TEXT NOT NULL,
            bio TEXT,
            nivel TEXT DEFAULT 'Pleno',
            foto TEXT DEFAULT '',
            ativo INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS servicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            descricao TEXT,
            preco REAL NOT NULL,
            duracao INTEGER NOT NULL,
            categoria TEXT DEFAULT 'Corte',
            ativo INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS agendamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            barbeiro_id INTEGER NOT NULL,
            servico_id INTEGER NOT NULL,
            data_hora TEXT NOT NULL,
            status TEXT DEFAULT 'confirmado',
            observacoes TEXT,
            nome_avulso TEXT,
            criado_em TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY(barbeiro_id) REFERENCES barbeiros(id),
            FOREIGN KEY(servico_id) REFERENCES servicos(id)
        );

        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            descricao TEXT,
            quantidade INTEGER DEFAULT 0,
            unidade TEXT DEFAULT 'un',
            ativo INTEGER DEFAULT 1,
            criado_em TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS uso_produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            quantidade INTEGER DEFAULT 1,
            observacao TEXT,
            criado_em TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY(produto_id) REFERENCES produtos(id),
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS avaliacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            barbeiro_id INTEGER NOT NULL,
            agendamento_id INTEGER UNIQUE NOT NULL,
            nota INTEGER NOT NULL CHECK(nota BETWEEN 1 AND 5),
            comentario TEXT,
            publica INTEGER DEFAULT 0,
            criado_em TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY(barbeiro_id) REFERENCES barbeiros(id),
            FOREIGN KEY(agendamento_id) REFERENCES agendamentos(id)
        );
    ''')

    # Seed admin
    admin = c.execute("SELECT id FROM usuarios WHERE email='admin@eclipse.com'").fetchone()
    if not admin:
        c.execute("""
            INSERT INTO usuarios (nome, email, senha, telefone, is_admin)
            VALUES (?, ?, ?, ?, 1)
        """, ('Administrador Eclipse', 'admin@eclipse.com',
              generate_password_hash('admin123'), '(61) 99999-0000'))

    # Seed barbeiros
    if not c.execute("SELECT id FROM barbeiros LIMIT 1").fetchone():
        barbeiros = [
            ('Ricardo Silva', 'Navalha Clássica, Visagismo', 'Especialista em cortes clássicos e barbas tradicionais com toalha quente.', 'Sênior'),
            ('Fabio Mendes', 'Fade Moderno, Barboterapia', 'Focado no design de barba e visagismo facial para um visual imponente.', 'Especialista'),
            ('Lucas Santos', 'Tribal Art, Hair Design', 'Referência em degradês, cortes urbanos e técnicas de pigmentação capilar.', 'Pleno'),
        ]
        c.executemany("INSERT INTO barbeiros (nome, especialidade, bio, nivel) VALUES (?,?,?,?)", barbeiros)

    # Seed serviços
    if not c.execute("SELECT id FROM servicos LIMIT 1").fetchone():
        servicos = [
            ('Corte de Cabelo', 'Corte personalizado com acabamento em navalha e lavagem premium.', 50.0, 45, 'Corte'),
            ('Barba Completa', 'Toalha quente, terapia de óleos e contorno perfeito.', 40.0, 30, 'Barba'),
            ('Eclipse Experience', 'Pacote premium: Corte, Barba e Massagem Facial com bebida à escolha.', 80.0, 75, 'Combo'),
            ('Coloração', 'Cobertura de brancos ou mudança de tom com pigmentos de alta qualidade.', 120.0, 60, 'Tratamento'),
            ('Selagem Capilar', 'Redução de volume e brilho intenso para fios saudáveis.', 150.0, 90, 'Tratamento'),
            ('Pezinho e Contorno', 'Manutenção rápida para manter o visual limpo entre cortes.', 20.0, 15, 'Manutenção'),
        ]
        c.executemany("INSERT INTO servicos (nome, descricao, preco, duracao, categoria) VALUES (?,?,?,?,?)", servicos)

    # Seed funcionários vinculados aos barbeiros
    if not c.execute("SELECT id FROM usuarios WHERE is_funcionario=1 LIMIT 1").fetchone():
        from datetime import datetime, timedelta
        funcs = [
            ('Ricardo Silva', 'ricardo.func@eclipse.com', 'Navalha Clássica, Visagismo'),
            ('Fabio Mendes',  'fabio.func@eclipse.com',  'Fade Moderno, Barboterapia'),
            ('Lucas Santos',  'lucas.func@eclipse.com',  'Tribal Art, Hair Design'),
        ]
        for nome, email, esp in funcs:
            if not c.execute("SELECT id FROM usuarios WHERE email=?", (email,)).fetchone():
                c.execute("INSERT INTO usuarios (nome, email, senha, is_funcionario) VALUES (?,?,?,1)",
                          (nome, email, generate_password_hash('func123')))
                func_id = c.lastrowid
                c.execute("UPDATE barbeiros SET usuario_id=? WHERE nome=?", (func_id, nome))

    # Seed produtos de exemplo
    if not c.execute("SELECT id FROM produtos LIMIT 1").fetchone():
        produtos = [
            ('Pomada Modeladora', 'Fixacao forte e brilho intenso', 15, 'un'),
            ('Oleo de Barba',     'Hidratacao e amolecimento para barbas', 20, 'fr'),
            ('Shampoo Masculino', 'Limpeza profunda para couro cabeludo', 30, 'fr'),
            ('Cera Capilar',      'Acabamento natural e flexivel', 10, 'un'),
            ('Balm para Barba',   'Hidratante e condicionador de barba', 12, 'un'),
        ]
        c.executemany("INSERT INTO produtos (nome, descricao, quantidade, unidade) VALUES (?,?,?,?)", produtos)

    # Seed retiradas de exemplo
    if not c.execute("SELECT id FROM uso_produtos LIMIT 1").fetchone():
        import random
        from datetime import datetime, timedelta
        funcs = c.execute("SELECT id FROM usuarios WHERE is_funcionario=1").fetchall()
        prods = c.execute("SELECT id FROM produtos").fetchall()
        if funcs and prods:
            obs_lista = ['Usado no cliente', 'Servico de barba', 'Corte + barba', 'Finalizacao', '']
            for _ in range(35):
                dias_atras = random.randint(0, 30)
                data = (datetime.now() - timedelta(days=dias_atras)).strftime('%Y-%m-%d %H:%M')
                c.execute("INSERT INTO uso_produtos (produto_id, usuario_id, quantidade, observacao, criado_em) VALUES (?,?,?,?,?)",
                          (random.choice(prods)[0], random.choice(funcs)[0],
                           random.randint(1, 3), random.choice(obs_lista), data))

    # Migrações para bancos existentes
    for sql in [
        "ALTER TABLE agendamentos ADD COLUMN nome_avulso TEXT",
        "ALTER TABLE usuarios ADD COLUMN is_funcionario INTEGER DEFAULT 0",
        "ALTER TABLE barbeiros ADD COLUMN usuario_id INTEGER",
    ]:
        try:
            c.execute(sql)
        except Exception:
            pass

    conn.commit()
    conn.close()

# ─── CACHE CONTROL ──────────────────────────────────────────────────────────

@app.after_request
def no_cache(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# ─── DECORATORS ─────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Faça login para continuar.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def funcionario_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if not session.get('is_funcionario') and not session.get('is_admin'):
            flash('Acesso restrito a funcionarios.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if not session.get('is_admin'):
            flash('Acesso restrito a administradores.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

# ─── ROTAS PÚBLICAS ─────────────────────────────────────────────────────────

@app.route('/')
def index():
    db = get_db()
    servicos = db.execute("SELECT * FROM servicos WHERE ativo=1 LIMIT 6").fetchall()
    barbeiros = db.execute("""
        SELECT b.*, COALESCE(ROUND(AVG(av.nota), 1), 0) as nota_media, COUNT(av.id) as total_avaliacoes
        FROM barbeiros b
        LEFT JOIN avaliacoes av ON b.id = av.barbeiro_id
        WHERE b.ativo=1
        GROUP BY b.id
    """).fetchall()
    depoimentos = db.execute("""
        SELECT av.comentario, av.nota, b.nome as barbeiro_nome, u.nome as cliente_nome
        FROM avaliacoes av
        JOIN barbeiros b ON av.barbeiro_id = b.id
        JOIN usuarios u ON av.usuario_id = u.id
        WHERE av.nota >= 4 AND av.comentario != '' AND LENGTH(TRIM(av.comentario)) > 8
        ORDER BY av.nota DESC, RANDOM()
        LIMIT 6
    """).fetchall()
    db.close()
    return render_template('client/index.html', servicos=servicos, barbeiros=barbeiros, depoimentos=depoimentos)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        senha = request.form.get('senha', '')
        db = get_db()
        user = db.execute("SELECT * FROM usuarios WHERE email=? AND is_admin=0", (email,)).fetchone()
        db.close()
        if user and check_password_hash(user['senha'], senha):
            session['user_id'] = user['id']
            session['user_nome'] = user['nome']
            session['is_admin'] = False
            session['is_funcionario'] = bool(user['is_funcionario'])
            flash(f'Bem-vindo de volta, {user["nome"].split()[0]}!', 'success')
            if user['is_funcionario']:
                return redirect(url_for('funcionario_agenda'))
            return redirect(url_for('meus_agendamentos'))
        flash('Email ou senha incorretos.', 'error')
    return render_template('client/login.html')

@app.route('/esqueci-senha', methods=['GET', 'POST'])
def esqueci_senha():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        db = get_db()
        user = db.execute("SELECT * FROM usuarios WHERE email=? AND is_admin=0", (email,)).fetchone()
        db.close()
        if user:
            token = serializer.dumps(email, salt='reset-senha')
            reset_url = url_for('resetar_senha', token=token, _external=True)
            try:
                msg = Message('Recuperacao de Senha — Barbearia Eclipse', recipients=[email])
                msg.html = f'''
                <div style="font-family:sans-serif;max-width:480px;margin:auto;background:#131313;color:#e5e2e1;padding:40px;border:1px solid #4d4635;">
                  <h1 style="color:#f2ca50;font-size:28px;margin-bottom:8px;">ECLIPSE</h1>
                  <p style="color:#d0c5af;font-size:12px;text-transform:uppercase;letter-spacing:4px;margin-bottom:32px;">Barbearia Premium</p>
                  <h2 style="font-size:20px;margin-bottom:16px;">Recuperacao de Senha</h2>
                  <p style="color:#d0c5af;margin-bottom:24px;">Clique no botao abaixo para redefinir sua senha. O link expira em <strong style="color:#f2ca50;">1 hora</strong>.</p>
                  <a href="{reset_url}" style="display:inline-block;background:#f2ca50;color:#131313;padding:14px 32px;text-decoration:none;font-weight:bold;text-transform:uppercase;letter-spacing:2px;margin-bottom:24px;">
                    Redefinir Senha
                  </a>
                  <p style="color:#99907c;font-size:12px;">Se voce nao solicitou a recuperacao de senha, ignore este email.</p>
                </div>
                '''
                mail.send(msg)
            except Exception:
                flash('Erro ao enviar email. Verifique as configuracoes de email no servidor.', 'error')
                return render_template('client/esqueci_senha.html')
        flash('Se o email estiver cadastrado, voce recebera um link de recuperacao em breve.', 'success')
        return redirect(url_for('login'))
    return render_template('client/esqueci_senha.html')

@app.route('/resetar-senha/<token>', methods=['GET', 'POST'])
def resetar_senha(token):
    try:
        email = serializer.loads(token, salt='reset-senha', max_age=3600)
    except SignatureExpired:
        flash('Link expirado. Solicite um novo.', 'error')
        return redirect(url_for('esqueci_senha'))
    except BadSignature:
        flash('Link invalido. Solicite um novo.', 'error')
        return redirect(url_for('esqueci_senha'))
    if request.method == 'POST':
        nova_senha = request.form.get('senha', '')
        confirmar = request.form.get('confirmar', '')
        if len(nova_senha) < 6:
            flash('A senha deve ter pelo menos 6 caracteres.', 'error')
            return render_template('client/resetar_senha.html', token=token)
        if nova_senha != confirmar:
            flash('As senhas nao coincidem.', 'error')
            return render_template('client/resetar_senha.html', token=token)
        db = get_db()
        db.execute("UPDATE usuarios SET senha=? WHERE email=?",
                   (generate_password_hash(nova_senha), email))
        db.commit()
        db.close()
        flash('Senha alterada com sucesso! Faca login.', 'success')
        return redirect(url_for('login'))
    return render_template('client/resetar_senha.html', token=token)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('is_admin'):
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        senha = request.form.get('senha', '')
        db = get_db()
        user = db.execute("SELECT * FROM usuarios WHERE email=? AND is_admin=1", (email,)).fetchone()
        db.close()
        if user and check_password_hash(user['senha'], senha):
            session['user_id'] = user['id']
            session['user_nome'] = user['nome']
            session['is_admin'] = True
            return redirect(url_for('admin_dashboard'))
        flash('Credenciais invalidas ou sem permissao de administrador.', 'error')
    return render_template('admin/login.html')

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip()
        senha = request.form.get('senha', '')
        telefone = request.form.get('telefone', '').strip()
        if not all([nome, email, senha]):
            flash('Preencha todos os campos obrigatórios.', 'error')
            return render_template('client/cadastro.html')
        db = get_db()
        existe = db.execute("SELECT id FROM usuarios WHERE email=?", (email,)).fetchone()
        if existe:
            db.close()
            flash('Este email já está cadastrado.', 'error')
            return render_template('client/cadastro.html')
        db.execute("INSERT INTO usuarios (nome, email, senha, telefone) VALUES (?,?,?,?)",
                   (nome, email, generate_password_hash(senha), telefone))
        db.commit()
        db.close()
        flash('Cadastro realizado com sucesso! Faça login.', 'success')
        return redirect(url_for('login'))
    return render_template('client/cadastro.html')

@app.route('/logout')
def logout():
    was_admin = session.get('is_admin')
    session.clear()
    flash('Voce saiu da sua conta.', 'success')
    if was_admin:
        return redirect(url_for('admin_login'))
    return redirect(url_for('login'))

@app.route('/agendar', methods=['GET', 'POST'])
@login_required
def agendar():
    db = get_db()
    servicos = db.execute("SELECT * FROM servicos WHERE ativo=1").fetchall()
    barbeiros = db.execute("SELECT * FROM barbeiros WHERE ativo=1").fetchall()
    if request.method == 'POST':
        servico_id = request.form.get('servico_id')
        barbeiro_id = request.form.get('barbeiro_id')
        data = request.form.get('data', '')
        hora = request.form.get('hora', '')
        observacoes = request.form.get('observacoes', '')
        if not all([servico_id, barbeiro_id, data, hora]):
            flash('Preencha todos os campos obrigatórios.', 'error')
            db.close()
            return render_template('client/agendar.html', servicos=servicos, barbeiros=barbeiros)
        data_hora = f"{data} {hora}"
        try:
            data_hora_dt = datetime.strptime(data_hora, '%Y-%m-%d %H:%M')
        except ValueError:
            flash('Data ou horário inválido.', 'error')
            db.close()
            return render_template('client/agendar.html', servicos=servicos, barbeiros=barbeiros)
        servico = db.execute("SELECT duracao FROM servicos WHERE id=?", (servico_id,)).fetchone()
        if not servico:
            flash('Serviço inválido.', 'error')
            db.close()
            return render_template('client/agendar.html', servicos=servicos, barbeiros=barbeiros)
        novo_fim = data_hora_dt + timedelta(minutes=servico['duracao'])
        conflitos = db.execute("""
            SELECT a.data_hora, s.duracao
            FROM agendamentos a JOIN servicos s ON a.servico_id=s.id
            WHERE a.barbeiro_id=? AND date(a.data_hora)=? AND a.status!='cancelado'
        """, (barbeiro_id, data)).fetchall()
        for c in conflitos:
            c_start = datetime.strptime(c['data_hora'], '%Y-%m-%d %H:%M')
            c_end = c_start + timedelta(minutes=c['duracao'])
            if data_hora_dt < c_end and novo_fim > c_start:
                flash(f'Horário indisponível. O profissional está ocupado das {c_start.strftime("%H:%M")} às {c_end.strftime("%H:%M")}. Escolha outro horário.', 'error')
                db.close()
                return render_template('client/agendar.html', servicos=servicos, barbeiros=barbeiros)
        db.execute("""
            INSERT INTO agendamentos (usuario_id, barbeiro_id, servico_id, data_hora, observacoes)
            VALUES (?,?,?,?,?)
        """, (session['user_id'], barbeiro_id, servico_id, data_hora, observacoes))
        db.commit()
        db.close()
        flash('Agendamento realizado com sucesso!', 'success')
        return redirect(url_for('meus_agendamentos'))
    from datetime import date as _date
    db.close()
    return render_template('client/agendar.html', servicos=servicos, barbeiros=barbeiros,
                           now_date=_date.today().isoformat())

@app.route('/meus-agendamentos')
@login_required
def meus_agendamentos():
    db = get_db()
    agendamentos = db.execute("""
        SELECT a.*, s.nome as servico_nome, s.preco, s.duracao,
               b.nome as barbeiro_nome, u.nome as usuario_nome
        FROM agendamentos a
        JOIN servicos s ON a.servico_id = s.id
        JOIN barbeiros b ON a.barbeiro_id = b.id
        JOIN usuarios u ON a.usuario_id = u.id
        WHERE a.usuario_id = ?
        ORDER BY a.data_hora DESC
    """, (session['user_id'],)).fetchall()
    avaliados = db.execute(
        "SELECT agendamento_id, nota FROM avaliacoes WHERE usuario_id=?",
        (session['user_id'],)
    ).fetchall()
    db.close()
    avaliados_map = {r['agendamento_id']: r['nota'] for r in avaliados}
    agora = datetime.now().strftime('%Y-%m-%d %H:%M')
    return render_template('client/meus_agendamentos.html',
                           agendamentos=agendamentos,
                           avaliados_map=avaliados_map,
                           agora=agora)

@app.route('/avaliar/<int:agendamento_id>', methods=['POST'])
@login_required
def avaliar(agendamento_id):
    nota = request.form.get('nota', type=int)
    comentario = request.form.get('comentario', '').strip()
    if not nota or not (1 <= nota <= 5):
        flash('Selecione uma nota de 1 a 5.', 'error')
        return redirect(url_for('meus_agendamentos'))
    db = get_db()
    ag = db.execute("SELECT * FROM agendamentos WHERE id=? AND usuario_id=?",
                    (agendamento_id, session['user_id'])).fetchone()
    if not ag or ag['data_hora'] >= datetime.now().strftime('%Y-%m-%d %H:%M'):
        db.close()
        flash('Agendamento invalido para avaliacao.', 'error')
        return redirect(url_for('meus_agendamentos'))
    ja = db.execute("SELECT id FROM avaliacoes WHERE agendamento_id=?", (agendamento_id,)).fetchone()
    if ja:
        db.close()
        flash('Voce ja avaliou este agendamento.', 'error')
        return redirect(url_for('meus_agendamentos'))
    db.execute("""
        INSERT INTO avaliacoes (usuario_id, barbeiro_id, agendamento_id, nota, comentario)
        VALUES (?,?,?,?,?)
    """, (session['user_id'], ag['barbeiro_id'], agendamento_id, nota, comentario))
    db.commit()
    db.close()
    flash('Avaliacao enviada! Obrigado pelo feedback.', 'success')
    return redirect(url_for('meus_agendamentos'))

@app.route('/cancelar-agendamento/<int:id>')
@login_required
def cancelar_agendamento(id):
    db = get_db()
    ag = db.execute("SELECT * FROM agendamentos WHERE id=? AND usuario_id=?",
                    (id, session['user_id'])).fetchone()
    if ag:
        db.execute("UPDATE agendamentos SET status='cancelado' WHERE id=?", (id,))
        db.commit()
        flash('Agendamento cancelado.', 'success')
    db.close()
    return redirect(url_for('meus_agendamentos'))

# ─── ROTAS FUNCIONÁRIO ───────────────────────────────────────────────────────

@app.route('/funcionario/agenda')
@funcionario_required
def funcionario_agenda():
    db = get_db()
    barbeiro = db.execute("SELECT * FROM barbeiros WHERE usuario_id=?", (session['user_id'],)).fetchone()
    agendamentos = []
    if barbeiro:
        agendamentos = db.execute("""
            SELECT a.*, s.nome as servico_nome, s.duracao, s.preco,
                   COALESCE(a.nome_avulso, u.nome) as usuario_nome
            FROM agendamentos a
            JOIN servicos s ON a.servico_id = s.id
            LEFT JOIN usuarios u ON a.usuario_id = u.id
            WHERE a.barbeiro_id = ?
            ORDER BY a.data_hora DESC
        """, (barbeiro['id'],)).fetchall()
    db.close()
    agora = datetime.now().strftime('%Y-%m-%d %H:%M')
    return render_template('funcionario/agenda.html', agendamentos=agendamentos, barbeiro=barbeiro, agora=agora)

@app.route('/funcionario/estoque')
@funcionario_required
def funcionario_estoque():
    db = get_db()
    produtos = db.execute("SELECT * FROM produtos WHERE ativo=1 ORDER BY nome").fetchall()
    historico = db.execute("""
        SELECT up.*, p.nome as produto_nome, p.unidade
        FROM uso_produtos up
        JOIN produtos p ON up.produto_id = p.id
        WHERE up.usuario_id = ?
        ORDER BY up.criado_em DESC LIMIT 30
    """, (session['user_id'],)).fetchall()
    db.close()
    return render_template('funcionario/estoque.html', produtos=produtos, historico=historico)

@app.route('/funcionario/pegar-produto/<int:produto_id>', methods=['POST'])
@funcionario_required
def funcionario_pegar_produto(produto_id):
    quantidade = request.form.get('quantidade', 1, type=int)
    observacao = request.form.get('observacao', '').strip()
    if quantidade < 1:
        flash('Quantidade invalida.', 'error')
        return redirect(url_for('funcionario_estoque'))
    db = get_db()
    produto = db.execute("SELECT * FROM produtos WHERE id=? AND ativo=1", (produto_id,)).fetchone()
    if not produto:
        db.close()
        flash('Produto nao encontrado.', 'error')
        return redirect(url_for('funcionario_estoque'))
    if produto['quantidade'] < quantidade:
        db.close()
        flash(f'Estoque insuficiente. Disponivel: {produto["quantidade"]} {produto["unidade"]}.', 'error')
        return redirect(url_for('funcionario_estoque'))
    db.execute("UPDATE produtos SET quantidade = quantidade - ? WHERE id=?", (quantidade, produto_id))
    db.execute("INSERT INTO uso_produtos (produto_id, usuario_id, quantidade, observacao) VALUES (?,?,?,?)",
               (produto_id, session['user_id'], quantidade, observacao))
    db.commit()
    db.close()
    flash(f'{quantidade} {produto["unidade"]} de "{produto["nome"]}" retirado do estoque.', 'success')
    return redirect(url_for('funcionario_estoque'))

@app.route('/funcionario/agendamento/concluir/<int:id>', methods=['POST'])
@funcionario_required
def funcionario_concluir_agendamento(id):
    db = get_db()
    barbeiro = db.execute("SELECT * FROM barbeiros WHERE usuario_id=?", (session['user_id'],)).fetchone()
    if barbeiro:
        ag = db.execute("SELECT * FROM agendamentos WHERE id=? AND barbeiro_id=? AND status='confirmado'",
                        (id, barbeiro['id'])).fetchone()
        if ag:
            db.execute("UPDATE agendamentos SET status='concluido' WHERE id=?", (id,))
            db.commit()
            flash('Agendamento marcado como concluido!', 'success')
        else:
            flash('Agendamento nao encontrado ou ja finalizado.', 'error')
    db.close()
    return redirect(url_for('funcionario_agenda'))

# ─── ROTAS ADMIN ─────────────────────────────────────────────────────────────

@app.route('/admin')
@admin_required
def admin_dashboard():
    db = get_db()
    total_agendamentos = db.execute("SELECT COUNT(*) FROM agendamentos").fetchone()[0]
    total_clientes = db.execute("SELECT COUNT(*) FROM usuarios WHERE is_admin=0").fetchone()[0]
    total_barbeiros = db.execute("SELECT COUNT(*) FROM barbeiros WHERE ativo=1").fetchone()[0]
    receita = db.execute("""
        SELECT COALESCE(SUM(s.preco),0) as total
        FROM agendamentos a JOIN servicos s ON a.servico_id=s.id
        WHERE a.status IN ('confirmado','concluido')
    """).fetchone()[0]
    agendamentos_recentes = db.execute("""
        SELECT a.*, s.nome as servico_nome, s.preco,
               b.nome as barbeiro_nome,
               COALESCE(a.nome_avulso, u.nome) as usuario_nome
        FROM agendamentos a
        JOIN servicos s ON a.servico_id=s.id
        JOIN barbeiros b ON a.barbeiro_id=b.id
        JOIN usuarios u ON a.usuario_id=u.id
        ORDER BY a.criado_em DESC LIMIT 10
    """).fetchall()
    db.close()
    return render_template('admin/dashboard.html',
                           total_agendamentos=total_agendamentos,
                           total_clientes=total_clientes,
                           total_barbeiros=total_barbeiros,
                           receita=receita,
                           agendamentos_recentes=agendamentos_recentes)

@app.route('/admin/servicos')
@admin_required
def admin_servicos():
    db = get_db()
    servicos = db.execute("SELECT * FROM servicos ORDER BY categoria, nome").fetchall()
    db.close()
    return render_template('admin/servicos.html', servicos=servicos)

@app.route('/admin/servicos/novo', methods=['POST'])
@admin_required
def admin_servico_novo():
    nome = request.form.get('nome', '').strip()
    descricao = request.form.get('descricao', '').strip()
    preco = request.form.get('preco', 0)
    duracao = request.form.get('duracao', 30)
    categoria = request.form.get('categoria', 'Corte')
    if nome and preco and duracao:
        db = get_db()
        db.execute("INSERT INTO servicos (nome, descricao, preco, duracao, categoria) VALUES (?,?,?,?,?)",
                   (nome, descricao, float(preco), int(duracao), categoria))
        db.commit()
        db.close()
        flash('Serviço adicionado com sucesso!', 'success')
    return redirect(url_for('admin_servicos'))

@app.route('/admin/servicos/editar/<int:id>', methods=['POST'])
@admin_required
def admin_servico_editar(id):
    nome = request.form.get('nome', '').strip()
    descricao = request.form.get('descricao', '').strip()
    preco = request.form.get('preco', 0)
    duracao = request.form.get('duracao', 30)
    categoria = request.form.get('categoria', 'Corte')
    db = get_db()
    db.execute("UPDATE servicos SET nome=?, descricao=?, preco=?, duracao=?, categoria=? WHERE id=?",
               (nome, descricao, float(preco), int(duracao), categoria, id))
    db.commit()
    db.close()
    flash('Serviço atualizado com sucesso!', 'success')
    return redirect(url_for('admin_servicos'))

@app.route('/admin/servicos/excluir/<int:id>')
@admin_required
def admin_servico_excluir(id):
    db = get_db()
    db.execute("UPDATE servicos SET ativo=0 WHERE id=?", (id,))
    db.commit()
    db.close()
    flash('Serviço removido.', 'success')
    return redirect(url_for('admin_servicos'))

@app.route('/admin/barbeiros')
@admin_required
def admin_barbeiros():
    db = get_db()
    barbeiros = db.execute("""
        SELECT b.*, u.email as func_email, u.id as func_id
        FROM barbeiros b
        LEFT JOIN usuarios u ON u.id = b.usuario_id AND u.is_funcionario = 1
        WHERE b.ativo = 1
        ORDER BY b.nome
    """).fetchall()
    db.close()
    return render_template('admin/barbeiros.html', barbeiros=barbeiros)

@app.route('/admin/barbeiros/novo', methods=['POST'])
@admin_required
def admin_barbeiro_novo():
    nome = request.form.get('nome', '').strip()
    especialidade = request.form.get('especialidade', '').strip()
    bio = request.form.get('bio', '').strip()
    nivel = request.form.get('nivel', 'Pleno')
    email = request.form.get('email', '').strip()
    senha = request.form.get('senha', '')
    if not nome or not especialidade:
        flash('Nome e especialidade são obrigatórios.', 'error')
        return redirect(url_for('admin_barbeiros'))
    if not email or not senha:
        flash('Email e senha são obrigatórios.', 'error')
        return redirect(url_for('admin_barbeiros'))
    db = get_db()
    if db.execute("SELECT id FROM usuarios WHERE email=?", (email,)).fetchone():
        flash('Este email já está em uso. Escolha outro.', 'error')
        db.close()
        return redirect(url_for('admin_barbeiros'))
    cursor = db.execute("INSERT INTO barbeiros (nome, especialidade, bio, nivel) VALUES (?,?,?,?)",
                        (nome, especialidade, bio, nivel))
    barb_id = cursor.lastrowid
    cur2 = db.execute("INSERT INTO usuarios (nome, email, senha, is_funcionario) VALUES (?,?,?,1)",
                      (nome, email, generate_password_hash(senha)))
    db.execute("UPDATE barbeiros SET usuario_id=? WHERE id=?", (cur2.lastrowid, barb_id))
    flash(f'Barbeiro {nome} adicionado com acesso ao sistema!', 'success')
    db.commit()
    db.close()
    return redirect(url_for('admin_barbeiros'))

@app.route('/admin/barbeiros/editar/<int:id>', methods=['POST'])
@admin_required
def admin_barbeiro_editar(id):
    nome = request.form.get('nome', '').strip()
    especialidade = request.form.get('especialidade', '').strip()
    bio = request.form.get('bio', '').strip()
    nivel = request.form.get('nivel', 'Pleno')
    db = get_db()
    db.execute("UPDATE barbeiros SET nome=?, especialidade=?, bio=?, nivel=? WHERE id=?",
               (nome, especialidade, bio, nivel, id))
    db.commit()
    db.close()
    flash('Barbeiro atualizado com sucesso!', 'success')
    return redirect(url_for('admin_barbeiros'))

@app.route('/admin/barbeiros/dar-acesso/<int:id>', methods=['POST'])
@admin_required
def admin_barbeiro_dar_acesso(id):
    email = request.form.get('email', '').strip()
    senha = request.form.get('senha', '')
    if not email or not senha:
        flash('Email e senha sao obrigatorios.', 'error')
        return redirect(url_for('admin_barbeiros'))
    db = get_db()
    barbeiro = db.execute("SELECT * FROM barbeiros WHERE id=?", (id,)).fetchone()
    if not barbeiro:
        db.close()
        flash('Barbeiro nao encontrado.', 'error')
        return redirect(url_for('admin_barbeiros'))
    if db.execute("SELECT id FROM usuarios WHERE email=?", (email,)).fetchone():
        db.close()
        flash('Email ja cadastrado.', 'error')
        return redirect(url_for('admin_barbeiros'))
    cursor = db.execute("INSERT INTO usuarios (nome, email, senha, is_funcionario) VALUES (?,?,?,1)",
                        (barbeiro['nome'], email, generate_password_hash(senha)))
    db.execute("UPDATE barbeiros SET usuario_id=? WHERE id=?", (cursor.lastrowid, id))
    db.commit()
    db.close()
    flash(f'Acesso criado para {barbeiro["nome"]}!', 'success')
    return redirect(url_for('admin_barbeiros'))

@app.route('/admin/barbeiros/excluir/<int:id>')
@admin_required
def admin_barbeiro_excluir(id):
    db = get_db()
    db.execute("UPDATE barbeiros SET ativo=0 WHERE id=?", (id,))
    db.commit()
    db.close()
    flash('Barbeiro removido.', 'success')
    return redirect(url_for('admin_barbeiros'))

@app.route('/admin/agendamentos')
@admin_required
def admin_agendamentos():
    db = get_db()
    status_f    = request.args.get('status', '')
    barbeiro_f  = request.args.get('barbeiro_id', '')
    data_de     = request.args.get('data_de', '')
    data_ate    = request.args.get('data_ate', '')
    where, params = ['1=1'], []
    if status_f:
        where.append('a.status=?'); params.append(status_f)
    if barbeiro_f:
        where.append('a.barbeiro_id=?'); params.append(barbeiro_f)
    if data_de:
        where.append("date(a.data_hora)>=?"); params.append(data_de)
    if data_ate:
        where.append("date(a.data_hora)<=?"); params.append(data_ate)
    agendamentos = db.execute(f"""
        SELECT a.*, s.nome as servico_nome, s.preco,
               b.nome as barbeiro_nome,
               COALESCE(a.nome_avulso, u.nome) as usuario_nome
        FROM agendamentos a
        JOIN servicos s ON a.servico_id=s.id
        JOIN barbeiros b ON a.barbeiro_id=b.id
        JOIN usuarios u ON a.usuario_id=u.id
        WHERE {' AND '.join(where)}
        ORDER BY a.data_hora DESC
    """, params).fetchall()
    barbeiros = db.execute("SELECT * FROM barbeiros WHERE ativo=1 ORDER BY nome").fetchall()
    db.close()
    return render_template('admin/agendamentos.html', agendamentos=agendamentos,
                           barbeiros=barbeiros, status_f=status_f, barbeiro_f=barbeiro_f,
                           data_de=data_de, data_ate=data_ate)

@app.route('/admin/estoque')
@admin_required
def admin_estoque():
    db = get_db()
    produtos = db.execute("SELECT * FROM produtos ORDER BY ativo DESC, nome").fetchall()
    historico = db.execute("""
        SELECT up.id, up.quantidade, up.observacao, up.criado_em,
               p.nome as produto_nome, p.unidade,
               COALESCE(b.nome, u.nome) as func_nome
        FROM uso_produtos up
        JOIN produtos p ON up.produto_id = p.id
        JOIN usuarios u ON up.usuario_id = u.id
        LEFT JOIN barbeiros b ON b.usuario_id = u.id
        ORDER BY up.criado_em DESC
        LIMIT 50
    """).fetchall()
    db.close()
    return render_template('admin/estoque.html', produtos=produtos, historico=historico)

@app.route('/admin/estoque/novo', methods=['POST'])
@admin_required
def admin_estoque_novo():
    nome = request.form.get('nome', '').strip()
    descricao = request.form.get('descricao', '').strip()
    quantidade = request.form.get('quantidade', 0, type=int)
    unidade = request.form.get('unidade', 'un').strip()
    if not nome:
        flash('Nome do produto e obrigatorio.', 'error')
        return redirect(url_for('admin_estoque'))
    db = get_db()
    db.execute("INSERT INTO produtos (nome, descricao, quantidade, unidade) VALUES (?,?,?,?)",
               (nome, descricao, quantidade, unidade))
    db.commit()
    db.close()
    flash('Produto adicionado ao estoque!', 'success')
    return redirect(url_for('admin_estoque'))

@app.route('/admin/estoque/editar/<int:id>', methods=['POST'])
@admin_required
def admin_estoque_editar(id):
    nome = request.form.get('nome', '').strip()
    descricao = request.form.get('descricao', '').strip()
    quantidade = request.form.get('quantidade', 0, type=int)
    unidade = request.form.get('unidade', 'un').strip()
    db = get_db()
    db.execute("UPDATE produtos SET nome=?, descricao=?, quantidade=?, unidade=? WHERE id=?",
               (nome, descricao, quantidade, unidade, id))
    db.commit()
    db.close()
    flash('Produto atualizado!', 'success')
    return redirect(url_for('admin_estoque'))

@app.route('/admin/estoque/excluir/<int:id>')
@admin_required
def admin_estoque_excluir(id):
    db = get_db()
    db.execute("UPDATE produtos SET ativo=0 WHERE id=?", (id,))
    db.commit()
    db.close()
    flash('Produto removido do estoque.', 'success')
    return redirect(url_for('admin_estoque'))

@app.route('/admin/funcionarios')
@admin_required
def admin_funcionarios():
    return redirect(url_for('admin_barbeiros'))

@app.route('/admin/funcionarios/novo', methods=['POST'])
@admin_required
def admin_funcionario_novo():
    nome = request.form.get('nome', '').strip()
    email = request.form.get('email', '').strip()
    senha = request.form.get('senha', '')
    especialidade = request.form.get('especialidade', '').strip()
    if not all([nome, email, senha]):
        flash('Preencha todos os campos obrigatorios.', 'error')
        return redirect(url_for('admin_funcionarios'))
    db = get_db()
    if db.execute("SELECT id FROM usuarios WHERE email=?", (email,)).fetchone():
        db.close()
        flash('Email ja cadastrado.', 'error')
        return redirect(url_for('admin_funcionarios'))
    cursor = db.execute("INSERT INTO usuarios (nome, email, senha, is_funcionario) VALUES (?,?,?,1)",
                        (nome, email, generate_password_hash(senha)))
    novo_id = cursor.lastrowid
    existing_barb = db.execute("SELECT id FROM barbeiros WHERE nome=? AND ativo=1", (nome,)).fetchone()
    if existing_barb:
        db.execute("UPDATE barbeiros SET usuario_id=? WHERE id=?", (novo_id, existing_barb['id']))
    else:
        db.execute("INSERT INTO barbeiros (nome, especialidade, usuario_id) VALUES (?,?,?)",
                   (nome, especialidade or 'Barbeiro', novo_id))
    db.commit()
    db.close()
    flash(f'Funcionario {nome} criado com sucesso!', 'success')
    return redirect(url_for('admin_funcionarios'))

@app.route('/admin/funcionarios/editar/<int:id>', methods=['POST'])
@admin_required
def admin_funcionario_editar(id):
    nome = request.form.get('nome', '').strip()
    email = request.form.get('email', '').strip()
    senha = request.form.get('senha', '')
    especialidade = request.form.get('especialidade', '').strip()
    if not all([nome, email]):
        flash('Nome e email sao obrigatorios.', 'error')
        return redirect(url_for('admin_funcionarios'))
    db = get_db()
    existing = db.execute("SELECT id FROM usuarios WHERE email=? AND id!=?", (email, id)).fetchone()
    if existing:
        db.close()
        flash('Email ja usado por outro usuario.', 'error')
        return redirect(url_for('admin_funcionarios'))
    if senha:
        db.execute("UPDATE usuarios SET nome=?, email=?, senha=? WHERE id=? AND is_funcionario=1",
                   (nome, email, generate_password_hash(senha), id))
    else:
        db.execute("UPDATE usuarios SET nome=?, email=? WHERE id=? AND is_funcionario=1",
                   (nome, email, id))
    db.execute("UPDATE barbeiros SET nome=?, especialidade=? WHERE usuario_id=?",
               (nome, especialidade, id))
    db.commit()
    db.close()
    flash('Funcionario atualizado.', 'success')
    return redirect(url_for('admin_funcionarios'))

@app.route('/admin/funcionarios/excluir/<int:id>')
@admin_required
def admin_funcionario_excluir(id):
    db = get_db()
    db.execute("UPDATE barbeiros SET ativo=0, usuario_id=NULL WHERE usuario_id=?", (id,))
    db.execute("DELETE FROM usuarios WHERE id=? AND is_funcionario=1", (id,))
    db.commit()
    db.close()
    flash('Funcionario removido.', 'success')
    return redirect(url_for('admin_funcionarios'))

@app.route('/admin/profissionais-dash')
@admin_required
def admin_profissionais_dash():
    db = get_db()
    resumo = db.execute("""
        SELECT u.id, u.nome,
               COUNT(up.id) as total_retiradas,
               COALESCE(SUM(up.quantidade), 0) as total_quantidade
        FROM usuarios u
        LEFT JOIN uso_produtos up ON up.usuario_id = u.id
        WHERE u.is_funcionario = 1
        GROUP BY u.id, u.nome
        ORDER BY total_quantidade DESC
    """).fetchall()
    detalhes = db.execute("""
        SELECT u.nome as funcionario_nome, p.nome as produto_nome,
               p.unidade, SUM(up.quantidade) as total, COUNT(up.id) as vezes
        FROM uso_produtos up
        JOIN usuarios u ON up.usuario_id = u.id
        JOIN produtos p ON up.produto_id = p.id
        GROUP BY up.usuario_id, up.produto_id
        ORDER BY u.nome, total DESC
    """).fetchall()
    db.close()
    return render_template('admin/profissionais_dash.html', resumo=resumo, detalhes=detalhes)

@app.route('/admin/graficos')
@admin_required
def admin_graficos():
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/calendario')
@admin_required
def admin_calendario():
    db = get_db()
    barbeiros = db.execute("SELECT * FROM barbeiros WHERE ativo=1").fetchall()
    servicos = db.execute("SELECT * FROM servicos WHERE ativo=1").fetchall()
    clientes = db.execute("SELECT id, nome, email FROM usuarios WHERE is_admin=0 ORDER BY nome").fetchall()
    db.close()
    return render_template('admin/calendario.html', barbeiros=barbeiros, servicos=servicos, clientes=clientes)

@app.route('/admin/agendamento/novo', methods=['POST'])
@admin_required
def admin_agendamento_novo():
    nome_avulso = request.form.get('nome_avulso', '').strip()
    barbeiro_id = request.form.get('barbeiro_id')
    servico_id = request.form.get('servico_id')
    data_hora = request.form.get('data_hora')
    observacoes = request.form.get('observacoes', '')
    if not all([nome_avulso, barbeiro_id, servico_id, data_hora]):
        flash('Preencha todos os campos obrigatorios.', 'error')
        return redirect(url_for('admin_calendario'))
    db = get_db()
    db.execute("""
        INSERT INTO agendamentos (usuario_id, barbeiro_id, servico_id, data_hora, observacoes, nome_avulso)
        VALUES (?,?,?,?,?,?)
    """, (session['user_id'], barbeiro_id, servico_id, data_hora, observacoes, nome_avulso))
    db.commit()
    db.close()
    flash('Agendamento criado com sucesso!', 'success')
    return redirect(url_for('admin_calendario'))

@app.route('/admin/agendamento/status/<int:id>', methods=['POST'])
@admin_required
def admin_agendamento_status(id):
    status = request.form.get('status')
    origem = request.form.get('origem', 'calendario')
    if status in ('confirmado', 'concluido', 'cancelado'):
        db = get_db()
        db.execute("UPDATE agendamentos SET status=? WHERE id=?", (status, id))
        db.commit()
        db.close()
    if origem == 'lista':
        flash('Status atualizado com sucesso!', 'success')
        return redirect(url_for('admin_agendamentos'))
    return ('', 204)

# ─── API DE DADOS PARA GRÁFICOS ──────────────────────────────────────────────

@app.route('/api/graficos/diario')
@admin_required
def api_grafico_diario():
    db = get_db()
    dados = db.execute("""
        SELECT strftime('%H:00', data_hora) as hora,
               COUNT(*) as total,
               SUM(s.preco) as receita
        FROM agendamentos a
        JOIN servicos s ON a.servico_id=s.id
        WHERE date(a.data_hora) = date('now','localtime')
          AND a.status != 'cancelado'
        GROUP BY hora ORDER BY hora
    """).fetchall()
    db.close()
    return jsonify([dict(r) for r in dados])

@app.route('/api/graficos/mensal')
@admin_required
def api_grafico_mensal():
    db = get_db()
    dados = db.execute("""
        SELECT strftime('%d', data_hora) as dia,
               COUNT(*) as total,
               SUM(s.preco) as receita
        FROM agendamentos a
        JOIN servicos s ON a.servico_id=s.id
        WHERE strftime('%Y-%m', a.data_hora) = strftime('%Y-%m','now','localtime')
          AND a.status != 'cancelado'
        GROUP BY dia ORDER BY dia
    """).fetchall()
    db.close()
    return jsonify([dict(r) for r in dados])

@app.route('/api/graficos/anual')
@admin_required
def api_grafico_anual():
    db = get_db()
    dados = db.execute("""
        SELECT strftime('%m', data_hora) as mes,
               COUNT(*) as total,
               SUM(s.preco) as receita
        FROM agendamentos a
        JOIN servicos s ON a.servico_id=s.id
        WHERE strftime('%Y', a.data_hora) = strftime('%Y','now','localtime')
          AND a.status != 'cancelado'
        GROUP BY mes ORDER BY mes
    """).fetchall()
    db.close()
    return jsonify([dict(r) for r in dados])

@app.route('/api/graficos/servicos-populares')
@admin_required
def api_servicos_populares():
    db = get_db()
    dados = db.execute("""
        SELECT s.nome, COUNT(*) as total, SUM(s.preco) as receita
        FROM agendamentos a
        JOIN servicos s ON a.servico_id=s.id
        WHERE a.status != 'cancelado'
        GROUP BY s.id, s.nome
        ORDER BY total DESC
    """).fetchall()
    db.close()
    return jsonify([dict(r) for r in dados])

@app.route('/api/agendamentos/calendario')
@admin_required
def api_calendario():
    db = get_db()
    rows = db.execute("""
        SELECT a.id, a.data_hora, a.status, a.observacoes,
               s.nome as servico_nome, s.duracao,
               b.nome as barbeiro_nome,
               COALESCE(a.nome_avulso, u.nome) as usuario_nome
        FROM agendamentos a
        JOIN servicos s ON a.servico_id = s.id
        JOIN barbeiros b ON a.barbeiro_id = b.id
        JOIN usuarios u ON a.usuario_id = u.id
    """).fetchall()
    db.close()
    colors = {'confirmado': '#4ade80', 'concluido': '#f2ca50', 'cancelado': '#ffb4ab'}
    events = []
    for r in rows:
        try:
            dt = datetime.strptime(r['data_hora'], '%Y-%m-%d %H:%M')
            start = dt.strftime('%Y-%m-%dT%H:%M:00')
            end = (dt + timedelta(minutes=r['duracao'])).strftime('%Y-%m-%dT%H:%M:00')
        except Exception:
            start = r['data_hora']
            end = r['data_hora']
        events.append({
            'id': r['id'],
            'title': f"{r['usuario_nome'].split()[0]} — {r['servico_nome']}",
            'start': start,
            'end': end,
            'backgroundColor': colors.get(r['status'], '#888'),
            'borderColor': colors.get(r['status'], '#888'),
            'textColor': '#131313',
            'extendedProps': {
                'barbeiro': r['barbeiro_nome'],
                'cliente': r['usuario_nome'],
                'servico': r['servico_nome'],
                'status': r['status'],
                'obs': r['observacoes'] or ''
            }
        })
    return jsonify(events)

@app.route('/api/graficos/barbeiros-ranking')
@admin_required
def api_barbeiros_ranking():
    db = get_db()
    dados = db.execute("""
        SELECT b.nome, COUNT(*) as total, SUM(s.preco) as receita
        FROM agendamentos a
        JOIN barbeiros b ON a.barbeiro_id=b.id
        JOIN servicos s ON a.servico_id=s.id
        WHERE a.status != 'cancelado'
        GROUP BY b.id, b.nome
        ORDER BY total DESC
    """).fetchall()
    db.close()
    return jsonify([dict(r) for r in dados])

@app.route('/admin/relatorio')
@admin_required
def admin_relatorio():
    db = get_db()
    total_ag    = db.execute("SELECT COUNT(*) FROM agendamentos").fetchone()[0]
    concluidos  = db.execute("SELECT COUNT(*) FROM agendamentos WHERE status='concluido'").fetchone()[0]
    cancelados  = db.execute("SELECT COUNT(*) FROM agendamentos WHERE status='cancelado'").fetchone()[0]
    receita     = db.execute("SELECT COALESCE(SUM(s.preco),0) FROM agendamentos a JOIN servicos s ON a.servico_id=s.id WHERE a.status IN ('confirmado','concluido')").fetchone()[0]
    clientes    = db.execute("SELECT COUNT(*) FROM usuarios WHERE is_admin=0 AND is_funcionario=0").fetchone()[0]
    barbeiros   = db.execute("SELECT COUNT(*) FROM barbeiros WHERE ativo=1").fetchone()[0]
    servicos_pop = db.execute("""
        SELECT s.nome, COUNT(*) as total, SUM(s.preco) as receita
        FROM agendamentos a JOIN servicos s ON a.servico_id=s.id
        WHERE a.status!='cancelado' GROUP BY s.id ORDER BY total DESC LIMIT 10
    """).fetchall()
    barbeiros_rank = db.execute("""
        SELECT b.nome, COUNT(*) as total, SUM(s.preco) as receita
        FROM agendamentos a JOIN barbeiros b ON a.barbeiro_id=b.id JOIN servicos s ON a.servico_id=s.id
        WHERE a.status!='cancelado' GROUP BY b.id ORDER BY total DESC
    """).fetchall()
    produtos_uso = db.execute("""
        SELECT b.nome as barbeiro, p.nome as produto, SUM(up.quantidade) as total, p.unidade
        FROM uso_produtos up JOIN usuarios u ON up.usuario_id=u.id
        JOIN barbeiros b ON b.usuario_id=u.id JOIN produtos p ON up.produto_id=p.id
        GROUP BY b.id, p.id ORDER BY b.nome, total DESC
    """).fetchall()
    from datetime import date
    db.close()
    return render_template('admin/relatorio.html',
        total_ag=total_ag, concluidos=concluidos, cancelados=cancelados,
        receita=receita, clientes=clientes, barbeiros=barbeiros,
        servicos_pop=servicos_pop, barbeiros_rank=barbeiros_rank,
        produtos_uso=produtos_uso, hoje=date.today().strftime('%d/%m/%Y'))

@app.route('/api/horarios-disponiveis')
@login_required
def api_horarios_disponiveis():
    barbeiro_id = request.args.get('barbeiro_id', type=int)
    data = request.args.get('data', '')
    servico_id = request.args.get('servico_id', type=int)
    if not all([barbeiro_id, data, servico_id]):
        return jsonify([])
    db = get_db()
    servico = db.execute("SELECT duracao FROM servicos WHERE id=?", (servico_id,)).fetchone()
    if not servico:
        db.close()
        return jsonify([])
    dur_nova = servico['duracao']
    ocupados = db.execute("""
        SELECT a.data_hora, s.duracao
        FROM agendamentos a JOIN servicos s ON a.servico_id=s.id
        WHERE a.barbeiro_id=? AND date(a.data_hora)=? AND a.status!='cancelado'
    """, (barbeiro_id, data)).fetchall()
    db.close()
    busy = []
    for ag in ocupados:
        s = datetime.strptime(ag['data_hora'], '%Y-%m-%d %H:%M')
        busy.append((s, s + timedelta(minutes=ag['duracao'])))
    slots = []
    base = datetime.strptime(f"{data} 08:00", '%Y-%m-%d %H:%M')
    fim_dia = datetime.strptime(f"{data} 20:00", '%Y-%m-%d %H:%M')
    cur = base
    while cur + timedelta(minutes=dur_nova) <= fim_dia + timedelta(minutes=1):
        slot_fim = cur + timedelta(minutes=dur_nova)
        disponivel = all(not (cur < b_end and slot_fim > b_start) for b_start, b_end in busy)
        slots.append({'hora': cur.strftime('%H:%M'), 'disponivel': disponivel})
        cur += timedelta(minutes=30)
    return jsonify(slots)

@app.route('/api/graficos/avaliacoes-barbeiros')
@admin_required
def api_avaliacoes_barbeiros():
    db = get_db()
    dados = db.execute("""
        SELECT b.nome, ROUND(COALESCE(AVG(av.nota), 0), 1) as media, COUNT(av.id) as total
        FROM barbeiros b
        LEFT JOIN avaliacoes av ON av.barbeiro_id = b.id
        WHERE b.ativo = 1
        GROUP BY b.id, b.nome
        ORDER BY media DESC
    """).fetchall()
    db.close()
    return jsonify([dict(r) for r in dados])

@app.route('/api/graficos/produtos-barbeiros')
@admin_required
def api_produtos_barbeiros():
    db = get_db()
    dados = db.execute("""
        SELECT b.nome as barbeiro,
               SUM(up.quantidade) as total,
               COUNT(up.id) as retiradas
        FROM uso_produtos up
        JOIN usuarios u ON up.usuario_id = u.id
        JOIN barbeiros b ON b.usuario_id = u.id
        GROUP BY b.id, b.nome
        ORDER BY total DESC
    """).fetchall()
    db.close()
    return jsonify([dict(r) for r in dados])

# ─── MAIN ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    print("=" * 50)
    print("Barbearia Eclipse - Sistema de Agendamento")
    print("=" * 50)
    print("Acesse: http://localhost:5000")
    print("Admin:  admin@eclipse.com / admin123")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)
