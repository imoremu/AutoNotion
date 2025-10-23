# AutoNotion - Dual Deployment Guide

This project supports deployment to both **Azure Functions** and **Vercel**. You can choose which platform to use based on your needs.

## Project Structure

```
├── pyproject.toml                        # Project configuration and dependencies
├── vercel.json                          # Vercel configuration (root level)
├── deployments/
│   ├── azure/
│   │   └── function_app.py              # Azure Functions entry point
│   └── vercel/
│       └── api/                         # Vercel API routes
│           ├── hello-notion.py
│           ├── run-daily-plan.py
│           └── scheduled-daily-plan.py
├── shared/                              # Shared business logic
│   ├── __init__.py
│   └── notion_service.py                # Core service logic
├── autonotion/                          # Original business logic
│   └── notion_registry_daily_plan.py
└── config/                              # Configuration files
    ├── local.settings.json
    └── env.example
```

## Environment Variables

Both platforms require the same environment variables:

- `NOTION_API_KEY`: Your Notion integration API key
- `NOTION_REGISTRY_DB_ID`: Database ID for the registry
- `NOTION_TASKS_DB_ID`: Database ID for tasks
- `RETRY_WAIT_SECONDS`: (Optional) Retry wait time in seconds (default: 5)
- `RETRY_ATTEMPTS`: (Optional) Number of retry attempts (default: 3)

## Deployment Options

### Option 1: Azure Functions (Current Setup)

**Pros:**
- Native Azure integration
- Built-in scheduling with Timer Triggers
- Easy local development with Azure Functions Core Tools

**Deployment:**
```bash
# Deploy to Azure Functions
func azure functionapp publish <your-function-app-name>
```

**Local Development:**
```bash
# Install Azure Functions Core Tools
npm install -g azure-functions-core-tools@4 --unsafe-perm true

# Start local development
func start
```

### Option 2: Vercel (New Setup)

**Pros:**
- Serverless with global edge deployment
- Built-in cron jobs
- Easy GitHub integration
- Free tier available

**Deployment:**
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
# Install dependencies
pip install -r requirements.txt

# Start Vercel development server
vercel dev
```

## API Endpoints

### Azure Functions
- `GET/POST /api/HelloNotion` - Hello endpoint
- `POST /api/run-daily-plan` - Manual daily plan execution
- Timer Trigger: `ScheduledNotionDailyPlan` - Runs daily at 2:05 AM

### Vercel
- `GET/POST /api/hello-notion` - Hello endpoint
- `POST /api/run-daily-plan` - Manual daily plan execution
- Cron Job: `/api/scheduled-daily-plan` - Runs daily at 2:05 AM

## Switching Between Platforms

### To Deploy to Vercel:
1. Set up environment variables in Vercel dashboard
2. Deploy using `vercel` command
3. The cron job will automatically be configured

### To Return to Azure Functions:
1. Deploy using `func azure functionapp publish`
2. Set environment variables in Azure portal
3. The timer trigger will automatically be configured

## Shared Business Logic

The core business logic is shared between both platforms through the `shared/notion_service.py` module. This ensures:

- ✅ Consistent behavior across platforms
- ✅ Easy maintenance and updates
- ✅ No code duplication
- ✅ Easy switching between platforms

## Monitoring and Logs

### Azure Functions
- Logs available in Azure portal
- Application Insights integration
- Local logs in `local_debug.log`

### Vercel
- Logs available in Vercel dashboard
- Function logs in real-time
- Cron job execution logs

## Cost Comparison

### Azure Functions
- Pay per execution
- Free tier: 1M requests/month
- Timer triggers included

### Vercel
- Free tier: 100GB-hours/month
- Cron jobs: Pro plan required ($20/month)
- Edge functions included

## Recommendations

- **Use Azure Functions** if you're already in the Azure ecosystem
- **Use Vercel** if you want global edge deployment and GitHub integration
- **Both platforms** support the same functionality and business logic
