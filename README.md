\# Velora — Travel Recommendation \& Social Sharing Platform



Velora is a full-stack travel platform built for Pakistan, combining AI-powered trip planning, social trip sharing, budget tracking, and interactive maps. Built as a lab project for Advanced Database Management Systems (ADBMS).



\## Features



The AI Trip Planner generates full day-by-day itineraries — routes, budget breakdown, accommodation, food, packing lists, and safety tips — using Groq's LLM API, tailored to Pakistani destinations, prices, and weather. Users can share travel experiences as posts, like content, and search for destinations or other users. A budget tracker saves and organizes trip costs by category, while an interactive map built on Leaflet.js and OpenStreetMap visualizes routes. Profiles show stats, post history, and saved trips.



\## Tech Stack



Backend runs on Python and Flask, with a vanilla HTML/CSS/JS frontend. Data is split across three databases based on shape: PostgreSQL handles relational data like users, likes, and budgets; MongoDB stores social content such as posts; Neo4j manages relationship-heavy recommendation data. Trip planning is powered by the Groq API, and maps use Leaflet.js with OpenStreetMap tiles.



\## Why Three Databases?



Velora uses polyglot persistence, matching each type of data to the database best suited for it rather than forcing everything into one system — structured data in PostgreSQL, flexible documents in MongoDB, and graph relationships in Neo4j.



\## Project Structure



| Path | Purpose |

| --- | --- |

| `app.py` | Main Flask entry point, routes, and session handling |

| `db.py` | Database connections (PostgreSQL, MongoDB, Neo4j) |

| `requirements.txt` | Python dependencies |

| `Procfile` | Production start command (gunicorn) |

| `.env` | Environment variables (not committed) |

| `routes/auth.py` | Login, registration, session management |

| `routes/posts.py` | Post creation and retrieval |

| `routes/social.py` | Likes, follows, social interactions |

| `routes/budget.py` | Budget tracking endpoints |

| `routes/ai.py` | Groq-powered trip planning, post analysis, budget estimation |

| `templates/` | HTML pages (Jinja2) |

| `static/style.css` | Application styling |

| `static/uploads/` | User-uploaded images |



\## Requirements



Core dependencies, listed in `requirements.txt`:



\- Flask — web framework

\- gunicorn — production WSGI server

\- psycopg2-binary — PostgreSQL driver

\- pymongo — MongoDB driver

\- neo4j — Neo4j driver

\- python-dotenv — loads `.env` variables

\- groq — Groq API client

\- requests — HTTP requests

\- Werkzeug and Jinja2 — Flask dependencies



Install everything with:



```bash

pip install -r requirements.txt

```



\## Environment Setup



Create a `.env` file in the project root with the following variables:



```env

PG\_HOST=your\_postgres\_host

PG\_PORT=5432

PG\_DB=your\_postgres\_db

PG\_USER=your\_postgres\_user

PG\_PASS=your\_postgres\_password

PG\_SSLMODE=require



MONGO\_URI=your\_mongodb\_connection\_string

MONGO\_DB=your\_mongodb\_db\_name



NEO4J\_URI=your\_neo4j\_connection\_uri

NEO4J\_USER=your\_neo4j\_username

NEO4J\_PASS=your\_neo4j\_password



FLASK\_SECRET\_KEY=a\_random\_secret\_key



GROQ\_API\_KEY=your\_groq\_api\_key

```



`db.py` reads the `PG\_\*`, `MONGO\_\*`, and `NEO4J\_\*` variables to connect to each database. `routes/ai.py` reads `GROQ\_API\_KEY` for AI trip planning. `app.py` reads `FLASK\_SECRET\_KEY` for session security. Never commit real credentials or secret values — `.env` is excluded via `.gitignore`.



\## Local Setup



Clone the repo and enter the project folder:



```bash

git clone https://github.com/areebakhalid3/Velora-AI-Travel-Recommendation-Social-Platform.git

cd Velora-AI-Travel-Recommendation-Social-Platform

```



Create a virtual environment and install dependencies (Windows Git Bash):



```bash

python -m venv venv

source venv/Scripts/activate

pip install -r requirements.txt

```



Add a `.env` file as described above, then run:



```bash

python app.py

```



\## Project Context



Built for the Advanced Database Management Systems (ADBMS) lab, demonstrating polyglot persistence across relational, document, and graph databases in a single production-style application.



