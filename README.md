<div align="center">

# 🚔 Sentinel Collector

### High-Performance Multiprocess FIR Dataset Collection Framework

Collect, organize and index FIR documents into a structured dataset for research, analytics and AI applications.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-success)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)
![License](https://img.shields.io/badge/License-MIT-orange)

</div>

---

# 📖 Overview

**Sentinel Collector** is a high-performance multiprocessing Python framework designed to automate large-scale collection and organization of publicly accessible FIR documents.

The project was originally built for research and hackathon purposes to create structured datasets that can later be used for:

- Crime Analytics
- OCR Pipelines
- AI Investigation Systems
- Knowledge Graphs
- NLP Research
- Information Retrieval
- Data Mining

The framework automatically organizes downloaded documents district-wise while maintaining a searchable metadata index.

---

# ✨ Features

- 🚀 Multiprocessing Architecture
- ⚡ Parallel Browser Workers
- 📂 Automatic District & Police Station Discovery
- 📄 Automatic PDF Collection
- 📊 CSV Metadata Index
- ♻️ Resume Interrupted Runs
- 📌 Duplicate Detection
- 📈 Live Progress Logging
- 📁 Organized Folder Structure
- 🔒 Fault Tolerant Execution

---

# 🏗 Architecture

```
                Public FIR Portal
                        │
                        ▼
            Multiprocess Collector
                        │
         ┌──────────────┴──────────────┐
         │                             │
         ▼                             ▼
 District-wise PDFs            Metadata CSV
         │                             │
         └──────────────┬──────────────┘
                        ▼
                  OCR Pipeline
                        ▼
                 Structured Dataset
                        ▼
                 AI Applications
```

---

# 📂 Output Structure

```
fir_pdfs/

├── Bengaluru City/
│      ├── Ashok Nagar/
│      │      ├── 0001_2024.pdf
│      │      ├── 0002_2024.pdf
│      │      └── ...
│
├── Mysuru City/
│
├── Raichur/
│
└── ...
```

---

# 📑 Metadata Index

Every downloaded document is indexed automatically.

| Column | Description |
|---------|-------------|
| district_id | District Identifier |
| district | District Name |
| police_station | Police Station |
| station_id | Police Station ID |
| fir_number | FIR Number |
| year | FIR Year |
| status | Download Status |
| pdf_path | Local PDF Path |

---

# ⚙️ Requirements

- Python 3.10+
- Google Chrome
- ChromeDriver

Install dependencies

```bash
pip install -r requirements.txt
```

---

# ▶️ Running

Simply execute

```bash
python main.py
```

The framework automatically

- discovers districts
- enumerates police stations
- collects documents
- stores PDFs
- updates metadata index
- resumes previous sessions

---

# 🚀 Performance

Current implementation supports

- Multiprocessing
- Multiple concurrent browser workers
- Automatic resume
- Fault recovery
- Large-scale collection
- CSV checkpointing
- District-wise organization

---

# 📊 Future Roadmap

- OCR Pipeline
- Structured JSON Export
- PostgreSQL Export
- Entity Extraction
- Knowledge Graph Generation
- Semantic Search
- Vector Database Integration
- AI Investigation Assistant
- Crime Analytics Dashboard

---

# 🛠 Built With

- Python
- Selenium
- BeautifulSoup
- Multiprocessing
- CSV
- ChromeDriver

---

# ⚠️ Disclaimer

This project is intended for research, educational and other authorized purposes only.

Users are responsible for complying with the terms of service, applicable laws and any restrictions governing the data sources they access.

---

# 🤝 Contributing

Pull requests are welcome.

For major changes, please open an issue first to discuss what you would like to improve.

---

# 📜 License

MIT License

---

<div align="center">

### ⭐ If you found this project useful, consider giving it a star!

Built with ☕ and lots of multiprocessing.

</div>
