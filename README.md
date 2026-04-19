# fm_ai_assistant

An AI assistant for Football Manager 23. Helps you find players by role and attributes, and provides tactical advice — all in one chat interface.
<img width="1897" height="904" alt="image" src="https://github.com/user-attachments/assets/4bfa1b3c-f2a4-44ec-96b2-f8c7ede1ce90" />


## Features

- **Player Search** — by role, league, country, attributes. E.g. *"Top 5 false nines in Russia"*
- **Tactical Advice** — formations, pressing, transitions. E.g. *"How to build a gegenpressing system?"*
- **Set Pieces** — corners, free kicks, throw-ins
- **Player Development** — training schedules, role assignments
- **Mixed Queries** — *"How to play gegenpressing and who in the RPL would fit?"*


## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/EgorPlotnikovRus/fm_ai_assistant.git
cd fm_ai_assistant
```

### 2. Create config.env

```env
API_KEY=your_openai_api_key
BASE_URL=https://api.openai.com/v1
```


### 3. Run

```bash
docker-compose up --build
```


## Example Queries

```
Top 5 false nines in the Russian Premier League
How do I set up near-post corners?
Best defensive midfielders in the RPL under 23
How to build a gegenpressing system and who in the Bundesliga fits?
Create a training plan for a winger
Who are the best target forwards in the Championship?
```
