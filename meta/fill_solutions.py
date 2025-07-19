#!/usr/bin/env python3
import os
import json
import boto3
import time
import logging
import dotenv
import re
from pathlib import Path
from botocore.exceptions import ClientError

# Load environment variables from .env file
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
dotenv.load_dotenv(env_path)

# Configuration
PENDING_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pending")
SOLUTIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "solutions")
MODEL_ID = os.getenv("MODEL_ID")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "solution_generator.log")

# Validate environment variables
def validate_env_vars():
    """Validate that required environment variables are set."""
    missing_vars = []
    if not MODEL_ID:
        missing_vars.append("MODEL_ID")
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}. Please check your .env file.")

# Validate environment variables
validate_env_vars()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('solution_generator')

# Ensure solutions directory exists
os.makedirs(SOLUTIONS_DIR, exist_ok=True)

# Initialize Bedrock client
try:
    bedrock_runtime = boto3.client('bedrock-runtime', region_name=AWS_REGION)
    logger.info(f"Successfully initialized Bedrock client in region {AWS_REGION}")
except Exception as e:
    logger.error(f"Failed to initialize Bedrock client: {e}")
    raise

def extract_problem_content(notebook_path):
    """Extract both title and problem statement from a Jupyter notebook."""
    try:
        with open(notebook_path, 'r', encoding='utf-8') as f:
            notebook = json.load(f)
        
        # Find markdown cells
        markdown_cells = [cell for cell in notebook['cells'] if cell['cell_type'] == 'markdown']
        
        if len(markdown_cells) >= 2:
            # First cell is title, second is problem statement
            title = ''.join(markdown_cells[0]['source'])
            problem_statement = ''.join(markdown_cells[1]['source'])
            return title, problem_statement
        elif len(markdown_cells) == 1:
            # Only one markdown cell, use it as both title and statement
            content = ''.join(markdown_cells[0]['source'])
            logger.warning(f"Only one markdown cell found in {notebook_path}, using it for both title and statement")
            return content, content
        else:
            logger.warning(f"No markdown cell found in {notebook_path}")
            return None, None
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in notebook: {notebook_path}")
        return None, None
    except Exception as e:
        logger.error(f"Error extracting problem content from {notebook_path}: {e}")
        return None, None

def generate_solution(problem_statement):
    """Generate solution using Claude Sonnet 3.7."""
    prompt = f"""
You are an expert algorithm and data structures problem solver. Given the following LeetCode problem, I need you to provide a complete solution with specific sections. Each section should be clearly marked with a header like "## Section Name" so I can parse them correctly.

Problem:
{problem_statement}

Please provide your response in exactly this format with these section headers:

## Solution Explanation
[Your detailed explanation of the approach and algorithm]

## Code
[Your efficient Python implementation here]

## Time and Space Complexity
[Your detailed time and space complexity analysis here]

## Test Cases
[Your test cases with comments here. Make sure the test cases are code tests and not just examples]

Make sure your Python code is complete, correct, and follows best practices.
Include multiple test cases that cover edge cases.
Do not include any other sections or text outside these four sections.
"""

    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Generating solution, attempt {attempt + 1}/{max_retries}")
            response = bedrock_runtime.invoke_model(
                modelId=MODEL_ID,
                contentType='application/json',
                accept='application/json',
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 4096,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.1,
                    "top_p": 0.9,
                })
            )
            
            response_body = json.loads(response['body'].read().decode('utf-8'))
            logger.info("Solution generated successfully")
            return response_body['content'][0]['text']
        except ClientError as e:
            if e.response['Error']['Code'] == 'ThrottlingException':
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Rate limited. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error("Max retries reached for rate limiting")
                    return None
            else:
                logger.error(f"AWS error generating solution: {e}")
                return None
        except Exception as e:
            logger.error(f"Error generating solution: {e}")
            return None

