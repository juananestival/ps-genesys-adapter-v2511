# Polysynth Genesys AudioHook Adapter

This repository contains a Python-based adapter that bridges Genesys Cloud AudioHook WebSocket connections with the Polysynth `bidiRunSession` API. It allows you to integrate your Genesys Cloud contact center with Polysynth agents for advanced conversational AI capabilities.

## Features

*   **Bidirectional Audio Streaming**: Seamlessly streams audio between Genesys Cloud and Polysynth.
*   **Audio Transcoding**: Automatically converts audio between Genesys Cloud's `PCMU` (µ-law) format and Polysynth's `LINEAR16` format.
*   **Genesys AudioHook Protocol Compliance**: Handles `open`, `opened`, `ping`, `pong`, `close`, `closed`, and `update` messages as per the Genesys AudioHook session walkthrough.
*   **Polysynth `bidiRunSession` Integration**: Communicates with Polysynth using its WebSocket API for real-time conversational AI.
*   **Google Cloud Authentication**: Uses Application Default Credentials (ADC) for authenticating with Polysynth.
*   **Basic Error Handling**: Sends `disconnect` messages to Genesys Cloud in case of errors.

## Prerequisites

Before running this adapter, ensure you have the following installed:

*   Python 3.8+
*   `pip` (Python package installer)
*   Google Cloud Project with Polysynth enabled
*   Google Cloud credentials configured (e.g., via `gcloud auth application-default login` or by setting the `GOOGLE_APPLICATION_CREDENTIALS` environment variable).

## Setup

1.  **Navigate to the adapter directory**:
    ```bash
    cd ps-genesys-adapter
    ```

2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure environment variables**:
    Create a `.env` file in the `ps-genesys-adapter` directory with the following content:
    ```
    # The port for the WebSocket server to listen on
    PORT=8080

    # The full resource name of your Polysynth agent
    # e.g. projects/your-project-id/locations/global/apps/your-app-id
    AGENT_ID=projects/your-project-id/locations/your-location/apps/your-app-id

    # Optional: Path to your Google Cloud credentials file if not using ADC
    # GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/keyfile.json
    ```
    **Replace `your-project-id`, `your-location`, and `your-app-id` with your actual Polysynth agent details.**

## Usage

To start the adapter, run the following command from the `ps-genesys-adapter` directory:

```bash
python main.py
```

The adapter will start a WebSocket server on the specified `PORT` (default: 8080) and listen for incoming connections from Genesys Cloud.

## Genesys Cloud Configuration

To use this adapter with Genesys Cloud, you will need to configure an AudioHook integration in your Genesys Cloud environment. Point the AudioHook WebSocket endpoint to the public URL of your running adapter (e.g., `wss://your-adapter-url.com/`).

## Future Improvements

*   **DTMF Handling**: Implement full support for DTMF (Dual-Tone Multi-Frequency) tones.
*   **Media Format Negotiation**: Dynamically negotiate audio codecs with Genesys Cloud beyond the default `PCMU`.
*   **Advanced Error Handling**: More granular error reporting and recovery mechanisms.
*   **Scalability**: Implement load balancing and horizontal scaling for high-volume deployments.
