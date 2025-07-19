import nbformat
import os

def update_markdown_newlines_in_notebook(input_path, output_path=None):
    """
    Reads a Jupyter notebook, and for every markdown cell,
    replaces single '\n' with double '\n\n' to create paragraph breaks.
    """
    nb = nbformat.read(input_path, as_version=4)

    changed = False
    for cell in nb.cells:
        if cell.cell_type == 'markdown':
            old_source = cell.source
            # Replace single \n with double \n\n
            # Note: avoid tripling newlines by first splitting and then joining
            lines = old_source.split('\n')
            new_source = '\n\n'.join(lines)
            if old_source != new_source:
                cell.source = new_source
                changed = True

    if changed:
        output_file = output_path if output_path else input_path
        nbformat.write(nb, output_file)
        print(f"✅ Updated: {output_file}")
    else:
        print(f"ℹ️ No change needed: {input_path}")

def update_all_notebooks_in_folder(folder):
    print(f"📂 Processing notebooks in folder: {folder}")
    for file in os.listdir(folder):
        if file.endswith('.ipynb'):
            input_path = os.path.join(folder, file)
            update_markdown_newlines_in_notebook(input_path)

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python add_double_newlines.py <folder_path>")
    else:
        folder = sys.argv[1]
        update_all_notebooks_in_folder(folder)