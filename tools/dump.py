import os
import sys

def print_tree(start_path='.', prefix=''):
    """
    Recursively prints the directory structure starting from start_path.
    Each directory and file is printed with a prefix to indicate its level in the hierarchy.

    Parameters:
        start_path (str): The starting directory path. Defaults to the current directory.
        prefix (str): The prefix string used for indentation. Defaults to an empty string.
    """
    entries = sorted(os.listdir(start_path))
    for index, name in enumerate(entries):
        path = os.path.join(start_path, name)
        connector = "└── " if index == len(entries) - 1 else "├── "
        print(prefix + connector + name)
        if os.path.isdir(path):
            extension = "    " if index == len(entries) - 1 else "│   "
            print_tree(path, prefix + extension)

def print_all_file_contents(start_path='.'):
    """
    Recursively prints the contents of all files in the directory tree starting from start_path.
    Each file's contents are printed with a header indicating the file path.
    If a file cannot be read, an error message is printed instead.

    Parameters:
        start_path (str): The starting directory path. Defaults to the current directory.
    """
    for root, _, files in os.walk(start_path):
        for fname in files:
            file_path = os.path.join(root, fname)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    print(f"########## [{file_path}] ##########\n")
                    print(f.read())
                    print()
            except Exception as e:
                print(f"########## [{file_path}] ##########\n")
                print(f"[Error reading file: {e}]\n")

if __name__ == '__main__':
    current_dir = os.path.join(os.getcwd(), 'app')
    output_path = os.path.join('tmp', 'dump.txt')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        sys.stdout = f
        print(f"Target Directory: {current_dir}")
        print("\n##################################################")
        print("## DIRECTORY STRUCTURE                          ##")
        print("##################################################\n")
        print_tree(current_dir)
        print("\n##################################################")
        print("## FILE CONTENTS                                ##")
        print("##################################################\n")
        print_all_file_contents(current_dir)
    sys.stdout = sys.__stdout__
    print(f"Dump saved to '{output_path}'.")
