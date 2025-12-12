# Echo Substrate v4: Production Deployment Guide

**Version:** 4.0  
**Status:** Finalized  
**Author:** Manus AI

---

## 1. Overview

This guide provides instructions for deploying the Echo Substrate v4 system in a production environment. It assumes a standard cloud environment with Docker and a managed PostgreSQL database.

## 2. Prerequisites

1.  **Docker & Docker Compose:** For containerization and orchestration.
2.  **Managed PostgreSQL Database:** A production-grade PostgreSQL instance (e.g., AWS RDS, Google Cloud SQL). **Do not use SQLite.**
3.  **Secrets Management:** A system for managing environment variables and secrets (e.g., AWS Secrets Manager, HashiCorp Vault).
4.  **Reverse Proxy:** A reverse proxy like Nginx or Traefik for SSL termination and load balancing.

## 3. Configuration

Create a `.env` file in the root of the project with the following environment variables. **Do not commit this file to version control.**

```env
# Database URL for your managed PostgreSQL instance
DATABASE_URL="postgresql://<user>:<password>@<host>:<port>/<database>"

# A strong, randomly generated secret key for JWT tokens
SECRET_KEY="your_strong_random_secret_key"

# Comma-separated list of allowed origins for CORS
# Example: "https://app.yourdomain.com,https://admin.yourdomain.com"
ALLOWED_ORIGINS="http://localhost:3000"

# Optional: Port for the API to run on
API_PORT=8000
```

## 4. Building the Docker Image

From the root of the project, build the Docker image:

```bash
docker build -t echo-substrate-v4:latest .
```

## 5. Database Migrations

The system uses SQLAlchemy to manage the database schema. The tables are created automatically on application startup. For production, you may want to use a migration tool like Alembic for more control over schema changes.

1.  **Initial Schema Creation:** The first time the application starts, it will create all necessary tables based on the models in `src/organs/models.py`.
2.  **Schema Updates:** For future updates, you will need to manage schema migrations manually or using a tool like Alembic.

## 6. Running the Application

You can run the application using Docker Compose for a simple deployment.

### `docker-compose.yml`

Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  api:
    image: echo-substrate-v4:latest
    container_name: echo-substrate-api
    restart: always
    env_file:
      - .env
    ports:
      - "${API_PORT:-8000}:8000"
    networks:
      - substrate-net

networks:
  substrate-net:
    driver: bridge
```

### Start the Service

```bash
docker-compose up -d
```

## 7. Initial Setup & Validation

1.  **Health Check:** Verify the service is running by accessing the health check endpoint:
    ```bash
    curl http://localhost:8000/health
    ```
    You should see `{"status":"healthy", ...}`.

2.  **Create Roles & Users:** Use the API to create users with the appropriate roles (Intent Architect, Arbiter, etc.).

3.  **Allocate Budgets:** Use the `/api/v1/metabolism/allocate` endpoint to allocate budgets to your initial agents.

4.  **Register Agents:** Register your sensor and task agents with the system.

## 8. Security Best Practices

*   **SSL/TLS:** Use a reverse proxy to terminate SSL and enforce HTTPS.
*   **Firewall:** Restrict access to the database port to only allow connections from the application server.
*   **Secrets:** Never hardcode secrets. Use a proper secrets management system.
*   **Backups:** Regularly back up your PostgreSQL database.
*   **Monitoring:** Monitor the application for errors, performance, and resource usage.

## 9. Audit Framework

The Apex system is designed to be auditable. The **Auditor** role is responsible for:

1.  **Reviewing the Event Log:** The `event_log` table in the database contains an immutable record of every action. Regularly query this table to ensure all actions are expected and authorized.
2.  **Verifying Provenance:** The `previous_event_id` in the `event_log` table creates a cryptographic-like chain. Any break in this chain indicates tampering.
3.  **Monitoring the Cost Ledger:** The `cost_ledger` table provides a complete record of all resources consumed by agents. Look for unusual spikes in cost.
4.  **Checking the Quarantine List:** The `quarantined_agents` table should be reviewed to understand why agents are being flagged by the Immune System.
