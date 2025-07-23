#!/bin/bash
ollama rm deepseek-r1:1.5b
brew uninstall ollama
ps aux | grep ollama | grep serve | awk '{print $2}' | xargs kill -9