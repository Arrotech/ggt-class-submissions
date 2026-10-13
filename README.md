# SQL Power Hour

A small web app for recording HackerRank SQL practice. Sign in with GitHub,
enter the topic and their own approach, solution, and optional reflection, then
publish a dated set of Markdown files directly to a repository. The app also
lets you download the published files as a ZIP.

The same FastAPI app runs locally and on Vercel. The command-line template
generator remains available as a lightweight offline fallback.

## How it works

1. An engineer opens the app and signs in with GitHub.
2. The engineer chooses a repository where the SQL Power Hour GitHub App is
   installed and their GitHub account has write access.
3. They enter the study topic and one or more HackerRank questions, including
   difficulty, their own approach, SQL solution, and optional reflection.
4. The app creates the dated Markdown files and publishes them in one commit.
5. The app shows links to the commit and offers a ZIP download of those files.

The app does not read HackerRank submissions or receive HackerRank webhooks.
Engineers paste the question link and their work into the form.

## Prerequisites

- Python 3.10 or newer
- A GitHub account
- A GitHub App configured for this workflow
- GitHub CLI is not required by the web app

## Make the app available to a team

There are two different repositories in this workflow:

- **App source repository:** contains this project and is imported into Vercel
  or cloned by engineers.
- **Practice repository:** selected by an engineer in the app to receive their
  dated Markdown notes.

For an existing, non-empty source repository, add this project to the repository
and push the commit. If the project is in a subdirectory, set that directory as
the Vercel project's Root Directory.

