import nbformat
import os

def validate_notebooks_in_folder(folder_path):
    print(f"Checking notebooks in folder: {folder_path}")
    failed_files = []

    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".ipynb"):
                file_path = os.path.join(root, file)
                try:
                    nb = nbformat.read(file_path, as_version=4)
                    num_cells = len(nb.cells)
                    if num_cells == 1:
                        print(f"[✅ OK] {file_path} has exactly 1 cell.")
                    else:
                        print(f"[❌ FAIL] {file_path} has {num_cells} cells.")
                        failed_files.append((file_path, num_cells))
                except Exception as e:
                    print(f"[⚠️ ERROR] Failed to read {file_path}: {e}")
                    failed_files.append((file_path, 'error'))

    print("\nSummary:")
    if not failed_files:
        print("✅ All notebooks have exactly 1 cell.")
    else:
        print(f"❌ {len(failed_files)} notebook(s) failed:")
        for path, count in failed_files:
            print(f"   - {path} (cells: {count})")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python validate_single_cell.py <folder_path>")
    else:
        folder = sys.argv[1]
        validate_notebooks_in_folder(folder)