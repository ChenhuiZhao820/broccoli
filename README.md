# Broccoli - Competition Application Automation

An automated workflow for generating startup competition applications using web scraping and AI-powered content generation.

## Features

- **Web Scraping**: Automatically extracts competition information from websites
- **Content Parsing**: Uses LLM to structure competition data intelligently
- **Application Generation**: Creates tailored responses using Monica AI
- **Complete Workflow**: End-to-end automation from URL to final application

## Dependencies

Install required Python packages:

```bash
pip install requests beautifulsoup4 selenium pyyaml
```

### Additional Requirements

- **Chrome Browser**: Required for dynamic web scraping
- **ChromeDriver**: Must be installed and accessible in PATH
- **Monica AI API Key**: Required for content generation

## Setup

### 1. Configure API Key

Replace the placeholder API key in `src/workflow/workflow_config.yaml`:

```yaml
llm_settings:
  api_key: "YOUR_MONICA_AI_API_KEY_HERE"
```

### 2. Configure File Paths

Update these paths in `workflow_config.yaml` with your actual file locations:

```yaml
reference_docs:
  application_question:
    # REPLACE "INVENT" WITH THE ACTUAL COMPETITON NAME YOU USED!!
    - "input/INVENT/questions.md"
  competition_information:
    # REPLACE "INVENT" WITH THE ACTUAL COMPETITON NAME YOU USED!!
    - "input/INVENT/competition_info/parsed_competition_info.json"
```

### 3. Prepare Reference Documents

Customize your project documentation in the `input/reference_docs/` directory (There are existing ones but feel free to add more):
Some suggestions are:

- `market_positioning.md`
- `business_model.md`
- `team_profiles.md`

## Usage

### Run Complete Workflow

```bash
python src/workflow/run_workflow.py
```

The script will:
1. Prompt for competition name and URL of the competition website. PLEASE ENTER THE LINK TO THE COMPETITION'S MOST INTRODUCTORY PAGE!
2. Scrape competition website
3. Parse content with AI
4. Generate application responses
5. Save final application to `output/[competition_name]/`

### Important Notes

- **Refresh webpage** before providing URL to ensure current content
- Check `logs/workflow.log` for detailed execution information
- Generated applications are saved as markdown files in the output directory

## Directory Structure

```
├── src/
│   ├── scraper/
│   │   ├── web_scraper.py
│   │   ├── content_parser.py
│   │   ├── monica_client.py
│   │   └── scraper_config.json
│   └── workflow/
│       ├── workflow_config.yaml
│       ├── prompt.md
│       └── run_workflow.py
├── input/
│   ├── reference_docs/
│   └── [competition_name]/
│       └── competition_info/
├── output/
│   └── [competition_name]/
├── logs/
└── workflow_execution.py
```

## Troubleshooting

- **Scraping fails**: Ensure ChromeDriver is installed and website is accessible
- **API errors**: Verify Monica AI API key and account credits
- **Missing content**: Check that reference documents exist at specified paths
- **Empty output**: Review logs for specific error messages

## Configuration Options

Key settings in `workflow_config.yaml`:

- `scraper_settings`: Adjust delays and retry attempts
- `llm_settings`: Configure AI model parameters
- `reference_docs`: Specify documentation file paths
- `logging`: Control log verbosity

## Support

Check the `logs/` directory for detailed error information and debugging data.