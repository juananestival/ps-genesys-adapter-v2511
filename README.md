# Genesys Cloud to Google Conversational AI Adapter

Author: Igor Aiestaran

_Special thanks to Juanan Estival for showing me how to navigate the Genesys console in record time, which helped immensely in figuring this all out._

This repository contains a Python-based adapter that bridges Genesys Cloud AudioHook WebSocket connections with Google's Conversational Agents (Generative) (using the BidiRunSession API). It allows you to integrate your Genesys Cloud contact center with powerful, real-time AI agents.

## Background

### Core Technologies

*   **[Genesys Cloud](https://www.genesys.com/cloud)**: A suite of cloud services for enterprise-grade contact center management. It handles customer communications across voice, chat, email, and other channels.

*   **[AudioHook](https://developer.genesys.cloud/devapps/audiohook/)**: A feature of Genesys Cloud that provides a real-time, bidirectional stream of a call's audio. It uses WebSockets to connect to a service that can monitor, record, or interact with the call audio.

*   **[WebSockets](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API)**: A communication protocol that enables a two-way interactive communication session between a user's browser or client and a server. It is ideal for real-time applications like live audio streaming.

*   **[Conversational Agents](https://cloud.google.com/customer-engagement-ai/conversational-agents/ps)**: This refers to Google Cloud's powerful platform for building AI-powered conversational experiences. These tools allow you to design, build, and deploy sophisticated voice and chat agents.

### What This Software Does

This application acts as a **bridge** between Genesys Cloud and Google's conversational AI services. It receives the real-time audio stream from a phone call via Genesys AudioHook, forwards that audio to your Google conversational agent for processing, and streams the agent's voice response back into the phone call. This creates a seamless, real-time conversation between the caller and your AI agent.

---

## 1. How to Deploy to Cloud Run (Recommended)

This method deploys the adapter as a scalable, serverless container on Google Cloud Run.

### Step 1: Configure Deployment Values

First, you need to create a configuration file with the specific details for your Google Cloud project and agent.

1.  Copy the example configuration file:
    ```bash
    cp script/values.sh.example script/values.sh
    ```

### Step 1a: Create a Service Account and Configure Authentication

The Cloud Run service needs a Google Cloud service account to run as, which grants it permission to interact with your conversational AI agent.

1.  **Create a service account:** If you don't have one already, create a service account for this adapter.
    ```bash
    gcloud iam service-accounts create [SERVICE_ACCOUNT_NAME] --display-name="Genesys Adapter Service Account"
    ```
    Replace `[SERVICE_ACCOUNT_NAME]` with a name like `genesys-adapter`. The full service account email will be `genesys-adapter@<your-project-id>.iam.gserviceaccount.com`. Use this full email for the `SERVICE_ACCOUNT` variable in your `values.sh` file.

2.  **Choose an authentication method:**

    *   **Option 1 (Recommended): Automatic Authentication**

        Grant the `roles/ces.client` role to your service account. This allows the adapter to automatically generate the necessary credentials to securely connect to your conversational agent.
        ```bash
        gcloud projects add-iam-policy-binding [PROJECT_ID] \
            --member="serviceAccount:[FULL_SERVICE_ACCOUNT_EMAIL]" \
            --role="roles/ces.client"
        ```
        You also need to grant your service account access to the Genesys API key and client secret:
        ```bash
        gcloud secrets add-iam-policy-binding [API_KEY_SECRET_NAME] \
            --member="serviceAccount:[FULL_SERVICE_ACCOUNT_EMAIL]" \
            --role="roles/secretmanager.secretAccessor"

        gcloud secrets add-iam-policy-binding [CLIENT_SECRET_NAME] \
            --member="serviceAccount:[FULL_SERVICE_ACCOUNT_EMAIL]" \
            --role="roles/secretmanager.secretAccessor"
        ```
        Replace `[API_KEY_SECRET_NAME]` and `[CLIENT_SECRET_NAME]` with the names of the secrets you created for the Genesys API key and client secret, respectively.

        With this option, you can leave the `AUTH_TOKEN_SECRET_PATH` variable in `values.sh` empty.

    *   **Option 2 (Advanced): Manual Token Management**

        If your security model requires you to manage access tokens manually, you can specify a path to a secret in Google Secret Manager using the `AUTH_TOKEN_SECRET_PATH` variable in `values.sh`.

        You will need to grant your service account access to the Genesys API key secret, the client secret, and the auth token secret:
        ```bash
        gcloud secrets add-iam-policy-binding [GENESYS_API_KEY_SECRET_NAME] \
            --member="serviceAccount:[FULL_SERVICE_ACCOUNT_EMAIL]" \
            --role="roles/secretmanager.secretAccessor"

        gcloud secrets add-iam-policy-binding [GENESYS_CLIENT_SECRET_NAME] \
            --member="serviceAccount:[FULL_SERVICE_ACCOUNT_EMAIL]" \
            --role="roles/secretmanager.secretAccessor"

        gcloud secrets add-iam-policy-binding [AUTH_TOKEN_SECRET_NAME] \
            --member="serviceAccount:[FULL_SERVICE_ACCOUNT_EMAIL]" \
            --role="roles/secretmanager.secretAccessor"
        ```
        Replace `[GENESYS_API_KEY_SECRET_NAME]`, `[GENESYS_CLIENT_SECRET_NAME]`, and `[AUTH_TOKEN_SECRET_NAME]` with the names of the respective secrets.

        **Important:** You are responsible for ensuring the token in Secret Manager is valid and refreshed periodically. The adapter will simply read and use whatever token is stored there.

### Step 1b: Configure Deployment Values

Open `script/values.sh` in a text editor and fill in the required values. Key variables include:
    *   `PROJECT_ID`: Your Google Cloud Project ID.
    *   `SERVICE_NAME`: The name you want to give your Cloud Run service (e.g., `genesys-adapter`).
    *   `SERVICE_ACCOUNT`: The service account the Cloud Run service will use.
    *   `LOCATION`: The Google Cloud region where you want to deploy (e.g., `us-central1`).
    *   `GENESYS_API_KEY_SECRET_PATH`: The full resource path to the Secret Manager secret containing the API key that Genesys will use to connect. **Ensure this secret exists and has a value configured.**
    *   `GENESYS_CLIENT_SECRET_PATH`: The full resource path to the Secret Manager secret containing the client secret for request signature verification.

**Note on Agent ID**: The agent ID is expected to be passed dynamically within the `inputVariables` of the Genesys "open" message as `_agent_id`. You can set these up in Architect (on the Genesys console) when setting up the integration in yoru flow. Any other variables in `inputVariables` (not starting with an underscore) will be forwarded to Polysynth.

### Step 2: Run the Deployment Script

Once your `values.sh` file is configured, run the deploy script:

```bash
bash script/deploy.sh
```

This script uses the `gcloud` CLI to build the container image, push it to the Artifact Registry, and deploy it to Cloud Run with all the specified configurations. After deployment, `gcloud` will output the public URL for your service, which you will use to configure the AudioHook in Genesys Cloud.

---

## 2. How to Run Locally for Development

This method is ideal for testing and development. It uses Google Cloud Shell and `ngrok` to expose the local server to the public internet so Genesys Cloud can connect to it.

### Step 1: Open Cloud Shell

Navigate to the [Google Cloud Console](https://console.cloud.google.com) and activate Cloud Shell.

### Step 2: Run the Setup Script

In your first Cloud Shell terminal, run the setup script. This will prepare your environment and start `ngrok`.

```bash
bash script/setup-cloud-shell.sh
```

This script automatically performs the following actions:
*   Installs `ngrok`, a utility to create a secure tunnel to your local environment.
*   Starts `ngrok` and dedicates the terminal to its output.

The script will finish by running `ngrok`, which will display a public "Forwarding" URL (e.g., `https://<random-string>.ngrok-free.app`). This is the secure public URL that you must use for the AudioHook integration in Genesys Cloud.

**Keep this terminal open.**

### Step 3: Run the Server

You will need a second Cloud Shell terminal to run the adapter itself.

1.  **Open a new terminal** and navigate to the project directory.

2.  Activate the project's virtual environment:
    ```bash
    . .venv/bin/activate
    ```

3.  Start the adapter application:
    ```bash
    # Make sure you have configured your .env file with PORT and GENESYS_API_KEY
    python main.py
    ```