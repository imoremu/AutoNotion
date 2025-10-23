# AutoNotion - Daily Planner Automation

An intelligent daily task management system that automatically duplicates unfinished tasks from the previous day and generates recurring periodic tasks in Notion.

## 🚀 Features

- **Duplicate Unfinished Tasks**: Automatically carries over incomplete tasks from yesterday with preserved timing
- **Generate Periodic Tasks**: Creates recurring tasks based on flexible schedules (daily, weekly, monthly, yearly)
- **Dual Deployment Support**: Deploy to either Azure Functions or Vercel
- **Smart Scheduling**: Supports complex scheduling like "2nd Tuesday of the month"

## 📁 Project Structure

```
AutoNotion/
├── 📁 config/                    # Configuration files
│   ├── logging.json             # Logging configuration
│   ├── local.settings.json      # Azure Functions local settings
│   └── env.example              # Environment variables template
├── 📁 docs/                     # Documentation
│   ├── VERCEL.md                # Vercel deployment guide
│   └── DEPLOYMENT.md            # Dual deployment guide
├── 📁 deployments/              # Platform-specific deployments
│   ├── 📁 azure/                # Azure Functions deployment
│   │   └── function_app.py      # Azure Functions entry point
│   └── 📁 vercel/               # Vercel deployment
│       └── 📁 api/              # Vercel API routes
│           ├── hello_notion.py
│           ├── run_daily_plan.py
│           └── scheduled_daily_plan.py
├── pyproject.toml               # Project configuration and dependencies
├── requirements.txt             # Vercel dependencies (generated from pyproject.toml)
├── vercel.json                  # Vercel configuration (root level)
├── 📁 shared/                   # Shared business logic
│   ├── notion_service.py        # Core service logic
│   └── notion_registry_daily_plan.py  # Original business logic
├── 📁 scripts/                  # Utility scripts
│   └── run_tests.py             # Test runner
├── 📁 tests/                    # Test suite
│   ├── 📁 unit/                 # Unit tests
│   │   └── test_shared_service.py
│   └── 📁 integration/          # Integration tests
│       ├── test_vercel_api_routes.py
│       └── test_dual_deployment.py
├── 📁 autonotion/               # Original business logic (preserved)
└── 📁 api/                      # Legacy Vercel API (deprecated)
```

## 🛠️ Quick Start

### Prerequisites
- Python 3.9+
- Notion account with integration token
- Choose your deployment platform:
  - **Azure Functions**: Azure account
  - **Vercel**: Vercel account (free tier available)

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repository-url>
   cd AutoNotion
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   # For Azure Functions (includes azure-functions package)
   pip install .[azure]
   
   # For Vercel (uses requirements.txt for deployment)
   pip install -r requirements.txt
   ```

### Configuration

Copy the environment template and configure your Notion credentials:

```bash
cp config/env.example .env.local
```

Edit `.env.local` with your Notion API details:
```bash
NOTION_API_KEY=your_notion_api_key_here
NOTION_REGISTRY_DB_ID=your_registry_database_id_here
NOTION_TASKS_DB_ID=your_tasks_database_id_here
```

## 🚀 Deployment Options

### Option 1: Azure Functions (Recommended for Azure users)

**Pros:**
- Native Azure integration
- Built-in timer triggers
- Easy local development

**Deploy:**
```bash
# Install Azure Functions Core Tools
npm install -g azure-functions-core-tools@4

# Deploy to Azure
func azure functionapp publish <your-function-app-name>
```

**Local Development:**
```bash
func start
```

### Option 2: Vercel (Recommended for global deployment)

**Pros:**
- Global edge deployment
- Built-in cron jobs
- GitHub integration
- Free tier available

**Deploy:**
```bash
# Install Vercel CLI
npm install -g vercel

# Deploy to Vercel
vercel

# Set environment variables
vercel env add NOTION_API_KEY
vercel env add NOTION_REGISTRY_DB_ID
vercel env add NOTION_TASKS_DB_ID
```

**Local Development:**
```bash
vercel dev
```

## 📋 Notion Database Setup

### Tasks Database (Master List)
Required properties:
- **Name** (Title): Task name
- **Tipo** (Select): Task type (Periódica, objetivo, puntual)
- **Periodicidad** (Multi-select): Recurrence (Diaria, Semanal, Mensual, Anual)
- **Día de la semana** (Multi-select): Days of week (1-7)
- **Día del mes** (Multi-select): Days of month (1-31)
- **Semana del mes** (Multi-select): Week of month (1ª, 2ª, 3ª, 4ª, Última)
- **Mes** (Multi-select): Months (1-12)
- **Hora** (Date): Template time for the task
- **Fecha de Alerta** (Date): Alert date for objetivo/puntual tasks
- **Estado** (Select): Task status

### Registry Database (Daily Tasks)
Required properties:
- **Nombre** (Title): Task name
- **Finalizada** (Checkbox): Completion status
- **Horario** (Date): Original scheduled time
- **Horario Planificado** (Date): Planned time for today
- **Tarea** (Relation): Link to master task
- **Status** (Select): Task status

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Run all tests
python scripts/run_tests.py

# Run specific test types
python scripts/run_tests.py --type unit
python scripts/run_tests.py --type integration
python scripts/run_tests.py --type azure
python scripts/run_tests.py --type vercel
```

## 📚 Documentation

- **[Vercel Deployment](docs/VERCEL.md)**: Vercel-specific deployment instructions
- **[Dual Deployment Guide](docs/DEPLOYMENT.md)**: Comparison and migration guide

## 🔄 Migration Between Platforms

The project supports easy migration between Azure Functions and Vercel:

1. **To Vercel**: Deploy using `vercel` command
2. **To Azure Functions**: Deploy using `func azure functionapp publish`
3. **Shared Logic**: Both platforms use the same business logic in `shared/`

## 📊 Monitoring

### Azure Functions
- Logs in Azure portal
- Application Insights integration
- Local logs in `local_debug.log`

### Vercel
- Logs in Vercel dashboard
- Real-time function logs
- Cron job execution monitoring

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `python scripts/run_tests.py`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Documentation**: [docs/](docs/)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/discussions)

---

**Made with ❤️ for productivity enthusiasts**
