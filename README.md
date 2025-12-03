![Python](https://img.shields.io/badge/Python-3.13+-3776AB?logo=python&logoColor=gold)
![Flask](https://img.shields.io/badge/Flask-3.x-000000?logo=flask)
![Poetry](https://img.shields.io/badge/Poetry-Package_Manager-purple?logo=poetry&logoColor=blue)
![MySQL](https://img.shields.io/badge/MySQL-Database-orange?logo=mysql&logoColor=white)
![APScheduler](https://img.shields.io/badge/APScheduler-Job_Scheduler-CC0000?logo=clockify)
![REST API](https://img.shields.io/badge/REST_API-Backend-4479A1?logo=fastapi)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-ORM-green?logo=sqlalchemy&logoColor=yellow)


**Project Dashboard (Trello):** [Automation Platform Trello](https://trello.com/b/zYFiB5vx/automation-platform)

<hr style="height:1px; opacity:0.3; border:0; background-color:#ccc;" />


# Automation Platform - Setup Guide

Follow the steps below to set up and run the **Automation Platform** project on your local system.

<hr style="height:1px; opacity:0.3; border:0; background-color:#ccc;" />

## 🚀 1. Clone the Repository
```
git clone https://github.com/chiragx16/Automation_Platform.git
cd Automation_Platform
```

<hr style="height:1px; opacity:0.3; border:0; background-color:#ccc;" />

## 🛠 2. Install Poetry (If Not Already Installed)
Poetry is used to manage project dependencies.

Run the following command:
```
curl -sSL https://install.python-poetry.org | python3 -
```

<hr style="height:1px; opacity:0.3; border:0; background-color:#ccc;" />

## 🗄 3. Create and Configure MySQL Database
Create a new database in MySQL:
```
CREATE DATABASE IF NOT EXISTS BOT_MANAGER;
```

Inside your `.env` file, add your database URI:
```
SQLALCHEMY_DATABASE_URI=mysql+pymysql://root:root@localhost/bot_manager
```
Replace username, password, and host as per your setup.

<hr style="height:1px; opacity:0.3; border:0; background-color:#ccc;" />

## 🔐 4. Configure Microsoft Azure OAuth Credentials
Go to **Microsoft Azure Portal** and create an application:
👉 https://azure.microsoft.com/en-us/get-started/azure-portal

Add the following values to your `.env`:
```
MS_CLIENT_ID=your_client_id
MS_CLIENT_SECRET=your_client_secret
MS_TENANT_ID=your_tenant_id
```

<hr style="height:1px; opacity:0.3; border:0; background-color:#ccc;" />

## 🔑 5. Set SECRET_KEY in `.env`
Add:
```
SECRET_KEY=your_secret_key
```

<hr style="height:1px; opacity:0.3; border:0; background-color:#ccc;" />

## 📦 6. Install Project Dependencies
Run the following inside project root:
```
poetry install
```
Poetry will create a virtual environment and install all required packages.

<hr style="height:1px; opacity:0.3; border:0; background-color:#ccc;" />

## 🖥 7. (Optional) Set VSCode Interpreter
VSCode may automatically detect the Poetry environment.
If not, manually set the Python interpreter to Poetry's virtual environment.

<hr style="height:1px; opacity:0.3; border:0; background-color:#ccc;" />

## ▶️ 8. Run the Project
From the project root directory:
```
poetry run python app.py
```

Your Automation Platform backend should now be running successfully.

<hr style="height:1px; opacity:0.3; border:0; background-color:#ccc;" />

## ✅ Setup Completed!
You're now ready to start using the **Automation Platform**.

If you face any issues, feel free to open an issue on GitHub or reach out for help.

