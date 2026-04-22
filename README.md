# Mail Meter Scraper 🚀

A powerful, high-performance email finding tool that automates the process of discovering professional email addresses using Mailmeteor's email finder. This application features a modern web interface, real-time progress tracking, and multi-threaded scraping capabilities.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-Framework-009688.svg)
![Playwright](https://img.shields.io/badge/Playwright-Automation-2EAD33.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## ✨ Features

- **Intuitive Web UI**: Modern, responsive interface built with FastAPI and Vanilla CSS.
- **Automated Column Detection**: Intelligent heuristics to automatically identify "Name" and "Domain" columns in your input files.
- **Multi-threaded Performance**: Highly configurable worker and tab system for maximum throughput.
- **Real-time Monitoring**: Live progress updates and logs delivered via WebSockets.
- **Flexible Exports**: Download results instantly in both CSV and JSON formats.
- **Robust Scraping**: Built-in retry logic and human-like interaction patterns to ensure high success rates.
- **Standalone Executable**: Can be compiled into a single `.exe` for easy distribution.

## 🛠️ Technology Stack

- **Backend**: Python, FastAPI, Uvicorn
- **Automation**: Playwright (Chromium)
- **Data Processing**: Pandas, Openpyxl
- **Frontend**: HTML5, CSS3 (Modern Glassmorphism Design), JavaScript
- **Communication**: WebSockets for real-time log broadcasting

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- Node.js (optional, for advanced frontend modifications)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/jinendradcm/mail_meter_scraper_APP.git
   cd mail_meter_scraper_APP
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright browsers**:
   ```bash
   playwright install chromium
   ```

### Running the Application

Start the application by running the main entry point:

```bash
python main.py
```

This will automatically open your default web browser to `http://127.0.0.1:8000`.

## 📖 Usage Guide

1. **Upload File**: Select a CSV or Excel file containing the names and domains you want to search.
2. **Configure Settings**:
   - **Workers**: Number of concurrent browser instances.
   - **Tabs**: Number of pages per browser instance.
3. **Start Scraping**: Click the "Start" button and watch the logs in real-time.
4. **Download Results**: Once finished, download the processed data from the "Outputs" section.

## 📁 Project Structure

```text
mail_meter_scraper_APP/
├── app.py              # FastAPI application & API endpoints
├── scraper.py          # Core scraping logic & Playwright automation
├── main.py             # Application entry point
├── templates/          # HTML templates
├── static/             # CSS and JavaScript assets
├── uploads/            # Temporary storage for uploaded files
├── outputs/            # Generated CSV/JSON result files
└── main.spec           # PyInstaller specification for building .exe
```

## 🏗️ Building the Executable

To build the standalone `.exe` file:

```bash
pip install pyinstaller
pyinstaller main.spec
```

The executable will be located in the `dist/` directory.

## 🛡️ License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---
Built with ❤️ by [Jinendra](https://github.com/jinendradcm)
