# Meshcore CLI Container

This directory is a placeholder to help you integrate the Meshcore CLI.

Options to use https://github.com/meshcore-dev/meshcore-cli:

- Easiest: Clone the repo locally and build a static binary, then COPY it into this image.
  - Example (if it’s a Go/Rust/Node CLI): produce `meshcore-cli` binary under `meshcore/bin/meshcore-cli` and uncomment the COPY in `meshcore/Dockerfile`.
- Alternatively: Replace this Dockerfile with one that clones and builds the repo during `docker build`.

For interactive usage during development, run `meshcore-cli` locally or inside a dedicated container and connect via the configured `MESHCORE_TARGET`.
