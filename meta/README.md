# LeetCode Solution Generator

This tool uses Amazon Bedrock with Claude Sonnet 3.7 to automatically generate solutions for LeetCode problems.

## How It Works

1. The script reads Jupyter notebooks from the `pending` folder
2. It extracts the problem statement from each notebook
3. It uses Claude Sonnet 3.7 to generate a comprehensive solution
4. It creates a new Jupyter notebook in the `solutions` folder with:
   - The original problem statement
   - A detailed explanation of the solution approach
   - Efficient Python implementation
   - Time and space complexity analysis
   - Test cases to verify the solution

## Prerequisites

- Python 3.6+
- AWS account with access to Amazon Bedrock
- Configured AWS credentials with permissions to use Bedrock
- Required Python packages: `boto3`, `json`

## Setup

1. Ensure you have AWS CLI configured with appropriate credentials
2. Install required packages:
   ```
   pip install boto3 python-dotenv
   ```
3. Set up your environment variables:
   ```
   cp .env.example .env
   ```
   Then edit the `.env` file with your specific configuration values if needed.

## Usage

Run the main script to process all pending notebooks:

```bash
python fill_solutions.py
```

Process a specific problem:

```bash
python fill_solutions.py --problem "1_Two Sum"
```

Limit the number of problems to process:

```bash
python fill_solutions.py --limit 5
```

Run in test mode with a single problem:

```bash
python fill_solutions.py --test
```

## Configuration

The script uses the following configuration:
- Configuration values are loaded from the `.env` file
- Input notebooks are read from the `pending` folder
- Output notebooks are saved to the `solutions` folder
- Logs are written to `solution_generator.log`

You can customize the following in your `.env` file:
- `MODEL_ID`: The Bedrock model ID to use
- `CLAUDE_PROFILE_ARN`: The ARN of your Claude profile
- `AWS_REGION`: The AWS region to use for Bedrock

## Notes

- The script skips notebooks that already have corresponding solutions
- It includes a small delay between API calls to avoid rate limiting
- The solution parsing logic attempts to identify different sections of Claude's response