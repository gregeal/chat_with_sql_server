to use conda in terminal
1. conda --version to know the version and if conda is available
2.  conda create --name chat-with-sql python=3.12 to create live a venv
3. conda activate chat-with-sql to run notebook local

to use uv in terminal, use the below command to activate jupyter nb for example
    uv venv  # If you haven't created a venv yet
    source .venv/bin/activate  # Or .venv\Scripts\activate on Windows
    uv pip install ipykernel

Ensure jupyter or ipython is accessible.
    uv pip install jupyter
    # Or if you prefer ipython
    uv pip install ipython

To install libraries 
uv pip install -r requirements.txt

To run the file
    uv run jupyter notebook main.ipynb

Note
Use Control-C to stop this server and shut down all kernels (twice to skip confirmation).

to use uv in the terminal instead of pip, use command like
uv run --with pandas jupyter notebook main.py