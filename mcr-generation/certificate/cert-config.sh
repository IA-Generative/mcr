# The --with isn't necessary because certifi is a sub dependency of the project. This flag makes it explicit
CERTIFY_PATH=$(uv run --with certifi python -c "import certifi; print(certifi.where())")
cat ./certificate/cert-ollama.pem >> $CERTIFY_PATH
