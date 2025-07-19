#!/usr/bin/env python3
import os
import json
import boto3
import logging
import dotenv
import re
from fill_solutions import extract_problem_content, generate_solution, parse_solution, create_solution_notebook, clean_code_section, logger, MODEL_ID, CLAUDE_PROFILE_ARN

# Configuration
PENDING_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pending")
SOLUTIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "solutions")

# Ensure solutions directory exists
os.makedirs(SOLUTIONS_DIR, exist_ok=True)

def verify_notebook_indentation(notebook_path):
    """Verify that indentation is preserved in the generated notebook."""
    try:
        with open(notebook_path, 'r', encoding='utf-8') as f:
            notebook = json.load(f)
        
        # Check notebook structure
        cell_types = [cell['cell_type'] for cell in notebook['cells']]
        logger.info(f"Notebook cell types: {cell_types}")
        
        # Expected structure: markdown, markdown, markdown, code, markdown, markdown, code
        expected_types = ['markdown', 'markdown', 'markdown', 'code', 'markdown', 'markdown', 'code']
        if cell_types != expected_types:
            logger.warning(f"Unexpected notebook structure. Expected {expected_types}, got {cell_types}")
        
        # Check code cells for proper indentation
        for i, cell in enumerate(notebook['cells']):
            if cell['cell_type'] == 'code':
                code = ''.join(cell['source'])
                # Check for common indentation issues
                if '    ' not in code and '\t' not in code and 'def ' in code:
                    logger.warning(f"Cell {i} may have indentation issues: no indentation found in code with function definitions")
                # Check for consistent indentation
                lines = code.split('\n')
                indent_levels = {}
                for j, line in enumerate(lines):
                    if line.strip() and line.startswith(' '):
                        indent = len(line) - len(line.lstrip(' '))
                        if indent not in indent_levels:
                            indent_levels[indent] = 0
                        indent_levels[indent] += 1
                
                logger.info(f"Cell {i} indent levels: {indent_levels}")
                
        return True
    except Exception as e:
        logger.error(f"Error verifying notebook indentation: {e}")
        return False

def check_markdown_cells(notebook_path):
    """Check the markdown cells in a notebook and log their content."""
    try:
        with open(notebook_path, 'r', encoding='utf-8') as f:
            notebook = json.load(f)
        
        markdown_cells = [cell for cell in notebook['cells'] if cell['cell_type'] == 'markdown']
        logger.info(f"Found {len(markdown_cells)} markdown cells in {notebook_path}")
        
        for i, cell in enumerate(markdown_cells):
            content = ''.join(cell['source'])
            preview = content[:100] + '...' if len(content) > 100 else content
            logger.info(f"Markdown cell {i+1} preview: {preview}")
        
        return markdown_cells
    except Exception as e:
        logger.error(f"Error checking markdown cells: {e}")
        return []

def test_single_notebook(problem_name=None):
    """Test the solution generation with a single notebook."""
    try:
        # Choose a simple problem for testing
        test_notebook = problem_name or "1_Two Sum.ipynb"
        notebook_path = os.path.join(PENDING_DIR, test_notebook)
        
        logger.info(f"Testing with notebook: {test_notebook}")
        
        # Check markdown cells in the notebook
        check_markdown_cells(notebook_path)
        
        # Extract problem title and statement
        problem_title, problem_statement = extract_problem_content(notebook_path)
        if not problem_statement:
            logger.error("Could not extract problem content, exiting...")
            return
        
        logger.info("Problem title and statement extracted successfully.")
        logger.info("Generating solution (this may take a minute)...")
        
        # Generate solution
        solution_text = generate_solution(problem_statement)
        if not solution_text:
            logger.error("Failed to generate solution, exiting...")
            return
        
        logger.info("Solution generated successfully.")
        
        # Parse solution into sections
        solution_sections = parse_solution(solution_text)
        
        # Print section details for verification
        for section, content in solution_sections.items():
            logger.info(f"{section.capitalize()} section length: {len(content)} characters")
            if section in ['code', 'test_cases']:
                # Log first few lines to check indentation
                first_lines = '\n'.join(content.split('\n')[:5])
                logger.info(f"First few lines of {section}:\n{first_lines}")
        
        # Create solution notebook
        output_path = create_solution_notebook(test_notebook, problem_title, problem_statement, solution_sections)
        if output_path:
            logger.info(f"Created solution notebook: {output_path}")
            
            # Verify indentation in the generated notebook
            if verify_notebook_indentation(output_path):
                logger.info("Indentation verification passed")
            else:
                logger.warning("Indentation verification failed or had warnings")
                
            logger.info("Test completed successfully!")
        else:
            logger.error("Failed to create solution notebook")
    except Exception as e:
        logger.error(f"Error in test: {e}")
        raise

if __name__ == "__main__":
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description='Test LeetCode solution generator')
    parser.add_argument('--problem', type=str, default="1_Two Sum.ipynb", help='Problem notebook to test with')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--check-cells', action='store_true', help='Only check markdown cells without generating solution')
    args = parser.parse_args()
    
    if args.verbose:
        # Set logging level to DEBUG for more detailed output
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)
    
    # Check if the problem file exists
    problem_path = os.path.join(PENDING_DIR, args.problem)
    if not os.path.exists(problem_path):
        print(f"Error: Problem file not found: {problem_path}")
        sys.exit(1)
    
    if args.check_cells:
        # Just check the markdown cells without generating a solution
        check_markdown_cells(problem_path)
    else:
        # Run the full test
        test_single_notebook(args.problem)