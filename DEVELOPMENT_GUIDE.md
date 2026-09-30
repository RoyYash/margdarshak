# Margdarshak — Development Guide

## SIH Submission Link
https://margdarshak-hruu9qdjpsaegqjdihmsst.streamlit.app/

This URL is PERMANENT and linked to the **main** branch of:
https://github.com/RoyYash/margdarshak

## Branch Rules
- **main** = Stable branch. SIH judges use this link. ONLY merge here when tested.
- **dev**  = Active development. Do ALL new work here. Push freely.

## Daily Workflow
1. Always be on dev:  git checkout dev
2. Make changes, commit: git add . && git commit -m "feat: ..." && git push origin dev
3. Test locally: streamlit run streamlit_app.py
4. When ready to go live: git checkout main && git merge dev && git push origin main && git checkout dev

## CRITICAL RULES
- NEVER push broken code to main
- NEVER rename streamlit_app.py on main (Streamlit Cloud entry point)
- NEVER delete the main branch
- Keep requirements.txt updated whenever you add a new package

## Key Files
- streamlit_app.py      -> Entry point (Streamlit Cloud reads this)
- routepulse_streamlit.py -> Main app logic
- requirements.txt      -> Dependencies

## Streamlit Secrets (API keys)
Go to https://share.streamlit.io -> your app -> Settings -> Secrets
Add keys in TOML format, access via st.secrets["KEY_NAME"]
