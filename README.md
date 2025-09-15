<!-- <p align="center">
  <a href="https://github.com/techySPHINX/Quorix" target="blank">
  <img src="https://i.imgur.com/3kQwQwC.png" width="120" alt="Quorix Logo" />
  </a>
</p> -->

<h1 align="center">
  Quorix
</h1>

<p align="center">
  An event booking , waitlist, advanced analytics and notification microservice engineered product.
<p>

<p align="center">
    <a href="https://github.com/techySPHINX/Quorix" target="blank">
     <img alt="License" src="https://img.shields.io/github/license/techySPHINX/Quorix?style=flat-square&logo=opensourceinitiative&logoColor=white&color=blue">
    </a>
    <a href="https://github.com/techySPHINX/Quorix" target="blank">
     <img src="https://img.shields.io/github/last-commit/techySPHINX/Quorix?style=flat-square&logo=git&logoColor=white&color=blue" alt="Last Commit" />
    </a>
    <a href="https://github.com/techySPHINX/Quorix/issues" target="blank">
     <img src="https://img.shields.io/github/issues/techySPHINX/Quorix?style=flat-square&logo=github&color=blue" alt="Open Issues" />
    </a>
    <a href="https://github.com/techySPHINX/Quorix/pulls" target="blank">
     <img src="https://img.shields.io/github/issues-pr/techySPHINX/Quorix?style=flat-square&logo=github&color=blue" alt="Open PRs" />
    </a>
</p>

**Quorix** is a robust and scalable microservice for managing event bookings, user notifications, and more. It's built with **FastAPI**, **SQLAlchemy**, and **Celery** to provide a high-performance, asynchronous, and reliable system.

## ✨ Key Features

- **🚀 Fast & Asynchronous:** Built on FastAPI and Starlette for high-performance, non-blocking I/O.
- **🎟️ Event & Booking Management:** Create, manage, and book events with ease.
- **🔔 Notification System:** Keep users informed with email notifications for bookings, cancellations, and reminders.
- **👥 User Authentication:** Secure user authentication and authorization using JWT.
- **⏳ Waitlist Functionality:** Automatically manage waitlists for fully booked events.
- **📊 Analytics:** (Optional) Endpoints for gathering insights on event and booking metrics.
- **⚙️ Background Tasks:** Offload tasks like sending emails to a Celery worker for a responsive API.
- **🗄️ Database Migrations:** Use Alembic to manage database schema changes.

## 🛠️ Tech Stack

- **Backend:** [FastAPI](https://fastapi.tiangolo.com/), [Python 3.11+](https://www.python.org/)
- **ORM:** [SQLAlchemy](https://www.sqlalchemy.org/)
- **Database:** [PostgreSQL](https://www.postgresql.org/) (recommended), SQLite (for testing)
- **Async Tasks:** [Celery](https://docs.celeryq.dev/en/stable/)
- **Caching & Message Broker:** [Redis](https://redis.io/)
- **Testing:** [Pytest](https://docs.pytest.org/)
- **Linting & Formatting:** [Ruff](https://beta.ruff.rs/docs/), [Black](https://github.com/psf/black), [MyPy](http://mypy-lang.org/)

## 🏛️ System Design

This repository includes a detailed system design document covering concurrency controls, database modeling, scalability patterns, API design, and optional features.

**➡️ [View the full System Design Document](docs/SYSTEM_DESIGN.md)**

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- [Poetry](https://python-poetry.org/docs/#installation) for dependency management
- [Docker](https://www.docker.com/get-started) and [Docker Compose](https://docs.docker.com/compose/install/) (for running with PostgreSQL and Redis)

### Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/techySPHINX/Quorix.git
    cd evently
    ```

2.  **Install dependencies using Poetry:**

    ```bash
    poetry install
    ```

3.  **Set up environment variables:**

    Create a `.env` file in the root directory by copying the example file:

    ```bash
    cp .env.example .env
    ```

    Update the `.env` file with your database credentials, SendGrid API key, and other settings.

### Running the Application

#### With Docker (Recommended)

This is the easiest way to get the application and its services (PostgreSQL, Redis) up and running.

1.  **Build and start the containers:**

    ```bash
    docker-compose up -d --build
    ```

2.  **Run database migrations:**

    ```bash
    docker-compose exec app alembic upgrade head
    ```

The API will be available at `http://localhost:8000`.

#### Locally (Without Docker)

1.  **Activate the virtual environment:**

    ```bash
    poetry shell
    ```

2.  **Run database migrations:**

    ```bash
    alembic upgrade head
    ```

3.  **Start the FastAPI server:**

    ```bash
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    ```

4.  **Start the Celery worker:**

    ```bash
    celery -A app.celery_app.celery worker -Q default,email,notifications -l info
    ```

## 🧪 Testing

The test suite uses `pytest` and an in-memory SQLite database by default for speed and reliability.

To run the tests:

```bash
poetry run pytest -q
```

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) to get started.

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
