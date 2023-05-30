# Conversational Agent


## Project Description
This is a conversational Agent MVP using Aleph Alpha (https://www.aleph-alpha.com/) or Azure OpenAI.

## Components
It ueses Langchain, FastAPI and a Vectordatabase.

## Deployment

If you are working in an envoironment with internet connection the easiest way is to use this command:
```bash
docker compose -f docker-compose-hub.yml up
```

This will pull the image from docker hub and run it. Instead of building it on your local machine.

If you want to build the image on your local machine you can use this command:
```bash
docker compose up
```

## Development Backend

To run the Backend use this command in the root directory:

```bash
poetry run uvicorn agent.api:app --reload
```

To run the tests you can use this command:

```bash
poetry run coverage run -m pytest tests log_cli=true
```

## Development Frontend