def parse_solution(solution_text):
    """Parse the solution text into sections."""
    sections = {
        "explanation": "",
        "code": "",
        "complexity": "",
        "test_cases": ""
    }
    
    try:
        # Look for section headers using regex
        explanation_match = re.search(r'(?:##\s*Solution\s*Explanation|##\s*Detailed\s*Explanation)\s*\n([\s\S]*?)(?:##\s*|$)', solution_text)
        code_match = re.search(r'##\s*Code\s*\n([\s\S]*?)(?:##\s*|$)', solution_text)
        complexity_match = re.search(r'(?:##\s*Time\s*and\s*Space\s*Complexity|##\s*Complexity)\s*\n([\s\S]*?)(?:##\s*|$)', solution_text)
        test_cases_match = re.search(r'##\s*Test\s*Cases\s*\n([\s\S]*?)(?:##\s*|$)', solution_text)
        
        # Extract content from matches
        if explanation_match:
            sections['explanation'] = explanation_match.group(1).strip()
        if code_match:
            sections['code'] = clean_code_section(code_match.group(1))
        if complexity_match:
            sections['complexity'] = complexity_match.group(1).strip()
        if test_cases_match:
            sections['test_cases'] = clean_code_section(test_cases_match.group(1))
        
        # If no matches found, try alternative approach with splitting
        if not any(sections.values()):
            # Split by markdown headers
            parts = re.split(r'##\s+', solution_text)
            for part in parts[1:]:  # Skip the first part (before any headers)
                lines = part.strip().split('\n', 1)
                if len(lines) < 2:
                    continue
                    
                header = lines[0].lower().strip()
                content = lines[1].strip() if len(lines) > 1 else ""
                
                if 'code' in header:
                    sections['code'] = clean_code_section(content)
                elif 'complexity' in header or ('time' in header and 'space' in header):
                    sections['complexity'] = content
                elif 'explanation' in header or 'solution' in header:
                    sections['explanation'] = content
                elif 'test' in header and 'case' in header:
                    sections['test_cases'] = clean_code_section(content)
        
        # Extract code blocks if they exist
        if not sections['code'] or not sections['test_cases']:
            code_blocks = re.findall(r'```(?:python)?\n([\s\S]*?)```', solution_text)
            if code_blocks:
                # First code block is likely the solution
                if not sections['code'] and len(code_blocks) > 0:
                    sections['code'] = clean_code_section(code_blocks[0])
                # Second code block is likely test cases
                if not sections['test_cases'] and len(code_blocks) > 1:
                    sections['test_cases'] = clean_code_section(code_blocks[1])
        
        # If test cases section is empty but there are assertions in the code
        if not sections['test_cases'] and 'assert' in sections['code']:
            code_lines = sections['code'].split('\n')
            test_lines = []
            main_code_lines = []
            
            # Try to separate test cases from main code
            in_test_section = False
            for line in code_lines:
                if ('test' in line.lower() or 'assert' in line or 
                    'example' in line.lower() or 'print(' in line):
                    in_test_section = True
                    test_lines.append(line)
                elif in_test_section and line.strip() and not line.startswith('def '):
                    test_lines.append(line)
                else:
                    if not in_test_section or not line.strip():
                        main_code_lines.append(line)
                    in_test_section = False
            
            if test_lines:
                sections['test_cases'] = '\n'.join(test_lines)
                sections['code'] = '\n'.join(main_code_lines)
        
        # Generate default content for empty sections
        if not sections['code'].strip():
            sections['code'] = '# Solution code will be added here\n'
        if not sections['complexity'].strip():
            sections['complexity'] = 'Time and space complexity analysis will be added here.'
        if not sections['explanation'].strip():
            sections['explanation'] = 'Solution explanation will be added here.'
        if not sections['test_cases'].strip():
            sections['test_cases'] = '# Test cases will be added here\n'
        
        logger.info("Successfully parsed solution into sections")
        return sections
    except Exception as e:
        logger.error(f"Error parsing solution: {e}")
        # Return default sections if parsing fails
        return {
            "code": "# Solution code will be added here\n",
            "complexity": "Time and space complexity analysis will be added here.",
            "explanation": "Solution explanation will be added here.",
            "test_cases": "# Test cases will be added here\n"
        }

def clean_code_section(code_text):
    """Clean up code sections by removing markdown code blocks and preserving indentation."""
    if not code_text:
        return "# Code will be added here\n"
    
    # Remove markdown code block markers
    code = code_text.replace('```python', '').replace('```', '').strip()
    
    # Fix common formatting issues
    lines = code.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Remove line numbers that might be present
        line = re.sub(r'^\s*\d+[:.)]\s*', '', line)
        cleaned_lines.append(line)
    
    code = '\n'.join(cleaned_lines)
    
    # Ensure there's a newline at the end
    if not code.endswith('\n'):
        code += '\n'
    
    return code

def create_solution_notebook(problem_name, problem_title, problem_statement, solution_sections):
    """Create a new Jupyter notebook with the solution."""
    try:
        # Format markdown content for better display
        def format_markdown(text):
            # Ensure headers have proper spacing
            text = re.sub(r'(#+)(\w)', r'\1 \2', text)
            # Fix bullet points
            text = re.sub(r'^\s*[*-]\s*', '* ', text, flags=re.MULTILINE)
            return text
        
        # Format the sections
        explanation = format_markdown(solution_sections["explanation"])
        complexity = format_markdown(solution_sections["complexity"])
        
        # Create cells for the notebook
        cells = [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": problem_title.split('\n')
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": problem_statement.split('\n')
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": ["## Solution Explanation\n"] + explanation.split('\n')
            },
            {
                "cell_type": "code",
                "metadata": {},
                "source": solution_sections["code"].split('\n'),
                "execution_count": None,
                "outputs": []
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": ["## Time and Space Complexity\n"] + complexity.split('\n')
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": ["## Test Cases\n"]
            },
            {
                "cell_type": "code",
                "metadata": {},
                "source": solution_sections["test_cases"].split('\n'),
                "execution_count": None,
                "outputs": []
            }
        ]
        
        # Create notebook structure
        notebook = {
            "cells": cells,
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3"
                },
                "language_info": {
                    "codemirror_mode": {
                        "name": "ipython",
                        "version": 3
                    },
                    "file_extension": ".py",
                    "mimetype": "text/x-python",
                    "name": "python",
                    "nbconvert_exporter": "python",
                    "pygments_lexer": "ipython3",
                    "version": "3.11.9"
                }
            },
            "nbformat": 4,
            "nbformat_minor": 5
        }
        
        # Write notebook to file
        output_path = os.path.join(SOLUTIONS_DIR, f"{problem_name}")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(notebook, f, indent=2)
        
        logger.info(f"Created solution notebook: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Error creating solution notebook for {problem_name}: {e}")
        return None

