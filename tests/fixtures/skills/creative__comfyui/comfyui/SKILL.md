---
name: comfyui
description: Generate images, video, and audio with ComfyUI — install, launch, manage
  nodes/models, run workflows with parameter injection. Uses the official comfy-cli
  for lifecycle and direct REST/WebSocket API for execution.
version: 5.0.0
author:
- kshitijk4poor
- alt-glitch
license: MIT
platforms:
- macos
- linux
- windows
compatibility: Requires ComfyUI (local, Comfy Desktop, or Comfy Cloud) and comfy-cli
  (auto-installed via pipx/uvx by the setup script).
prerequisites:
  commands:
  - python3
setup:
  help: Run scripts/hardware_check.py FIRST to decide local vs Comfy Cloud; then scripts/comfyui_setup.sh
    auto-installs locally (or use Cloud API key for platform.comfy.org).
metadata:
  hermes:
    tags:
    - comfyui
    - image-generation
    - stable-diffusion
    - flux
    - sd3
    - wan-video
    - hunyuan-video
    - creative
    - generative-ai
    - video-generation
    related_skills:
    - stable-diffusion-image-generation
    - image_gen
    category: creative
category: creative
---
# comfyui

Generate images, video, and audio with ComfyUI — install, launch, manage nodes/models, run workflows with parameter injection. Uses the official comfy-cli for lifecycle and direct REST/WebSocket API for execution.
