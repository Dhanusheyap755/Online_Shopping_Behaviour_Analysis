"""
Executes EDA_Analysis.ipynb via nbclient, verifying zero errors across all 27 sections
and embedding all outputs, plots, and data tables directly into the notebook.
"""

import os
import nbformat
from nbclient import NotebookClient

def run_notebook():
    base_dir = r"C:\Users\abidh\.gemini\antigravity\scratch\Online_Shopping_Behaviour_Analysis"
    notebook_dir = os.path.join(base_dir, "notebooks")
    nb_path = os.path.join(notebook_dir, "EDA_Analysis.ipynb")

    print(f"Reading notebook from: {nb_path}")
    with open(nb_path, "r", encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)

    client = NotebookClient(nb, timeout=600, kernel_name="python3", resources={"metadata": {"path": notebook_dir}})
    
    print("Executing notebook cells...")
    client.execute()

    print(f"Execution complete! Writing executed notebook to: {nb_path}")
    with open(nb_path, "w", encoding="utf-8") as f:
        nbformat.write(nb, f)

    print("Success: All notebook cells executed with 0 errors!")

if __name__ == "__main__":
    run_notebook()
