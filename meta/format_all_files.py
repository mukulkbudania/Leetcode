import nbformat
import os
import re

def format_single_notebook(input_path, output_path=None):
    # Extract title from file name
    file_name = os.path.basename(input_path)
    base_name = os.path.splitext(file_name)[0]
    if '_' in base_name:
        num, title_part = base_name.split('_', 1)
        title_text = f"# {num}. {title_part.replace('_', ' ')}"
    else:
        title_text = f"# {base_name.replace('_', ' ')}"

    nb = nbformat.read(input_path, as_version=4)

    new_cells = []

    # Add title cell at the top
    new_cells.append(nbformat.v4.new_markdown_cell(title_text))

    for cell in nb.cells:
        if cell.cell_type == 'markdown':
            lines = cell.source.split('\n')
            new_lines = []
            for line in lines:
                # Bold Example lines
                line = re.sub(r'^(\s*)(Example\s*\d*:)', r'\1**\2**', line)
                line = re.sub(r'^(\s*)(Example:)', r'\1**\2**', line)
                # Bold Constraints lines
                line = re.sub(r'^(\s*)(Constraints:)', r'\1**\2**', line)
                new_lines.append(line)
            cell.source = '\n'.join(new_lines)
        new_cells.append(cell)

    nb.cells = new_cells

    # Save updated notebook
    output_file = output_path if output_path else input_path
    nbformat.write(nb, output_file)
    print(f"✅ Formatted: {output_file}")

def format_all_notebooks_in_folder(folder):
    print(f"📂 Processing all notebooks in folder: {folder}")
    for file in os.listdir(folder):
        if file.endswith('.ipynb'):
            input_path = os.path.join(folder, file)
            # You can also create an output file if you prefer
            # output_path = os.path.join(folder, "formatted_" + file)
            format_single_notebook(input_path)

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python format_all_notebooks.py <folder_path>")
    else:
        folder = sys.argv[1]
        format_all_notebooks_in_folder(folder)