For a new source repository, create it with an initial commit (for example,
select GitHub's **Add a README** option) before trying to clone or import it.
An empty repository has no branch or files for GitHub or Vercel to retrieve.
After the source code has been pushed, engineers can clone it and follow the
local setup below; deploying it to Vercel makes the hosted workflow available
to them over the internet.

Each engineer also needs to install the GitHub App on the practice repository
they want to publish into. Do not add app secrets to either Git repository.

## Create and configure the GitHub App

An app owner or GitHub organization administrator should create one GitHub App
for the team:

1. Open **GitHub Settings → Developer settings → GitHub Apps → New GitHub App**.
2. Choose an app name and set the homepage URL. For local testing, use
   `http://localhost:8000`; for production, use the Vercel app URL.
3. Add authorization callback URLs for each environment:
   `http://localhost:8000/auth/callback` and
   `https://YOUR-VERCEL-DOMAIN/auth/callback`.
4. Under **Repository permissions**, set **Contents** to **Read and write**.
   **Metadata** should remain **Read-only**.
5. Do not subscribe to webhooks; this app does not use any.
6. Enable user authorization (OAuth) for the GitHub App and leave expiring
   user tokens enabled.
7. Choose who can install the app. To let engineers use it with their own
   repositories, make it available for any GitHub account. Organization-owned
   repositories may require an organization administrator's approval.
8. Save the app's **Client ID**, create a **Client secret**, and note the
   app's URL slug. Share these secrets only through an approved secrets manager
   or local environment configuration, never in source code.

The app is deliberately installed on the repositories an engineer chooses.
The website lists only repositories where the app is installed and the signed-in
engineer has write access. GitHub enforces the app's repository permissions.

## Run locally

### 1. Get the project and create a virtual environment

In PowerShell:

```powershell
git clone https://github.com/ORG/APP-SOURCE-REPOSITORY.git
cd APP-SOURCE-REPOSITORY
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If `py` is not installed, replace it with `python`:

```powershell
python -m venv .venv
```

### 2. Configure local environment variables

Copy the example file, then fill in the values from your GitHub App:

```powershell
Copy-Item .env.example .env
```

Set `GITHUB_APP_CLIENT_ID`, `GITHUB_APP_CLIENT_SECRET`, and `GITHUB_APP_SLUG`
in `.env`. Generate a unique local session secret:

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copy the printed value into `SESSION_SECRET` in `.env`. Keep `.env private;
it is excluded by `.gitignore`.

### 3. Start the app and sign in

```powershell
.\.venv\Scripts\python.exe -m uvicorn app:app --reload --env-file .env
```

Open [http://localhost:8000](http://localhost:8000), install the GitHub App on
at least one repository where your account can write, and then choose
**Continue with GitHub**. For the first test, use a dedicated test repository:
publishing creates a commit on the selected repository's default branch.

## Deploy to Vercel

Vercel supports FastAPI as a Python Function. This project exposes the FastAPI
instance as `app` in the supported root `app.py` entry point and declares its
dependencies in `requirements.txt`, so Vercel detects the application without a
custom `vercel.json`. The templates and mounted static assets are included in
the project deployment.

1. Put this project in the root of a dedicated GitHub repository and push its
   source files. Do not push the parent workspace or `.env`. In Vercel, import
   that repository and set the Root Directory to the project folder if it is
   nested inside a larger repository.
2. In Vercel project settings, set the Python runtime to a version supported by
   Vercel and compatible with the requirements (Python 3.10 or newer), then add
   these environment variables for the Production environment:
   Production environment:

   ```text
   APP_ENV=production
   APP_BASE_URL=https://YOUR-VERCEL-DOMAIN
   SESSION_SECRET=<a unique random value>
   GITHUB_APP_CLIENT_ID=<GitHub App client ID>
   GITHUB_APP_CLIENT_SECRET=<GitHub App client secret>
   GITHUB_APP_SLUG=<GitHub App URL slug>
   ```

   Generate the production session secret locally with:

   ```powershell
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

   Add secrets in Vercel's environment-variable settings; do not commit them
   or reuse the local development secret.
3. Add the deployed callback URL (`https://YOUR-VERCEL-DOMAIN/auth/callback`)
   to the GitHub App configuration.
4. Redeploy after setting the environment variables. Open the Vercel URL,
   install the GitHub App on a repository, sign in, and publish a test session.
5. Once verified, assign your custom domain in Vercel and add its
   `https://YOUR-CUSTOM-DOMAIN/auth/callback` URL to the GitHub App as well.

For local and production environments to share a GitHub App, add both callback
URLs to its settings. Vercel Functions are stateless, so the app keeps no
practice notes on the Vercel filesystem; the source of truth is GitHub, and
the ZIP download is generated from the published commit.

## Project layout

```text
app.py                         FastAPI/Vercel entry point
generate_daily.py              Local blank-template command
sql_power_hour/
  auth.py                      GitHub App OAuth and encrypted token handling
  cli.py                       Offline template generator
  config.py                    Environment-based settings
  content.py                   Validation and Markdown generation
  forms.py                     Web form parsing and validation
  github_api.py                Repository listing, publishing, and API client
  web_helpers.py               Shared auth, template, and GitHub helpers
  web.py                       FastAPI configuration and route registration
  routes/
    auth.py                    Sign-in and sign-out endpoints
    practice.py                Practice form and publishing endpoints
    downloads.py               Published ZIP download endpoint
templates/                     Jinja HTML pages
static/                        Styles and question-form interaction
tests/                         Focused unit tests
requirements.txt               Python dependencies
.env.example                   Local environment variable template
```

## Local templates without GitHub sign-in

To generate blank Markdown files from the command line:

```powershell
.\.venv\Scripts\python.exe .\generate_daily.py
```

The command prompts for a date, a question count (default three), and titles.
It creates files such as `10-13-2026/001-select-all.md` beside the script.

## Security notes

- GitHub client secrets and session secrets belong only in environment
  variables, not in source files.
- The OAuth state is checked to prevent cross-site login requests.
- GitHub access and refresh tokens are encrypted in an HTTP-only cookie and
  never rendered into the page.
- Production requires a random `SESSION_SECRET` and an HTTPS `APP_BASE_URL`;
  cookies are marked Secure when HTTPS is configured.
- GitHub App user tokens expire and are refreshed when needed.
- The app makes commits directly to the selected repository's default branch.
  Use a dedicated repository if you want a review step before notes are shared.
- Public repositories make solutions visible to everyone. Use a private
  repository when that is not intended.