def main(limit=None):
    """Main function to process all pending notebooks."""
    try:
        # Get list of pending notebooks
        pending_notebooks = [f for f in os.listdir(PENDING_DIR) if f.endswith('.ipynb')]
        
        # Apply limit if specified
        if limit and limit > 0 and limit < len(pending_notebooks):
            pending_notebooks = pending_notebooks[:limit]
            logger.info(f"Processing limited set of {limit} notebooks out of {len(pending_notebooks)} total")
        else:
            logger.info(f"Found {len(pending_notebooks)} pending notebooks")
        
        # Process each notebook
        success_count = 0
        skip_count = 0
        error_count = 0
        
        for i, notebook_file in enumerate(pending_notebooks):
            problem_name = notebook_file
            notebook_path = os.path.join(PENDING_DIR, notebook_file)
            solution_path = os.path.join(SOLUTIONS_DIR, problem_name)
            
            logger.info(f"Processing {i+1}/{len(pending_notebooks)}: {problem_name}")
            
            # Skip if solution already exists
            if os.path.exists(solution_path):
                logger.info(f"Solution already exists for {problem_name}, skipping...")
                skip_count += 1
                continue
            
            try:
                # Extract problem title and statement
                problem_title, problem_statement = extract_problem_content(notebook_path)
                if not problem_statement:
                    logger.warning(f"Could not extract problem content from {problem_name}, skipping...")
                    error_count += 1
                    continue
                
                # Generate solution
                logger.info(f"Generating solution for {problem_name}...")
                solution_text = generate_solution(problem_statement)
                if not solution_text:
                    logger.warning(f"Failed to generate solution for {problem_name}, skipping...")
                    error_count += 1
                    continue
                
                # Parse solution into sections
                solution_sections = parse_solution(solution_text)
                
                # Create solution notebook
                output_path = create_solution_notebook(problem_name, problem_title, problem_statement, solution_sections)
                if output_path:
                    success_count += 1
                    logger.info(f"Successfully processed {problem_name}")
                else:
                    error_count += 1
                
                # Add a delay to avoid rate limiting
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error processing {problem_name}: {e}")
                error_count += 1
        
        # Log summary
        logger.info(f"Processing complete. Success: {success_count}, Skipped: {skip_count}, Errors: {error_count}")
        
    except Exception as e:
        logger.error(f"Error in main function: {e}")
        raise

def process_single_notebook(notebook_file):
    """Process a single notebook."""
    notebook_path = os.path.join(PENDING_DIR, notebook_file)
    solution_path = os.path.join(SOLUTIONS_DIR, notebook_file)
    
    logger.info(f"Processing single notebook: {notebook_file}")
    
    # Skip if solution already exists
    if os.path.exists(solution_path):
        logger.info(f"Solution already exists for {notebook_file}, skipping...")
        return False
    
    # Extract problem title and statement
    problem_title, problem_statement = extract_problem_content(notebook_path)
    if not problem_statement:
        logger.warning(f"Could not extract problem content from {notebook_file}")
        return False
    
    # Generate solution
    logger.info(f"Generating solution for {notebook_file}...")
    solution_text = generate_solution(problem_statement)
    if not solution_text:
        logger.warning(f"Failed to generate solution for {notebook_file}")
        return False
    
    # Parse solution into sections
    solution_sections = parse_solution(solution_text)
    
    # Create solution notebook
    output_path = create_solution_notebook(notebook_file, problem_title, problem_statement, solution_sections)
    if output_path:
        logger.info(f"Successfully processed {notebook_file}")
        return True
    else:
        return False

if __name__ == "__main__":
    import argparse
    import sys
    
    # Check if .env file exists
    if not os.path.exists(env_path):
        print(f"Error: .env file not found at {env_path}")
        print("Please create a .env file by copying .env.example and filling in your values.")
        sys.exit(1)
    
    parser = argparse.ArgumentParser(description='Generate LeetCode solutions using Claude Sonnet 3.7')
    parser.add_argument('--problem', type=str, help='Process a specific problem notebook')
    parser.add_argument('--limit', type=int, help='Limit the number of problems to process')
    parser.add_argument('--test', action='store_true', help='Run in test mode with a single problem')
    args = parser.parse_args()
    
    try:
        if args.test:
            from test_solution_generator import test_single_notebook
            test_single_notebook()
        elif args.problem:
            if not args.problem.endswith('.ipynb'):
                args.problem += '.ipynb'
            process_single_notebook(args.problem)
        else:
            main(limit=args.limit)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)