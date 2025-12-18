# 🪨 RockGPT (Containerized Version)

**RockGPT** is a self-hosted, open-source conversational assistant specialized in **geoscience knowledge**. It uses **Retrieval-Augmented Generation (RAG)** to integrate scientific content into LLM responses.  
This version is containerized with [Ollama](https://ollama.com) as inference engine and [OpenWebUI](https://github.com/open-webui/open-webui) as user interface.

---

## 🚀 Quickstart: Add New Knowledge via RAG

### Installation
#### 1. Prerequisites
- [docker](https://www.docker.com/) installed

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

#### 4. Start the services
```sh
docker compose up -d
```

#### 5. Get Ollama models
```sh
docker compose exec ollama bash -c "ollama pull mistral:7b"
docker compose exec ollama bash -c "ollama pull deepseek-r1:32b"
docker compose exec ollama bash -c "ollama pull gemma2:27b"
docker compose exec ollama bash -c "ollama pull llama3.3:70b-instruct-q3_K_S"
docker compose exec ollama bash -c "ollama pull orca2:13b"
docker compose exec ollama bash -c "ollama pull phi4:latest"
docker compose exec ollama bash -c "ollama pull qwen2.5:72b-instruct"
```

### Access the Interface
- Open your browser and go to: `http://localhost:8585`  

### Login
- Enter your username and password  

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
rockgpt/
├── docker-compose.yml
├── ollama/
│  └── models/      # Local LLMs (e.g., Mistral, LLaMA)
├── openwebui/
│  └── data/       # Knowledge base content
└── README.md       # This file
```
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
