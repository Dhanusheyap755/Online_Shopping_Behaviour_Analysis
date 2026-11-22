"""
Direct cell executor for EDA_Analysis.ipynb.
Executes each code cell in a clean shared execution namespace,
captures stdout, return values, and matplotlib figures (as base64 PNG display_data),
and saves the executed notebook with real embedded outputs and charts.
"""

import os
import sys
import io
import base64
import nbformat
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def execute_notebook_directly():
    base_dir = r"C:\Users\abidh\.gemini\antigravity\scratch\Online_Shopping_Behaviour_Analysis"
    notebook_dir = os.path.join(base_dir, "notebooks")
    nb_path = os.path.join(notebook_dir, "EDA_Analysis.ipynb")

    print(f"Loading notebook: {nb_path}")
    with open(nb_path, "r", encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)

    # Prepare execution context
    exec_globals = {
        "__name__": "__main__",
        "__file__": nb_path,
    }

    # Add display function to mimic IPython
    def mock_display(*args):
        for arg in args:
            if hasattr(arg, "to_string"):
                print(arg.to_string())
            else:
                print(str(arg))

    exec_globals["display"] = mock_display

    code_cells = [cell for cell in nb.cells if cell.cell_type == "code"]
    print(f"Total code cells to execute: {len(code_cells)}")

    os.chdir(notebook_dir)

    for idx, cell in enumerate(code_cells, 1):
        cell_source = cell.source
        print(f"Executing code cell {idx}/{len(code_cells)}...")

        # Reset stdout capture
        old_stdout = sys.stdout
        redirected_output = io.StringIO()
        sys.stdout = redirected_output

        # Clear any existing plots
        plt.close('all')

        cell_outputs = []
        try:
            exec(cell_source, exec_globals)
            out_str = redirected_output.getvalue()

            if out_str:
                cell_outputs.append(nbformat.v4.new_output(
                    output_type="stream",
                    name="stdout",
                    text=out_str
                ))

            # Check if any matplotlib figures were generated
            for fig_num in plt.get_fignums():
                fig = plt.figure(fig_num)
                buf = io.BytesIO()
                fig.savefig(buf, format='png', bbox_inches='tight', dpi=120)
                buf.seek(0)
                img_b64 = base64.b64encode(buf.read()).decode('utf-8')
                cell_outputs.append(nbformat.v4.new_output(
                    output_type="display_data",
                    data={"image/png": img_b64, "text/plain": "<Figure size ...>"},
                    metadata={}
                ))
            plt.close('all')

        except Exception as e:
            sys.stdout = old_stdout
            print(f"ERROR in cell {idx}: {e}")
            raise e
        finally:
            sys.stdout = old_stdout

        cell.outputs = cell_outputs
        cell.execution_count = idx

    print("All code cells executed successfully!")
    print(f"Saving executed notebook to {nb_path}...")
    with open(nb_path, "w", encoding="utf-8") as f:
        nbformat.write(nb, f)
    print("Notebook successfully saved with outputs and images embedded!")

if __name__ == "__main__":
    execute_notebook_directly()
