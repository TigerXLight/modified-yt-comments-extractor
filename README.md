
## 4. Replace your “Security Notes” section with this

```markdown
## Security Notes Before Sharing or Uploading

If you installed `keyring` and the app shows **Secure** under the API key box, your API key is normally stored in your operating system’s credential manager rather than inside `settings.json`.

If `settings.json` does not contain your API key, and your key is not hardcoded into any `.py` file, you usually do not need to worry about the key being uploaded.

However, before uploading or sharing a copy of the project, it is still best to work from a copied clean folder.

Do not edit or upload your original working folder directly. Make a copied folder first, then remove or ignore files that should not be uploaded.

Do not include:

```text
venv/
settings.json
.env
dist/
build/
__pycache__/
exported CSV, TXT, or Excel files
your personal API key