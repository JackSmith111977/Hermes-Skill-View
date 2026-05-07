---
name: gif-search
description: Search and download GIFs from Tenor using curl. No dependencies beyond
  curl...
version: 1.1.0
triggers:
- gif search
- gif-search
author: Hermes Agent
license: MIT
prerequisites:
  env_vars:
  - TENOR_API_KEY
  commands:
  - curl
  - jq
metadata:
  hermes:
    tags:
    - GIF
    - Media
    - Search
    - Tenor
    - API
category: media
---
# gif-search

Search and download GIFs from Tenor using curl. No dependencies beyond curl...
