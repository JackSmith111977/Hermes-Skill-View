---
name: github-deploy-upload
description: 安全地将本地部署目录通过定时 cron 推送到 GitHub 仓库。涵盖认证令牌安全存储（独立文件 600 权限）、git remote
  内容自动清理、远程分支适配等实践。
version: 1.0.0
triggers:
- deploy upload
- deploy-upload
- 定时上传
- 自动推送
- github push token
- github deploy token
- 安全推送脚本
- deploy-upload.sh
author: 小喵 (Hermes Agent)
license: MIT
metadata:
  hermes:
    tags:
    - GitHub
    - Deploy
    - Security
    - Git
    - Cron
    - Token
    related_skills:
    - github-repo-management
    - github-auth
    - hermes-ops-tips
category: github
---
# github-deploy-upload

安全地将本地部署目录通过定时 cron 推送到 GitHub 仓库。涵盖认证令牌安全存储（独立文件 600 权限）、git remote 内容自动清理、远程分支适配等实践。
