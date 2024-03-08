# AudioScribe

Welcome to AudioScribe, an solution designed to transform podcasts, YouTube videos, and audios into accurate, shareable text. With AudioScribe, you can easily capture and utilize information from your audio and video content, making it accessible, searchable, and more valuable.

## Features

- **Podcast Transcription**: Quickly transcribe podcasts from ListenNotes, Spotify, and YouTube using unique IDs or text search.
- **YouTube Audio Extraction**: Extract audio from YouTube videos and transcribe them into text.
- **Custom Progress Indicators**: Monitor the transcription process with real-time updates and custom progress messages.
- **Content Summarization**: Get concise summaries of your transcriptions to capture key points.
- **Speaker Identification**: AudioScribe distinguishes between different speakers, organizing the transcription accordingly.
- **Language Detection**: Automatically detects and transcribes content in multiple languages.

## Installation

To get started with AudioScribe, clone this repository to your local machine:

```
git clone https://github.com/yourusername/audioscribe.git
cd audioscribe
```

### Install the required Python packages:

```
pip install -r requirements.txt
```

### Setup

Create a secret.toml file in the directory /.streamlit of the project and add your API keys:

```
listennotes = "your_listennotes_api_key"
assemblyai = "your_assemblyai_api_key"
[spotify]
id = "your_spotify_client_id"
secret = "your_spotify_client_secret"
```

## Running AudioScribe

To start the AudioScribe application, run:

```
streamlit run app.py
```

## Contributing

We welcome contributions to AudioScribe! If you have suggestions for improvements or encounter any issues, please feel free to open an issue or submit a pull request.

## Acknowledgments

- Thanks to ListenNotes, Spotify, and YouTube for providing access to their APIs.
- Thanks to AssemblyAI for the transcription services.