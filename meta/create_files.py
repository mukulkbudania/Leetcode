import os
import json

# Path to your file
file_path = "18_07_2025_Last3Months.csv"

# Read lines from file
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for line in lines:
    parts = line.strip().split(',')
    if len(parts) >= 2:
        problem_id = parts[0].strip()
        title = parts[1].strip()
        
        # Replace spaces with underscore only in problem id part
        # Keep title as it is (with spaces)
        filename = f"{problem_id}_{title}.ipynb"
        
        # Optional: remove problematic characters from filename
        filename = filename.replace('/', ' ').replace('\\', ' ')
        
        # Create minimal empty notebook content
        notebook_content = {
            "cells": [],
            "metadata": {},
            "nbformat": 4,
            "nbformat_minor": 5
        }
        
        # Write to .ipynb file
        with open(filename, 'w', encoding='utf-8') as nb_file:
            json.dump(notebook_content, nb_file, ensure_ascii=False, indent=2)

        print(f"Created {filename}")