"""
Barbearia Eclipse - Sistema de Agendamento
TCC - Backend com Flask + SQLite
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from datetime import datetime, date, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = 'eclipse_barbearia_tcc_2024_secret_key'

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
            criado_em TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY(barbeiro_id) REFERENCES barbeiros(id),
            FOREIGN KEY(servico_id) REFERENCES servicos(id)
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

    # Seed agendamentos de exemplo para os gráficos
    if not c.execute("SELECT id FROM agendamentos LIMIT 1").fetchone():
        import random
        from datetime import datetime, timedelta
        statuses = ['confirmado', 'confirmado', 'confirmado', 'concluido', 'concluido', 'cancelado']
        for i in range(120):
            dias_atras = random.randint(0, 365)
            data = (datetime.now() - timedelta(days=dias_atras)).strftime('%Y-%m-%d %H:%M')
            c.execute("""
                INSERT INTO agendamentos (usuario_id, barbeiro_id, servico_id, data_hora, status)
                VALUES (1, ?, ?, ?, ?)
            """, (random.randint(1,3), random.randint(1,6), random.choice(statuses), data))

    conn.commit()
    conn.close()

# ─── DECORATORS ─────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Faça login para continuar.', 'error')
            return redirect(url_for('login'))
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
    db.close()
    return render_template('client/index.html', servicos=servicos, barbeiros=barbeiros)

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
            flash(f'Bem-vindo de volta, {user["nome"].split()[0]}!', 'success')
            return redirect(url_for('meus_agendamentos'))
        flash('Email ou senha incorretos.', 'error')
    return render_template('client/login.html')

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
        data_hora = request.form.get('data_hora')
        observacoes = request.form.get('observacoes', '')
        if not all([servico_id, barbeiro_id, data_hora]):
            flash('Preencha todos os campos.', 'error')
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
    db.close()
    return render_template('client/agendar.html', servicos=servicos, barbeiros=barbeiros)

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
               b.nome as barbeiro_nome, u.nome as usuario_nome
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
    barbeiros = db.execute("SELECT * FROM barbeiros ORDER BY nome").fetchall()
    db.close()
    return render_template('admin/barbeiros.html', barbeiros=barbeiros)

@app.route('/admin/barbeiros/novo', methods=['POST'])
@admin_required
def admin_barbeiro_novo():
    nome = request.form.get('nome', '').strip()
    especialidade = request.form.get('especialidade', '').strip()
    bio = request.form.get('bio', '').strip()
    nivel = request.form.get('nivel', 'Pleno')
    if nome and especialidade:
        db = get_db()
        db.execute("INSERT INTO barbeiros (nome, especialidade, bio, nivel) VALUES (?,?,?,?)",
                   (nome, especialidade, bio, nivel))
        db.commit()
        db.close()
        flash('Barbeiro adicionado!', 'success')
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
    agendamentos = db.execute("""
        SELECT a.*, s.nome as servico_nome, s.preco,
               b.nome as barbeiro_nome, u.nome as usuario_nome
        FROM agendamentos a
        JOIN servicos s ON a.servico_id=s.id
        JOIN barbeiros b ON a.barbeiro_id=b.id
        JOIN usuarios u ON a.usuario_id=u.id
        ORDER BY a.data_hora DESC
    """).fetchall()
    db.close()
    return render_template('admin/agendamentos.html', agendamentos=agendamentos)

@app.route('/admin/graficos')
@admin_required
def admin_graficos():
    return render_template('admin/graficos.html')

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
    usuario_id = request.form.get('usuario_id')
    barbeiro_id = request.form.get('barbeiro_id')
    servico_id = request.form.get('servico_id')
    data_hora = request.form.get('data_hora')
    observacoes = request.form.get('observacoes', '')
    if not all([usuario_id, barbeiro_id, servico_id, data_hora]):
        flash('Preencha todos os campos obrigatorios.', 'error')
        return redirect(url_for('admin_calendario'))
    db = get_db()
    db.execute("""
        INSERT INTO agendamentos (usuario_id, barbeiro_id, servico_id, data_hora, observacoes)
        VALUES (?,?,?,?,?)
    """, (usuario_id, barbeiro_id, servico_id, data_hora, observacoes))
    db.commit()
    db.close()
    flash('Agendamento criado com sucesso!', 'success')
    return redirect(url_for('admin_calendario'))

@app.route('/admin/agendamento/status/<int:id>', methods=['POST'])
@admin_required
def admin_agendamento_status(id):
    status = request.form.get('status')
    if status in ('confirmado', 'concluido', 'cancelado'):
        db = get_db()
        db.execute("UPDATE agendamentos SET status=? WHERE id=?", (status, id))
        db.commit()
        db.close()
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
               u.nome as usuario_nome
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
