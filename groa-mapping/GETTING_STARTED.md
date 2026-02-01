# Getting Started with GROA Mapping

This guide will help you set up the development environment and run the machine learning pipeline to map carbon accumulation potential.

## Prerequisites

-   **Python 3.10+**
-   **Poetry** (Python dependency manager)
    -   Install instructions: [https://python-poetry.org/docs/#installation](https://python-poetry.org/docs/#installation)

## Installation

1.  **Clone the repository** (if you haven't already):
    ```bash
    git clone <repository-url>
    cd GROA
    ```

2.  **Install dependencies**:
    We use `poetry` to manage dependencies and create a virtual environment.
    ```bash
    poetry install
    ```

## Running the Pipeline

We have created a modular pipeline in the `processing_scripts/` directory. You can run each step using `poetry run`.

### Step 1: Prepare Training Data
Loads the raw field measurements (`data/biomass_litter_CWD.csv`) and site metadata, filters for young forests (≤ 30 years), and calculates carbon accumulation rates.

```bash
poetry run python processing_scripts/01_prepare_training_data.py
```
*Output:* `outputs/training_data_basic.csv`

### Step 2: Train the Model
Trains a Random Forest Regressor using the prepared data. It uses environmental covariates (Temperature, Precipitation, Soil Type) to predict carbon accumulation rates.

```bash
poetry run python processing_scripts/02_train_model.py
```
*Output:* `outputs/groa_model.pkl` (Trained Model)

### Step 3: Generate Global Map
Applies the trained model to a global grid (synthetic data in this demo) to create a map of potential carbon accumulation rates.

```bash
poetry run python processing_scripts/03_create_map.py
```
*Output:* `outputs/global_map_predictions.csv`

### Step 4: Visualize Results
Generates an interactive HTML report with a global map and data table.

```bash
poetry run python processing_scripts/04_visualize_map.py
```
*Output:* `outputs/global_carbon_map_report.html`

## Project Structure

-   `data/`: Contains the raw CSV data files from the original study.
-   `MappingGlobalCarbon/`: Original source code for the machine learning logic (`gfw_forestlearn`).
-   `processing_scripts/`: Python scripts created to execute the data processing and modeling pipeline.
-   `outputs/`: Generated files (cleaned data, models, and predictions).
-   `pyproject.toml`: Poetry configuration file defining dependencies.

## Reproducing Paper Figures

The original paper used R for statistical analysis. Since you are using a Python environment, we have provided a Python script that reproduces Figure 1 using `matplotlib` and `seaborn`.

```bash
poetry run python processing_scripts/05_reproduce_figure_1.py
```
*Output:* `outputs/figure_1_reproduction_python.png`

## Troubleshooting

-   **GDAL/Rasterio Issues**: The original code relies on `gdal` and `rasterio`, which can be difficult to install on some systems. The training scripts include mocks for these libraries since they are not strictly required for the Random Forest training logic in this demonstration. If you need full raster processing capabilities, ensure you have the GDAL system libraries installed.
