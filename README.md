# 🪨 RockGPT (Containerized Version)

**RockGPT** is a self-hosted, open-source conversational assistant specialized in **geoscience knowledge**. It uses **Retrieval-Augmented Generation (RAG)** to integrate scientific content into LLM responses.  

This version is containerized with:
- [Ollama](https://ollama.com) as the inference engine
- [OpenWebUI](https://github.com/open-webui/open-webui) as the user interface

---

## 🚀 Quickstart: Add New Knowledge via RAG

### Installation

⚠️ **Important note about performance**

The use of **GPU acceleration is strongly recommended**.  
Running RockGPT with **CPU-only** may lead to **very slow inference**, high memory usage, or models **failing to load or operate correctly**, especially for large models (e.g. 32B, 70B, 72B).

For a reliable and usable experience, we highly recommend deploying RockGPT on a system equipped with **NVIDIA GPUs**.


#### 1. Prerequisites (CPU)

- Docker 19.03+
- Docker Compose v2

Verify Docker installation:

```sh
docker compose version
```

#### 1a. Prerequisites (GPU – Important)

To enable GPU acceleration (NVIDIA), your system must have:

- An NVIDIA GPU
- Recent NVIDIA drivers
- NVIDIA Container Toolkit
- Docker 19.03+
- Docker Compose v2

Verify GPU availability:
```
nvidia-smi
```

Verify Docker GPU support:
```sh
docker run --rm --gpus all nvidia/cuda:13.1.0-base-ubuntu24.04 nvidia-smi
```

If this command works, Docker can access the GPU correctly.

#### 2. Clone the repository
```sh
git clone https://github.com/INGV/RockGPT.git
cd RockGPT
```

#### 3. Get the _dataset_ for OpenWebUI and unzip it
```sh
cd openwebui/
curl -L -O "https://webservices.ingv.it/rockgpt-open-webui.zip"
unzip rockgpt-open-webui.zip
cd ..
```

#### 4. Create the configuration file

The stack is configured through a `.env` file in the repository root. Docker Compose reads it
automatically, so the deployment is fully described by the repository plus this single file, and
`docker compose up -d` is reproducible with no variables exported by hand.

```sh
cp env.example .env
chmod 600 .env
```

Then edit `.env`. Every variable is optional and falls back to the default in `compose.yml`, but
**pinning the two image tags is strongly recommended**: Open WebUI migrates its database forward on
start and cannot migrate it back, so an unintended tag change can break an existing deployment.

```sh
OLLAMA_DOCKER_TAG=0.24.0
WEBUI_DOCKER_TAG=v0.11.3-cuda
OPEN_WEBUI_PORT=8585
OLLAMA_PORT=11434
```

> ⚠️ `.env` holds the API keys and is listed in `.gitignore`. Never commit it, and never hardcode a
> key in `compose.yml`.

#### 5. Start the services

##### With GPU acceleration (recommended)

If your system has a compatible NVIDIA GPU, start the stack with:
```sh
docker compose -f compose.yml -f compose-gpu.yml up -d
```

This enables GPU usage only for the Ollama service.

##### With CPU-only

```sh
docker compose up -d
```

#### 6. Get Ollama models

**Note**: Large models (`32B` / `70B` / `72B`) are strongly recommended with GPU support.

```sh
docker compose exec ollama bash -c "ollama pull gpt-oss:20b"
docker compose exec ollama bash -c "ollama pull mixtral:8x7b"
docker compose exec ollama bash -c "ollama pull deepseek-r1:32b"
docker compose exec ollama bash -c "ollama pull gemma2:27b"
docker compose exec ollama bash -c "ollama pull llama3.3:70b-instruct-q3_K_S"
docker compose exec ollama bash -c "ollama pull orca2:13b"
docker compose exec ollama bash -c "ollama pull phi4:latest"
docker compose exec ollama bash -c "ollama pull qwen2.5:72b-instruct"
docker compose exec ollama bash -c "ollama pull qwen3.6:35b"
```

#### 7. Verify GPU offload

After loading a model, check that it runs entirely on the GPU:

```sh
docker compose exec ollama bash -c "ollama ps"
```

The `PROCESSOR` column should read `100% GPU`. A value like `40%/60% CPU/GPU` means there is not enough
VRAM: reduce the context size in Open WebUI (`num_ctx`) or use a smaller model. See the inline comments
in `compose.yml` for the KV cache settings that mitigate this.

### Configuration

All the variables below are read from `.env` (see step 4). They are optional: an empty or missing
variable falls back to the default listed here.

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_DOCKER_TAG` | `0.24.0` | Ollama image tag. Pin it, and read the note below before raising it. |
| `WEBUI_DOCKER_TAG` | `v0.11.3-cuda` | Open WebUI image tag. Pin it: downgrades break the database. |
| `OPEN_WEBUI_PORT` | `8585` | Host port for the web interface |
| `OLLAMA_PORT` | `11434` | Host port for the Ollama API |
| `WEBUI_AUTH` | `False` | `False` skips the login prompt entirely. Set it to `True` on a networked host. |
| `WEBUI_SECRET_KEY` | *(empty)* | Session signing key. Empty means Open WebUI generates and persists one. |
| `GLOBAL_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `OPENAI_API_BASE_URLS` | *(empty)* | Optional OpenAI-compatible backend alongside Ollama, comma-separated |
| `OPENAI_API_KEYS` | *(empty)* | Keys for the URLs above, in the same order, comma-separated |
| `DEFAULT_MODEL_PARAMS` | *(empty)* | Default parameters for every model, as JSON. See the note below. |
| `TASK_MODEL_EXTERNAL` | *(empty)* | Model for background tasks when the chat runs on an external backend |

Single sign-on and reverse proxy, all optional and all inert while the OIDC block is empty:

| Variable | Default | Description |
|---|---|---|
| `OAUTH_PROVIDER_NAME` | *(empty)* | Name shown on the login button, e.g. `Keycloak` |
| `OAUTH_CLIENT_ID` | *(empty)* | OIDC client id |
| `OAUTH_CLIENT_SECRET` | *(empty)* | OIDC client secret. `.env` only, never in `compose.yml` |
| `OPENID_PROVIDER_URL` | *(empty)* | Discovery document URL. Mind the `/auth` prefix on a legacy Keycloak |
| `OPENID_REDIRECT_URI` | *(empty)* | Must match the provider's valid redirect URI exactly |
| `OAUTH_SCOPES` | `openid email profile` | Requested scopes |
| `ENABLE_OAUTH_SIGNUP` | `False` | Create an account on a first SSO login |
| `DEFAULT_USER_ROLE` | `pending` | Role of that new account. `pending` requires an admin to approve |
| `PENDING_USER_OVERLAY_TITLE` / `_CONTENT` | *(empty)* | Text shown to a pending account |
| `OAUTH_MERGE_ACCOUNTS_BY_EMAIL` | `False` | Land on an existing local account with the same email |
| `OAUTH_ALLOWED_DOMAINS` | `*` | Comma-separated allow-list of email domains |
| `OAUTH_CODE_CHALLENGE_METHOD` | *(empty)* | Set to `S256` to send PKCE. Nothing is sent otherwise |
| `ENABLE_LOGIN_FORM` | `True` | Keep the local email/password form as a break-glass door |
| `WEBUI_URL` | *(empty)* | Public base URL as the browser sees it |
| `WEBUI_SESSION_COOKIE_SECURE` | `False` | Mark the session cookie `Secure`. Set it behind an HTTPS proxy |
| `WEBUI_AUTH_COOKIE_SECURE` | `False` | Same, for the auth cookie |

#### Ollama and the NVIDIA driver

`OLLAMA_DOCKER_TAG` is pinned to `0.24.0` on purpose. Releases after it build their CUDA 12 backend
with a toolkit that requires **NVIDIA driver 550 or newer**, and on an older driver the failure is
not graceful. Measured on a host with driver `535.104.05` and two Tesla V100:

| Version | Behaviour on a V100 |
|---|---|
| `0.24.0` | works, model fully on GPU |
| `0.30.0` – `0.30.10` | GPUs are detected, then the model load aborts with `CUDA error: device kernel image is invalid` |
| `0.30.11` and later | GPUs are rejected up front with `NVIDIA driver too old, required_driver "550 or newer"`, and inference silently falls back to CPU, about 7x slower |

There are no `0.25` to `0.29` releases: the series goes straight from `0.24.0` to `0.30.0`.

The GPU architecture is not the constraint: compute capability 7.0 is still in the CUDA 12 preset of
the current releases (`llama/server/CMakePresets.json`, `llama_cuda_v12_linux`). Both failures come
from the same cause, the driver, so updating it to 550 or newer is enough to raise the tag. Verify
the driver with `nvidia-smi` first.

#### Function calling and the task model

Open WebUI 0.11 changed the function calling default from prompt-based to **native**: the tool list
is attached to every request. Models without native tool support then fail hard — Ollama answers
`400 <model> does not support tools`, an OpenAI-compatible gateway answers `500` — and the user only
sees an empty reply. `DEFAULT_MODEL_PARAMS={"function_calling":"legacy"}` restores the prompt-based
mode, which works with every model, retrieval on a knowledge base included.

`TASK_MODEL_EXTERNAL` names the model that generates chat titles, tags and follow-up questions when
the chat itself runs on an external backend. Left empty it means "reuse the chat model", but 0.11
forwards that as an empty model id, and a gateway rejects it: the string `Model '' was not found`
ends up inside the reply. Point it at a small local model, e.g. `phi4:latest`.

### Single sign-on (OIDC)

Open WebUI can delegate authentication to an OpenID Connect provider. The INGV deployment uses
Keycloak, but nothing below is Keycloak-specific except the paths.

#### On the provider

Create a **confidential** client:

- Client authentication **on**; Authorization **off**
- **Standard flow** only — no direct access grants, no service accounts, no implicit flow
- Valid redirect URI, exact and without wildcards: `https://<your-host>/oauth/oidc/callback`
- Web origins: `https://<your-host>`
- The default `email` and `profile` client scopes must be assigned as **Default**, not Optional:
  Open WebUI uses the `email` claim as the account key and cannot create a user without it

No roles, no mappers, no dedicated client scope: see [Roles](#roles-and-permissions) for why.

#### In `.env`

```sh
WEBUI_AUTH=True
WEBUI_URL=https://<your-host>
OAUTH_PROVIDER_NAME=Keycloak
OAUTH_CLIENT_ID=<client id>
OAUTH_CLIENT_SECRET=<client secret>
OPENID_PROVIDER_URL=https://<keycloak>/realms/<realm>/.well-known/openid-configuration
OPENID_REDIRECT_URI=https://<your-host>/oauth/oidc/callback
ENABLE_OAUTH_SIGNUP=True
OAUTH_MERGE_ACCOUNTS_BY_EMAIL=True
DEFAULT_USER_ROLE=pending
ENABLE_LOGIN_FORM=True
WEBUI_SESSION_COOKIE_SECURE=True
WEBUI_AUTH_COOKIE_SECURE=True
```

A Keycloak served under the legacy `/auth` prefix needs
`https://<keycloak>/auth/realms/<realm>/.well-known/openid-configuration`; the modern path answers
404 there, and the failure only surfaces as a generic login error.

> ⚠️ `WEBUI_URL`, `ENABLE_LOGIN_FORM` and `DEFAULT_USER_ROLE` are **PersistentConfig**: `.env` seeds
> the database on the first start that reads it, and from then on the stored value wins. On a
> deployment that already has them stored, change them under Admin Settings → General and
> → Users, not in `.env`. Same caveat as `DEFAULT_MODEL_PARAMS` above.
>
> The `OAUTH_*` variables are declared PersistentConfig too, but 0.11.3 does not expose them in the
> admin interface and never writes them to the database, so `.env` stays authoritative for them.
> Apply a change by **recreating** the container — `docker compose up -d`, not
> `docker compose restart`, which reuses the container and does not re-read the environment.

`OAUTH_ALLOWED_DOMAINS` matches the full domain exactly, not a suffix: `example.org` rejects
`someone@dept.example.org`, and that person sees a generic login error rather than the pending
screen. List every subdomain in use, or leave it at `*` and let `DEFAULT_USER_ROLE=pending` be the
gate.

#### Behind a reverse proxy

The proxy must forward `X-Forwarded-Proto` and `Host`, and must pass the WebSocket upgrade on
`/ws/` — Open WebUI uses socket.io for streaming, and a proxy that swallows the upgrade answers
`400` on `/ws/socket.io/`. With nginx:

```nginx
location /ws/ {
    proxy_pass http://<upstream>;
    proxy_http_version 1.1;
    proxy_set_header Upgrade    $http_upgrade;
    proxy_set_header Connection $connection_upgrade;
    proxy_set_header Host       $http_host;
    proxy_set_header X-Real-IP  $remote_addr;
    proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 7d;
}
```

Repeating the headers is required, not redundant: a `proxy_set_header` inside a `location` disables
inheritance of every `proxy_set_header` set at the server level.

#### PKCE

Open WebUI sends no `code_challenge` unless `OAUTH_CODE_CHALLENGE_METHOD=S256` is set. Set it here
first, confirm a login works, and only then make PKCE mandatory on the provider — the other order
rejects every authorization request with `Missing parameter: code_challenge`.

#### Logout

Signing out of Open WebUI ends the local session only. The provider's session survives, so clicking
the SSO button again signs the user straight back in without a password prompt. This is deliberate:
a federated logout would also sign them out of every other application on the realm.

### Roles and permissions

Open WebUI has exactly three roles — `admin`, `user`, `pending` — and this deployment keeps them in
its own database. `ENABLE_OAUTH_ROLE_MANAGEMENT` is deliberately **not** enabled: with it on, the
role is recomputed from a token claim at every login, which silently undoes any promotion made from
the admin interface. The provider answers *who you are*; Open WebUI decides *what you may do*.

What a `user` may actually do is not the role but the **default user permissions**, under
Admin Settings → Users: some sixty flags grouped into `workspace`, `sharing`, `chat`, `features` and
`settings`. A read-only user is `user` with `workspace.*` and `sharing.*` off — they can chat and
attach files to a chat, but cannot create models, knowledge bases, prompts or tools.

Permissions layer in three levels, so a middle tier is a group and never a fourth role:

1. **Default user permissions** — apply to every `user`
2. **Groups** — add permissions on top, and grant access to specific models and knowledge bases
3. **Per-resource access control** — each model, knowledge base or prompt is public, or restricted
   to named groups or users

Access is gated by `DEFAULT_USER_ROLE=pending`: anyone in the realm can authenticate, lands in a
waiting screen, and an administrator promotes them under Admin Settings → Users. Opening the
instance to everyone later is one value changed from `pending` to `user`.

### Recovering an account

Open WebUI has no password reset and no SMTP support, so a forgotten local password can only be
fixed by rewriting the hash. With the stack stopped, so the SQLite database is not being written:

```sh
docker compose stop open-webui
docker compose run --rm --no-deps --entrypoint "" open-webui python - <<'EOF'
import sqlite3
from open_webui.utils.auth import get_password_hash
db = sqlite3.connect("/app/backend/data/webui.db")
db.execute(
    "UPDATE auth SET password = ? WHERE email = ?",
    (get_password_hash("<new password>"), "<account email>"),
)
db.commit()
EOF
docker compose -f compose.yml -f compose-gpu.yml up -d
```

`docker compose run` is used rather than `docker exec` because the latter cannot attach to a stopped
container. Hashing through `open_webui.utils.auth` keeps the bcrypt parameters the application
expects. Back up `openwebui/rockgpt-open-webui/` first.

> ⚠️ Both variables only **seed a fresh database**. Open WebUI stores them on first start and from
> then on the stored value wins, so changing `.env` on a running deployment has no effect. There,
> change them in the interface instead:
> - Admin Settings → Models → Model Defaults → Model Parameters → Function Calling
> - Admin Settings → Interface → Tasks → External Task Model

Check the resolved configuration before starting, to make sure `.env` is being picked up:

```sh
docker compose -f compose.yml -f compose-gpu.yml config
```

### Access the Interface
- Open your browser and go to: `http://localhost:8585`

> ⚠️ Authentication is **disabled** by default (`WEBUI_AUTH=False`): the interface opens directly on
> the preloaded admin account, with no login prompt. On a host reachable from the network this means
> anyone who can open the port has full access, including to the configured API keys. Set
> `WEBUI_AUTH=True` in `.env` there, and see [Single sign-on](#single-sign-on-oidc) below.
>
> The account preloaded in the dataset has a password generated by Open WebUI at first start, which
> nobody knows. Reset it before enabling authentication, or you lock yourself out — Open WebUI has
> **no password reset flow and no SMTP support**. See [Recovering an account](#recovering-an-account).
>
> Enabling authentication is a **one-way door**: the instance then accumulates users, and Open WebUI
> refuses to start with authentication disabled and more than one user in the database. Back out by
> restoring a backup of `openwebui/rockgpt-open-webui/`, not by setting `WEBUI_AUTH` to `False`.

### Create a New Knowledge Base
- On the **left sidebar**, click the **Workspace icon**
- On the **top bar**, select the **Knowledge** tab
- Click the **"Create new knowledge base"** button (top-right)
- **Upload files** (e.g. PDF, TXT, CSV) by dragging and dropping them into the interface

> ℹ️ The system already includes a default knowledge base with 28 open-access scientific papers.

### Attach the Knowledge Base to a Model
- Navigate to: `Workspace > Models > Create New Model`
- Select a **foundational model**
- Choose the **knowledge base** you just created to bind it to the new model

### Advanced RAG Configuration
- For fine-tuning RAG settings (e.g., chunk size, embedding model, retriever strategy), refer to the [OpenWebUI documentation](https://docs.openwebui.com/)

---

## 📁 Project Structure
```
RockGPT/
├── compose.yml                     # Base stack: ollama + open-webui
├── compose-gpu.yml                 # Overlay: NVIDIA device reservation for ollama
├── env.example                     # Template for .env
├── .env                            # Local configuration, gitignored, holds the API keys
├── ollama/
│  └── data/                        # -> /root/.ollama, pulled models
├── openwebui/
│  └── rockgpt-open-webui/          # -> /app/backend/data, unpacked from the dataset zip
│     ├── webui.db                  # Users, chats, model definitions
│     ├── vector_db/                # Chroma embeddings for RAG
│     └── uploads/                  # Source documents of the knowledge base
└── README.md                       # This file
```

> ⚠️ The contents of `ollama/data/` and `openwebui/` are **not** tracked in git. After cloning, both
> directories are empty: models come from `ollama pull`, the knowledge base from the dataset zip
> (step 3).

---

## 📚 Preloaded Knowledge

The default deployment includes 28 peer-reviewed, open-access publications on:
- Seismotectonics of the Apennines
- Rock deformation and structural geology
- Regional geodynamics of Italy

---

## License & Credits
This repository is intended for academic and research purposes.  

### License
This project is licensed under the **Apache License 2.0**. See the [LICENSE](LICENSE) file for the full license text.

### Acknowledgments
RockGPT is built upon and integrates the following open-source projects:
* **[Open WebUI](https://github.com/open-webui/open-webui)** - Licensed under the BSD 3-Clause "New" or "Revised" License.
* **[Ollama](https://github.com/ollama/ollama)** - Licensed under the MIT License.

We are grateful to the maintainers and contributors of these projects for their invaluable work.


# Contribute
Thanks to your contributions!

Here is a list of users who already contributed to this repository: \
<a href="https://github.com/INGV/RockGPT/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=INGV/RockGPT" />
</a>

# Author
(c) 2025 Daniele Bailo daniele.bailo[at]ingv.it \
(c) 2025 Valentino Lauciani valentino.lauciani[at]ingv.it \
(c) 2025 Raffale Di Stefano raffaele.distefano[at]ingv.it \
(c) 2025 Fabrizio Bernardi fabrizio.bernardi[at]ingv.it 

Istituto Nazionale di Geofisica e Vulcanologia, Italia
