"""Streamlit entry point for the MARGDARSHAK dashboard.

Uses runpy.run_path() to re-execute routepulse_streamlit.py on EVERY Streamlit rerun.
'from routepulse_streamlit import *' would only execute the module once (Python's module
cache), causing a blank page on every rerun after the first load.
"""

import runpy

runpy.run_path("routepulse_streamlit.py", run_name="__main__")
