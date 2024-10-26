# AudioScribe

**Audio Content Transcription Platform**

A streamlined solution designed to transform podcasts, YouTube videos, and audio content into accurate, searchable text. AudioScribe makes audio content accessible, searchable, and more valuable through automated transcription.

### Demo

Try it live at: [AudioScribe Web App](https://audioscribe.streamlit.app/)

### Overview

**Description:** Educational project focused on building a platform that converts various audio sources into text transcriptions, leveraging multiple content provider APIs and AI-powered transcription services.

**Challenge:** Learning to integrate and orchestrate multiple third-party APIs (ListenNotes, Spotify, YouTube, AssemblyAI) into a cohesive application while managing different data formats, authentication methods, and providing a seamless user experience.

### Tech Stack
- ![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white) ![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat-square&logo=streamlit&logoColor=white) ![AssemblyAI](https://img.shields.io/badge/AssemblyAI-5B5B5B?style=flat-square&logo=assembly&logoColor=white)
- Various Content APIs (ListenNotes, Spotify, YouTube)

### Key Features
**Multi-Source Support**:
- Podcasts from ListenNotes and Spotify
- Videos from YouTube
- Direct audio file uploads

**Advanced Processing**:
- Speaker identification
- Automatic language detection
- Content summarization

### Installation

1. Clone the repository:
```bash
git clone https://github.com/jbo-tech/audioscribe.git
cd audioscribe
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure API keys:
Create a `/.streamlit/secrets.toml` file with:
```toml
listennotes = "your_listennotes_api_key"
assemblyai = "your_assemblyai_api_key"
[spotify]
id = "your_spotify_client_id"
secret = "your_spotify_client_secret"
```

4. Launch the application:
```bash
streamlit run transcrypt-app.py
```

### API Integration
The project integrates with several third-party services:
- [AssemblyAI](https://www.assemblyai.com/) for audio transcription
- [ListenNotes](https://www.listennotes.com/api/) for podcast content
- [Spotify API](https://developer.spotify.com/documentation/web-api) for podcast access
- [YouTube](https://developers.google.com/youtube/v3) for video content

### Acknowledgments
- Thanks to ListenNotes, Spotify, and YouTube for their API access
- Thanks to AssemblyAI for providing transcription services

---
*Last Updated: 26/10/2024*
