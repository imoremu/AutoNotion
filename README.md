# AutoNotion Daily Planner

An Azure Function App designed to automate daily task management in Notion. It intelligently duplicates unfinished tasks from the previous day and generates recurring periodic tasks, ensuring your daily plan is always ready.

## Features

- **Duplicate Unfinished Tasks**: Automatically carries over any incomplete tasks from yesterday's plan to today. It preserves the original time and sets it as a "Planned Time" for the new day.
- **Generate Periodic Tasks**: Creates recurring tasks based on a schedule defined in a master tasks database. Supports:
  - Daily
  - Weekly (on specific days of the week)
  - Monthly (on a specific day number or a relative day, e.g., the 2nd Tuesday)
  - Yearly

## How It Works

This project is an Azure Function with a **timer trigger**, configured to run once a day (e.g., shortly after midnight). When triggered, it performs the following actions:

1.  **Fetches Yesterday's Tasks**: It queries the `Registry` database to find all tasks from the previous day that are not marked as "Done".
2.  **Duplicates Unfinished Tasks**: For each unfinished task, it creates a new entry for the current day, preserving the original task details.
3.  **Generates Periodic Tasks**: It scans the `Tasks` database for any recurring tasks scheduled for the current day and creates them in the `Registry` database.

## Getting Started

### Prerequisites

- Python 3.9+
- An Azure account
- A Notion account and an integration token

### Installation

1. Clone the repository:
   ```sh
   git clone <your-repository-url>
   cd AutoNotion
   ```
2. Create and activate a virtual environment:
   ```sh
   python -m venv .venv
   source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
   ```
3. Install the required dependencies:
   ```sh
   pip install -r requirements.txt
   ```

### Configuration

This function relies on environment variables for its configuration. These can be set in `local.settings.json` for local development or in the Application Settings of your Azure Function App.

- `NOTION_API_KEY`: Your Notion integration secret token.
- `NOTION_REGISTRY_DB_ID`: The ID of the Notion database where daily tasks are created.
- `NOTION_TASKS_DB_ID`: The ID of the Notion database containing the master list of periodic tasks.

### Notion Database Setup

For the script to work correctly, your Notion databases need specific properties:

-   **Tasks Database (`NOTION_TASKS_DB_ID`)**:
    -   A `Schedule` property (Text) to define the recurrence (e.g., "daily", "weekly:monday,wednesday", "monthly:15", "yearly:07-25").
    -   A `Name` property (Title) for the task name.
-   **Registry Database (`NOTION_REGISTRY_DB_ID`)**:
    -   A `Status` property (Select) to track completion. The script checks for statuses that are *not* "Done".
    -   A `Date` property (Date) to associate the task with a specific day.

### Deployment to Azure

You can deploy this function to Azure using the Azure Functions extension for Visual Studio Code or the Azure CLI. Remember to configure the environment variables listed above in your Function App's `Configuration -> Application settings`.

## License

This project is licensed under the MIT License - see the LICENSE file for details.