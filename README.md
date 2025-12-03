# Automation Platform - Setup Guide

Follow the steps below to set up and run the **Automation Platform** project on your local system.

---

## 🚀 1. Clone the Repository
```
git clone https://github.com/chiragx16/Automation_Platform.git
cd Automation_Platform
```

---

## 🛠 2. Install Poetry (If Not Already Installed)
Poetry is used to manage project dependencies.

Run the following command:
```
curl -sSL https://install.python-poetry.org | python3 -
```

---

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

---

## 🔐 4. Configure Microsoft Azure OAuth Credentials
Go to **Microsoft Azure Portal** and create an application:
👉 https://azure.microsoft.com/en-us/get-started/azure-portal

Add the following values to your `.env`:
```
MS_CLIENT_ID=your_client_id
MS_CLIENT_SECRET=your_client_secret
MS_TENANT_ID=your_tenant_id
```

---

## 🔑 5. Set SECRET_KEY in `.env`
Add:
```
SECRET_KEY=your_secret_key
```

---

## 📦 6. Install Project Dependencies
Run the following inside project root:
```
poetry install
```
Poetry will create a virtual environment and install all required packages.

---

## 🖥 7. (Optional) Set VSCode Interpreter
VSCode may automatically detect the Poetry environment.
If not, manually set the Python interpreter to Poetry's virtual environment.

---

## ▶️ 8. Run the Project
From the project root directory:
```
poetry run python app.py
```

Your Automation Platform backend should now be running successfully.

---

## ✅ Setup Completed!
You're now ready to start using the **Automation Platform**.

If you face any issues, feel free to open an issue on GitHub or reach out for help.

