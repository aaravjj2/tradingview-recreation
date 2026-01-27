# Cboe Historical Options Pipeline

Automated pipeline to download, filter, and normalize Cboe options data.

## Usage

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. Configure `config.yaml`

3. Run the pipeline:
   ```bash
   python main.py run_all --config config.yaml
   ```

## Pipeline Stages

1. **Download**: Fetches monthly ZIP files from Cboe.
2. **Process**: Unzips, parses, filters, and normalizes data.
3. **Verify**: Ensures data integrity and completeness.
