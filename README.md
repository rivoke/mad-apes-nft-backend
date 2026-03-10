# Mad Apes NFT — Backend

A Django REST Framework backend powering the Mad Apes NFT platform. The system handles wallet-based authentication, a social task/points economy, a food item reward system, loot box mechanics, and on-chain NFT minting via Web3 and Thirdweb integrations.

---

## Table of Contents

- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Setup Instructions](#setup-instructions)
- [Environment Variables](#environment-variables)
- [Running the Project](#running-the-project)
- [Project Structure](#project-structure)
- [Application Overview](#application-overview)
- [Data Models](#data-models)
- [API Endpoints](#api-endpoints)
- [Background Tasks (Celery)](#background-tasks-celery)
- [Deployment](#deployment)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 5.2 + Django REST Framework 3.15 |
| Auth | JWT via `djangorestframework-simplejwt` |
| Database | PostgreSQL (`psycopg2-binary`) |
| Cache / Broker | Redis (`django-redis`, `redis[hiredis]`) |
| Task Queue | Celery 5.6 |
| File Storage | AWS S3 (`django-storages`, `boto3`) |
| Blockchain | `web3` (EVM / Avalanche), `solana`, `solders` |
| NFT Minting | Thirdweb API |
| Server | Gunicorn |

---

## Prerequisites

Ensure you have the following installed:

- Python 3.10+
- pip
- PostgreSQL
- Redis (for Celery task queue)

---

## Setup Instructions

1. **Clone the repository:**

    ```sh
    git clone <repository-url>
    cd <repository-directory>
    ```

2. **Create and activate a virtual environment:**

    ```sh
    python -m venv venv

    # Windows
    venv\Scripts\activate

    # macOS / Linux
    source venv/bin/activate
    ```

3. **Install dependencies:**

    ```sh
    pip install -r requirements.txt
    ```

4. **Create a `.env` file** in the root directory (see [Environment Variables](#environment-variables) below).

5. **Run migrations:**

    ```sh
    python manage.py makemigrations
    python manage.py migrate
    ```

6. **Create a superuser (optional, for Django Admin access):**

    ```sh
    python manage.py createsuperuser
    ```

---

## Environment Variables

Create a `.env` file in the project root with the following keys:

```env
# Application
BACKEND_ENVIRONMENT=MAIN       # MAIN, LOCAL, DEV, PROD
PORT=5000
HOST_URL=http://127.0.0.1:8000
DEBUG=True

# Database (PostgreSQL)
DATABASE_NAME=madapenft2
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_USERNAME=postgres
DATABASE_PASSWORD=admin

# JWT
JWT_SECRET_KEY=your_jwt_secret_key

# AWS S3 (media file storage)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_STORAGE_BUCKET_NAME=your_bucket_name
AWS_S3_ENDPOINT_URL=your_s3_endpoint
AWS_MEDIA_FOLDER=madape

# NFT / Blockchain
DEFAULT_NETWORK=1
ACCOUNT_NFT_COLLECTION_ADDRESS=0x...
PRIVATE_KEY=your_wallet_private_key
ACCOUNT_NFT_OWNER=0x...
LOOTBOX_COLLECTION_ADDRESS=0x...
LOOTBOX_NFT_OWNER=0x...
THIRDWEB_CLIENT_ID=your_thirdweb_client_id
THIRDWEB_SECRET_ID=your_thirdweb_secret

# Web3 Provider (defaults to Avalanche Fuji testnet)
WEB3_PROVIDER_URL=https://43113.rpc.thirdweb.com/<client_id>
CHAIN_ID=43113

# Celery / Redis
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
```

> **Note:** `JWT_SECRET_KEY`, `PRIVATE_KEY`, `AWS_*`, and `THIRDWEB_SECRET_ID` are required in all environments and have no fallback defaults.

---

## Running the Project

**Development server:**

```sh
python manage.py runserver
```

Access at: `http://127.0.0.1:8000`

**Celery worker** (required for background task processing):

```sh
celery -A environment.celery worker --loglevel=info
```

---

## Project Structure

```
mad-apes-nft-backend/
│
├── manage.py                    # Django management entry point
├── requirements.txt             # Python dependencies
├── gunicorn.config.py           # Gunicorn production server config
│
├── environment/                 # Django settings & configuration
│   ├── base.py                  # Shared settings (installed apps, middleware, CORS, Celery, S3)
│   ├── main.py                  # Environment-specific settings (DB connection)
│   ├── variables.py             # Centralised env-var loader (via python-decouple)
│   ├── celery.py                # Celery application instance
│   └── storage.py               # Custom S3 storage backend
│
├── common/                      # Core infrastructure
│   ├── urls.py                  # Root URL router
│   ├── views.py                 # Health check endpoint
│   ├── permissions.py           # Custom DRF permission classes
│   ├── pagination.py            # Global pagination config
│   ├── utils.py                 # Shared utility functions
│   ├── asgi.py / wsgi.py        # ASGI / WSGI entry points
│   └── management/commands/     # Custom management commands (e.g. setup_backend)
│
├── user/                        # User management, NFT profiles, food & loot box systems
│   ├── models.py                # All data models (see Data Models section)
│   ├── views.py                 # API views
│   ├── serializers.py           # DRF serializers
│   ├── services.py              # Business logic layer
│   ├── tasks.py                 # Celery tasks (minting, rewards)
│   ├── urls.py                  # User API routes
│   ├── admin.py                 # Django Admin configuration
│   └── migrations/              # Database migration files
│
├── tasks/                       # Social task & engagement system
│   ├── models.py                # SocialTask, UserSocialTask models
│   ├── views.py                 # Task listing and submission views
│   ├── serializers.py           # Task serializers
│   ├── urls.py                  # Task API routes
│   └── migrations/              # Database migration files
│
├── exceptions/                  # Global exception handling
│   └── (custom exception handler registered in DRF settings)
│
└── static_files/                # Static assets
```

---

## Application Overview

### `user` app
The core application. Manages:
- **Wallet authentication** — EVM signature-based login via a challenge/response flow.
- **User profiles** — NFT ownership data, referral codes, point balances.
- **Food item economy** — Users earn `FLOWER` and `BANANA` items through tasks and referrals, then consume them for points.
- **Loot box system** — Users spend food items to purchase and open loot boxes, winning rewards of varying rarity (Common, Rare, Epic, Legendary) with on-chain NFT minting.
- **Points & leaderboard** — Every action (task completion, food consumption, referral) results in points tracked via `PointsTransaction` records.

### `tasks` app
Manages the social engagement system:
- **SocialTask** — Admin-created tasks (follow Twitter, join Telegram, daily login, etc.) that reward food items upon completion.
- **UserSocialTask** — Tracks which tasks a user has submitted and whether they have been verified.

### `common` app
Infrastructure layer:
- Root URL routing
- Health check endpoint (`GET /`)
- Custom permissions, pagination, utilities
- WSGI/ASGI application instances

---

## Data Models

### `user` app

| Model | Description |
|---|---|
| `User` | Custom user model with wallet address, referral code, nickname, and cached total points |
| `FoodItem` | Defines food types (`FLOWER`, `BANANA`) with point values |
| `FoodInventory` | Per-user inventory of each food item type |
| `FoodConsumption` | Audit log of food items consumed for points |
| `ReferralReward` | Tracks food rewards granted via the referral system |
| `PointsTransaction` | Full ledger of all point movements for a user |
| `LootBox` | A purchasable loot box with food item cost and purchase limits |
| `LootBoxReward` | Possible rewards for a given loot box, with rarity and drop-rate weighting |
| `UserLootBoxPurchase` | Tracks a user's loot box purchases and how many have been opened |
| `UserLootBoxReward` | Reward won from opening a loot box, including on-chain minting status |
| `MintProfile` | Stores on-chain NFT data (token ID, contract address, stats) linked to a user |

### `tasks` app

| Model | Description |
|---|---|
| `SocialTask` | An admin-defined social engagement task with type, reward food item, and quantity |
| `UserSocialTask` | A user's submission/completion record for a specific task |

---

## API Endpoints

Base URL: `http://<host>/`

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/token/` | Obtain JWT access and refresh tokens |
| `POST` | `/api/token/refresh/` | Refresh a JWT access token |

### User (`/api/user/`)

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `POST` | `/api/user/challenge/` | Get a wallet signature challenge | No |
| `POST` | `/api/user/login/` | Login with wallet signature | No |
| `GET` | `/api/user/current/` | Get current authenticated user profile | Yes |
| `PATCH` | `/api/user/update-profile/` | Update user profile (nickname, etc.) | Yes |
| `GET` | `/api/user/my-rank/` | Get current user's leaderboard rank | Yes |
| `POST` | `/api/user/verify-referral-code/` | Validate a referral code | Yes |
| `POST` | `/api/user/account_nft_update/` | Trigger NFT account data update | Yes |
| `GET` | `/api/user/food/items/` | List all available food item types | Yes |
| `GET/POST` | `/api/user/food/inventory/` | View inventory / consume food items for points | Yes |
| `GET` | `/api/user/lootbox/available/` | List purchasable loot boxes | Yes |
| `POST` | `/api/user/lootbox/<id>/purchase/` | Purchase a loot box with food items | Yes |
| `POST` | `/api/user/lootbox/<id>/open/` | Open a purchased loot box | Yes |
| `GET` | `/api/user/lootbox/inventory/` | View unopened loot boxes | Yes |
| `GET` | `/api/user/lootbox/my-purchases/` | View loot box purchase history | Yes |
| `GET` | `/api/user/lootbox/my-rewards/` | View rewards won from loot boxes | Yes |

### Tasks (`/api/tasks/`)

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/api/tasks/` | List all active social tasks | Yes |
| `GET/POST` | `/api/tasks/my-tasks/` | View completed tasks / submit a task | Yes |

### System

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Health check |
| `GET` | `/admin/` | Django admin panel |

---

## Background Tasks (Celery)

Celery is used for asynchronous processing. The broker is Redis.

Key async operations (defined in `user/tasks.py`):

- **NFT minting** — After a loot box is opened, minting the reward NFT on-chain via the Thirdweb API is handled asynchronously.
- **Reward distribution** — Food item rewards from loot boxes are added to user inventory in the background.

Start the worker with:

```sh
celery -A environment.celery worker --loglevel=info
```

---

## Deployment

The project uses **Gunicorn** as the production WSGI server, configured in `gunicorn.config.py`.

- Binds to `0.0.0.0:<PORT>` (default: `5000`)
- Workers: `cpu_count()` (auto-scaled)
- Threads: `(2 * workers) + 1`
- Timeout: 60 seconds

**Run in production:**

```sh
gunicorn -c gunicorn.config.py common.wsgi
```

Media files are served directly from **AWS S3** via the custom storage backend in `environment/storage.py`. Ensure all AWS environment variables are set before deploying.

---

## CORS & Allowed Origins

The following origins are whitelisted by default (configurable in `environment/base.py`):

- `http://localhost:3000`
- `http://127.0.0.1:8000`
- `https://api-nft.macd.gg`

Update `ALLOWED_ORIGINS` in `base.py` to add any additional frontend or staging domains.
