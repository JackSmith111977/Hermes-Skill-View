---
name: feishu-send-file
description: 飞书发送文件的正确流程和最佳实践。通过飞书原生 API（上传→获 file_key→发送 file 消息）实现文件发送。解释为什么 send_mess...
version: 1.0.0
triggers:
- 发送文件到飞书
- 飞书上传文件
- 飞书发送 PDF
- 飞书发送图片
- feishu file upload
- 飞书 API 文件
aliases:
- /feishu-send-file
allowed-tools:
- terminal
- read_file
- write_file
metadata:
  hermes:
    tags:
    - feishu
    - file
    - upload
    - send
    - api
    category: feishu
    skill_type: library-reference
    design_pattern: tool-wrapper
    related_skills:
    - feishu
category: feishu
---
# feishu-send-file

飞书发送文件的正确流程和最佳实践。通过飞书原生 API（上传→获 file_key→发送 file 消息）实现文件发送。解释为什么 send_mess...
