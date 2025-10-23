# AutoNotion - Vercel Deployment

This document provides specific instructions for deploying AutoNotion to Vercel.

## Quick Start

### 1. Prerequisites
- Node.js 18+ installed
- Vercel CLI installed: `npm install -g vercel`
- Notion API key and database IDs

### 2. Environment Variables
Set these in your Vercel dashboard or via CLI:

```bash
vercel env add NOTION_API_KEY
vercel env add NOTION_REGISTRY_DB_ID  
vercel env add NOTION_TASKS_DB_ID
```

### 3. Deploy
```bash
# Deploy to Vercel
vercel

# For production
vercel --prod
```

## API Endpoints

Once deployed, your endpoints will be available at:
- `https://your-app.vercel.app/api/hello-notion`
- `https://your-app.vercel.app/api/run-daily-plan`
- `https://your-app.vercel.app/api/scheduled-daily-plan` (cron job)

## Cron Job Configuration

The scheduled daily plan runs automatically at 2:05 AM daily via Vercel's cron jobs feature. This is configured in the root `vercel.json`:

```json
{
  "crons": [
    {
      "path": "/api/scheduled-daily-plan",
      "schedule": "0 5 2 * * *"
    }
  ]
}
```

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Start development server
vercel dev
```

## Monitoring

- View logs in Vercel dashboard
- Monitor cron job executions
- Check function execution times
- Set up alerts for failures

## Troubleshooting

### Common Issues

1. **Environment Variables Not Set**
   - Check Vercel dashboard → Settings → Environment Variables
   - Ensure all required variables are set

2. **Cron Job Not Running**
   - Verify cron schedule in root `vercel.json`
   - Check Vercel Pro plan (cron jobs require Pro)
   - Review function logs

3. **Import Errors**
   - Ensure `shared/` directory is included
   - Check Python path configuration

### Debug Mode

Enable debug logging by setting environment variable:
```bash
vercel env add LOG_LEVEL DEBUG
```

## Migration from Azure Functions

If migrating from Azure Functions:

1. **Keep Azure Functions code** - it's preserved in the repository
2. **Set up Vercel environment** - use same environment variables
3. **Test endpoints** - verify all functionality works
4. **Configure cron job** - ensure scheduled execution works
5. **Monitor deployment** - check logs and execution

## Rollback Plan

To return to Azure Functions:
1. Deploy using `func azure functionapp publish`
2. Set environment variables in Azure portal
3. Verify timer trigger is working

The Azure Functions code remains unchanged and ready to use.
