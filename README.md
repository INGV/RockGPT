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

#### Ollama on Volta GPUs (Tesla V100)

`OLLAMA_DOCKER_TAG` is pinned to `0.24.0` on purpose. Ollama dropped compute capability 7.0 from its
CUDA builds after that release, and the failure is not graceful:

| Version | Behaviour on a V100 |
|---|---|
| `0.24.0` | works, model fully on GPU |
| `0.30.0` – `0.30.10` | GPUs are detected, then the model load aborts with `CUDA error: device kernel image is invalid` |
| `0.30.11` and later | GPUs are rejected up front with `NVIDIA driver too old, required_driver "550 or newer"`, and inference silently falls back to CPU, about 7x slower |

There are no `0.25` to `0.29` releases: the series goes straight from `0.24.0` to `0.30.0`.

A newer NVIDIA driver lifts the second check but does not necessarily fix the first, which is an
architecture problem, not a driver one. On newer hardware none of this applies — raise the tag.

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

> ℹ️ Authentication is **disabled** by default (`WEBUI_AUTH=False`): the interface opens directly on
> the preloaded admin account, with no login prompt. On a host reachable from the network this means
> anyone who can open the port has full access, including to the configured API keys.
>
> To enable authentication, set `WEBUI_AUTH=True` in `.env` and restart the stack. You can then
> sign in with the account shipped in the dataset:
> - Email: `admin@test-email.com`
> - Password: `adminpass`

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
