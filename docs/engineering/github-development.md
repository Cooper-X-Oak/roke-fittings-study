# GitHub development policy

- `main` is the protected integration branch and must not receive task implementation pushes.
- GitHub Pages publishes from `/docs` on the task branch selected for the explicit deployment request.
- Task branches use `<type>/<issue-number>-<short-slug>`.
- Required checks: verify there are no zero-byte or temporary files, no unprefixed same-site root resource paths, no file above GitHub's 100 MB limit, and confirm the deployed URL returns HTTP 200.
- This repository is an unofficial educational mirror. Do not add credentials, working forms, analytics secrets, or user-data collection.