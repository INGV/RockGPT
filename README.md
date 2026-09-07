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
WEBUI_DOCKER_TAG=v0.9.6-cuda
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
| `OLLAMA_DOCKER_TAG` | `latest` | Ollama image tag. Pin it. |
| `WEBUI_DOCKER_TAG` | `v0.9.6-cuda` | Open WebUI image tag. Pin it: downgrades break the database. |
| `OPEN_WEBUI_PORT` | `8585` | Host port for the web interface |
| `OLLAMA_PORT` | `11434` | Host port for the Ollama API |
| `WEBUI_AUTH` | `False` | `False` skips the login prompt entirely. Set it to `True` on a networked host. |
| `WEBUI_SECRET_KEY` | *(empty)* | Session signing key. Empty means Open WebUI generates and persists one. |
| `GLOBAL_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `OPENAI_API_BASE_URLS` | *(empty)* | Optional OpenAI-compatible backend alongside Ollama, comma-separated |
| `OPENAI_API_KEYS` | *(empty)* | Keys for the URLs above, in the same order, comma-separated |

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
