@echo off
start python screen_capture_node.py
timeout /t 2
start python remote_viewer_node.py 