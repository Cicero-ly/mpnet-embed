# mpnet-embed

API / Job runner for performing vector embedding for newly added thoughts in the "news" thought collection.

This could not have been possible without Ramsis Hammadi!

## What's happening:

- /api contains FastAPI server for executing jobs on request.
- /cron contains a simple request being made to API.

## TODO:

- tests
- GH actions for auto deploy to control plane
- email on failure
- email on max_size reached