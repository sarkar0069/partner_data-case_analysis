# Performance Improvement Program: Submission

Files
- `analysis.ipynb`: full analysis (Part 1 + Part 2)  findings and the final recommendation
- `core.py`: shared logic (points, budget, quality score); used by notebook and app
- `app.py`: Streamlit dashboard (live levers for point rates, bonus, stress test, weights, threshold)
- `partner_data.xlsx`: input data (keep in same folder)
- `requirements.txt`

## Run locally
    pip install -r requirements.txt
    jupyter notebook analysis.ipynb      # Kernel > Restart & Run All
    streamlit run app.py

## Deploy on Streamlit Community Cloud (free, shareable link)
1. Create a GitHub repo and upload ALL files in this folder (including partner_data.xlsx).
2. Go to https://share.streamlit.io and sign in with GitHub.
3. New app > pick the repo/branch > Main file path: `app.py` > Deploy.
4. Share the `https://<name>.streamlit.app` URL. In the app's Settings > Sharing choose
   "Public" or invite specific emails if the repo is private.
5. Add the same repo link and a notebook export (File > Download as HTML) to your submission.
