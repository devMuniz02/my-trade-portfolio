[![LinkedIn](https://img.shields.io/badge/LinkedIn-devmuniz-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/devmuniz)
[![GitHub Profile](https://img.shields.io/badge/GitHub-devMuniz02-181717?logo=github&logoColor=white)](https://github.com/devMuniz02)
[![Portfolio](https://img.shields.io/badge/Portfolio-devmuniz02.github.io-0F172A?logo=googlechrome&logoColor=white)](https://devmuniz02.github.io/)
[![Hugging Face](https://img.shields.io/badge/Hugging%20Face-manu02-FFD21E?logoColor=black)](https://huggingface.co/manu02)

# My Trade Portfolio

> This repo contains my number of trades and PnL. Daily, Weekly, Monthly, and All-Time. This portfolio is based on predicitons and probalities of the trades only, no speculations, politics nor anything related.

- [Features](#features) - [Installation](#installation) - [Repository Setup](#repository-setup) - [Usage](#usage) - [Configuration](#configuration) - [Contributing](#contributing) - [License](#license) - [Contact](#contact)

## Overview

This repo contains my number of trades and PnL. Daily, Weekly, Monthly, and All-Time. This portfolio is based on predicitons and probalities of the trades only, no speculations, politics nor anything related.

## Repository Structure

| Path | Description |
| --- | --- |
| `assets/` | Images, figures, or other supporting media used by the project. |
| `scripts/` | Top-level project directory containing repository-specific resources. |
| `.gitignore` | Top-level file included in the repository. |
| `LICENSE` | Repository license information. |
| `README.md` | Primary project documentation. |
| `requirements.txt` | Python dependency specification for local setup. |

## Getting Started

1. Clone the repository.

   ```bash
   git clone https://github.com/devMuniz02/my-trade-portfolio.git
   cd my-trade-portfolio
   ```

2. Prepare the local environment.

Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Run or inspect the project entry point.

Use the project-specific scripts or notebooks in the repository root to run the workflow.

## Features

This project provides:
- Automated tracking of your number of trades and PnL (Profit and Loss) for Daily, Weekly, Monthly, and All-Time periods
- GIF visualization of portfolio performance using Polymarket data
- Easy configuration via environment variables

## Installation

### Prerequisites

- Python 3.8+ (recommended)
- Node.js v16+ (if using npm features)

### Installation Steps

```bash
# Clone the repository
git clone https://github.com/devMuniz02/my-trade-portfolio.git

# Navigate to the project directory
cd my-trade-portfolio

# Install dependencies
npm install
# or
pip install -r requirements.txt
```

## Repository Setup

After cloning this template repository, run the setup script to automatically populate the README with your repository information:

### Prerequisites for Setup Script
- Python 3.6+
- Git configured with remote origin

### Setup Steps
```bash
# Install Python dependencies
pip install -r requirements.txt

# Run the setup script
python update_readme.py
```

This script will:
- Fetch repository information from GitHub API
- Update the project name and description in README.md
- Extract the repository name from the git remote URL

**Note:** Make sure your repository has a remote origin set and is pushed to GitHub before running the script.

## Usage

### Basic Usage

#### Generate Portfolio Performance GIF

This script fetches your trade and PnL data from Polymarket and generates an animated GIF showing your portfolio performance over different periods.

**Requirements:**
- Set your environment variables in a `.env` file in the project root:
	- `WALLET`: Your Polymarket wallet address
	- `FUNDS`: Your initial portfolio funds (numeric)

**Run the script:**
```bash
python scripts/create_gif.py
```
The GIF will be saved to `assets/performance_animation.gif`.

If you see the message `Please set WALLET and FUNDS environment variables.`, ensure your `.env` file is correctly configured.

### Advanced Usage


You can customize the GIF appearance or data sources by modifying `scripts/create_gif.py`. For more advanced analytics, use the Jupyter notebooks in the `notebooks/` folder to explore your trade data interactively.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**Links:**
- **GitHub:** [https://github.com/devMuniz02/](https://github.com/devMuniz02/)
- **LinkedIn:** [https://www.linkedin.com/in/devmuniz](https://www.linkedin.com/in/devmuniz)
- **Hugging Face:** [https://huggingface.co/manu02](https://huggingface.co/manu02)
- **Portfolio:** [https://devmuniz02.github.io/](https://devmuniz02.github.io/)

Project Link: [https://github.com/devMuniz02/my-trade-portfolio](https://github.com/devMuniz02/my-trade-portfolio)

---

⭐ If you find this project helpful, please give it a star!

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Repository Setup](#repository-setup)
- [Usage](#usage)
- [Configuration](#configuration)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## Project Structure

```
my-trade-portfolio/
├── assets/                 # Static assets (images, icons, etc.)
├── data/                   # Data files and datasets
├── docs/                   # Documentation files
├── notebooks/              # Jupyter notebooks for analysis and prototyping
├── scripts/                # Utility scripts and automation tools
├── src/                    # Source code
├── tests/                  # Unit tests and test files
├── LICENSE                 # License file
├── README.md               # Project documentation
└── requirements.txt        # Python dependencies
```

### Directory Descriptions

- **`assets/`**: Store static files like images, icons, fonts, and other media assets.
- **`data/`**: Place datasets, input files, and any data-related resources here.
- **`docs/`**: Additional documentation, guides, and project-related files.
- **`notebooks/`**: Jupyter notebooks for data exploration, prototyping, and demonstrations.
- **`scripts/`**: Utility scripts for automation, setup, deployment, or maintenance tasks.
- **`src/`**: Main source code for the project.
- **`tests/`**: Unit tests, integration tests, and test-related files.

## ️ Configuration

### Environment Variables

Create a `.env` file in the project root with the following:

```
WALLET=your_polymarket_wallet_address
FUNDS=your_initial_funds
```

These are required for the GIF generation script to fetch and display your portfolio data.
