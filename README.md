# Django REST Framework (DRF) Template by Baboons

This repository is a template for setting up a Django REST Framework (DRF) project. It includes configurations for environment variables, database connections, JWT authentication, and more.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Setup Instructions](#setup-instructions)
- [Environment Variables](#environment-variables)
- [Running the Project](#running-the-project)
- [Project Structure](#project-structure)

## Prerequisites

Before you begin, ensure you have the following installed on your machine:

- Python 3.8+
- pip (Python package installer)

## Setup Instructions

1. **Clone the repository:**

    ```sh
    git clone <repository-url>
    cd <repository-directory>
    ```

2. **Create a virtual environment:**

    ```sh
    python -m venv venv
    ```

3. **Activate the virtual environment:**

    - On Windows:

        ```sh
        venv\Scripts\activate
        ```

    - On macOS/Linux:

        ```sh
        source venv/bin/activate
        ```

4. **Install the required packages:**

    ```sh
    pip install -r requirements.txt
    ```

5. **Create a `.env` file in the root directory and add your environment variables:**

    Refer to the `Environment Variables` section below for the required variables.

6. **Run the migrations:**

    ```sh
    python manage.py makemigrations
    python manage.py migrate
    ```

## Environment Variables

Create a `.env` file in the root directory of your project and add the following variables:

```env
DATABASE_NAME=your_db_name
DATABASE_HOST=your_db_host
DATABASE_PORT=5432
DATABASE_USERNAME=your_db_username
DATABASE_PASSWORD=your_db_password
```

## Running the Project

1. **Start the development server:**

    ```sh
    python manage.py runserver
    ```

2. **Access the application:**

    Open your web browser and navigate to `http://127.0.0.1:8000`.

## Project Structure

- `manage.py`: Django's command-line utility for administrative tasks.
- `requirements.txt`: List of dependencies to be installed.
- `environment/`: Contains environment-specific settings.
- `common/`: Contains common utilities, models, views, and other shared components.
- `user/`: Contains user-related models, views, serializers, and management commands.

## Key Files

- `manage.py`: 
    ```python:manage.py
    startLine: 0
    endLine: 24
    ```

- `environment/variables.py`: 
    ```python:environment/variables.py
    startLine: 0
    endLine: 44
    ```

- `requirements.txt`: 
    ```requirements.txt
    startLine: 0
    endLine: 87
    ```

- `environment/base.py`: 
    ```python:environment/base.py
    startLine: 0
    endLine: 198
    ```

- `environment/main.py`: 
    ```python:environment/main.py
    startLine: 0
    endLine: 47
    ```

- `common/management/commands/setup_backend.py`: 
    ```python:common/management/commands/setup_backend.py
    startLine: 0
    endLine: 55
    ```

## Additional Information

For more details on the project structure and individual modules, refer to the respective files in the repository.

---

This template is designed to help the team quickly set up and start developing with Django REST Framework. If you encounter any issues or have questions, please refer to the official [Django documentation](https://docs.djangoproject.com/en/stable/) or the [Django REST Framework documentation](https://www.django-rest-framework.org/).
