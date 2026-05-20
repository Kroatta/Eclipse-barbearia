# 🪒 Barbearia Eclipse — Sistema de Agendamento

> **TCC — Desenvolvimento Web Full Stack**  
> Sistema completo de agendamento para barbearia com painel administrativo e gráficos analíticos.

---

## 📋 Sobre o Projeto

Sistema web desenvolvido como Trabalho de Conclusão de Curso (TCC), implementando uma solução completa de agendamento para a **Barbearia Eclipse**, incluindo:

- **Frontend**: HTML5, Tailwind CSS, JavaScript (ES6+), Chart.js
- **Backend**: Python 3 + Flask (framework web)
- **Banco de Dados**: SQLite3 (embutido, sem necessidade de instalação separada)
- **Autenticação**: Sistema de sessões com senha criptografada (bcryptjs)

---

## 🚀 Como Rodar o Projeto

### Pré-requisitos
- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)

### Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/eclipse-barbearia.git
cd eclipse-barbearia

# 2. Crie um ambiente virtual (recomendado)
python -m venv venv
source venv/bin/activate       # Linux/Mac
venv\Scripts\activate          # Windows

# 3. Instale as dependências
pip install flask werkzeug

# 4. Execute a aplicação
python app.py
```

### Acesse no navegador
```
http://localhost:5000
```

---

## 🔐 Credenciais de Acesso

### Administrador
- **URL de Login**: `http://localhost:5000/admin/login`
- **Email**: `admin@eclipse.com`
- **Senha**: `admin123`

### Cliente (para testar)
- **URL de Login**: `http://localhost:5000/login`
- **Email**: `cliente@eclipse.com`
- **Senha**: `cliente123`

---

## 📁 Estrutura do Projeto

```
eclipse-barbearia/
│
├── app.py                     # 🔧 Backend principal (Flask)
│
├── templates/
│   ├── base.html              # Layout base (flash messages, fonts)
│   │
│   ├── client/                # Páginas do cliente
│   │   ├── index.html         # Homepage pública
│   │   ├── login.html         # Tela de login
│   │   ├── cadastro.html      # Cadastro de usuário
│   │   ├── agendar.html       # Fazer agendamento
│   │   └── meus_agendamentos.html
│   │
│   └── admin/                 # Painel administrativo
│       ├── base_admin.html    # Layout com sidebar
│       ├── login.html         # Login exclusivo do admin
│       ├── dashboard.html     # Visão geral
│       ├── graficos.html      # 📊 Gráficos (diário/mensal/anual)
│       ├── calendario.html    # 📅 Calendário de agendamentos
│       ├── servicos.html      # CRUD de serviços
│       ├── barbeiros.html     # CRUD de barbeiros
│       └── agendamentos.html  # Lista todos os agendamentos
│
├── instance/
│   └── eclipse.db             # Banco SQLite (gerado automaticamente)
│
└── README.md
```

---

## ✨ Funcionalidades

### 👤 Área do Cliente
- [x] Página inicial com serviços, equipe e depoimentos
- [x] Cadastro e login de usuário (URL exclusiva: `/login`)
- [x] Agendamento de serviços (escolha serviço, barbeiro, data/hora)
- [x] Visualizar e cancelar próprios agendamentos
- [x] Avaliação com estrelas (1–5) para agendamentos já realizados
- [x] Nota média dos barbeiros exibida na página principal

### 🔒 Painel Administrativo (exclusivo admin — `/admin/login`)
- [x] Dashboard com KPIs (total agendamentos, clientes, receita)
- [x] **Calendário interativo** de agendamentos:
  - Visualização mensal, semanal, diária e lista
  - Cores por status (verde/dourado/vermelho)
  - Clique no evento para ver detalhes e alterar status
  - Criação de novo agendamento diretamente pelo calendário
- [x] **Gráficos analíticos** com 3 períodos:
  - 📅 **Diário** — agendamentos e receita por hora
  - 📆 **Mensal** — evolução do mês atual por dia
  - 📊 **Anual** — comparativo dos 12 meses
- [x] Gráfico de serviços mais/menos pedidos (doughnut)
- [x] Ranking de barbeiros (bar chart)
- [x] Receita por serviço (horizontal bar)
- [x] Tabela detalhada com participação percentual
- [x] CRUD completo de Serviços (criar, editar, excluir)
- [x] CRUD de Barbeiros
- [x] Listagem de agendamentos com filtro por status

---

## 🎨 Design

Paleta de cores inspirada no tema premium **Eclipse**:
- **Primary**: `#f2ca50` (Dourado)
- **Background**: `#131313` (Preto profundo)
- **Surface**: `#201f1f` (Cinza escuro)
- **Fontes**: Playfair Display (display) + Hanken Grotesk (corpo)

---

## 🛠️ Tecnologias Utilizadas

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3 + Flask |
| Banco de Dados | SQLite3 |
| Autenticação | Werkzeug (hash seguro) |
| Frontend | HTML5 + Tailwind CSS |
| Gráficos | Chart.js |
| Ícones | Google Material Symbols |
| Fontes | Google Fonts |

---

## 📚 Conceitos Aplicados (TCC)

- **MVC** — Separação de responsabilidades (routes/templates/db)
- **CRUD** — Create, Read, Update, Delete em todas as entidades
- **Autenticação & Autorização** — Sessões com controle de acesso por papel (admin/user)
- **Segurança** — Senhas com hash bcrypt, proteção de rotas
- **REST-like API** — Endpoints JSON para dados dos gráficos (`/api/graficos/...`)
- **Responsive Design** — Layout adaptável mobile/desktop
- **UX/UI** — Design system consistente com paleta de cores e tipografia definidas

---

## 👨‍💻 Autor

Desenvolvido como TCC — Curso de Ciência da Computação 
Brasília, 2026

---

*"Excelência em cada detalhe, estilo em cada corte."*
