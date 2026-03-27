FROM node:20-bookworm

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code globally
RUN npm install -g @anthropic-ai/claude-code

# PyYAML for reading prompt_snippets.yaml at runtime
RUN pip3 install --break-system-packages pyyaml

# Create non-root user (Claude Code blocks --dangerously-skip-permissions as root)
RUN useradd -m -s /bin/bash bwuser

# Ensure the work and project directories exist and are writable
RUN mkdir -p /app/project /app/bw /home/bwuser/.claude \
    && chown -R bwuser:bwuser /app /home/bwuser/.claude

USER bwuser

WORKDIR /app/project

ENTRYPOINT ["/bin/bash"]
