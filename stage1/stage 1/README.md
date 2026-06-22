# Motion Planning Sprint

## Setup

### Prerequisites

* Make sure **Python 3.11** is installed on your machine.
* Open the project in **PyCharm**.

### Configure the Python Interpreter

1. Click **No Interpreter** in the bottom-right corner of PyCharm.
2. Select **Add New Interpreter → Add Local Interpreter**.
3. Choose the appropriate Python version and click **OK**.

### Install Dependencies

1. Open the **Terminal** panel in the bottom-left corner.

2. Verify that the command prompt starts with `(venv)`.

   * If it does not, close the current terminal tab and open a new one.

3. Run:

   ```bash
   pip install -r requirements.txt
   ```

4. Wait for all packages to install successfully.

### Run the Application

1. Run `app.py` in algorithmics.
2. Wait until the following message appears in the console:

   ```text
   Dash is running on http://0.0.0.0:7324/
   ```
   
3. to access the app, open http://localhost:7324 on your browser.

## Instructions

* Exercise formalization appears in the file `Motion Planning Sprint.docx`
* Within this file you'll find:
  * Background story and problem explanation
  * Formalization of technical details about the task - how a path looks, what threats are there, etc.
  * Explanations over the existing code resources and how to use them.
* We recommend you to read the task and pre-plan your initial workflow.
* Make sure you use the graph visualization functionality we provided for you.
