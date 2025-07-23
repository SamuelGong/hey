References and Acknowledgments
The tools provided in the current folder are adapted from a specific branch of the GitHub repository for Owl, a concurrent general-purpose AI agent:

https://github.com/camel-ai/owl/tree/gaia58.18/owl/camel

We extend our sincere thanks to the authors for their inspiration and commitment to open-source development.

---

# Getting Started

To begin using these tools:

1. Install the required dependencies:

```bash
# at the current folder
pip install -r requirements.txt
```

2. In your project folder, update the `config.yml` file to include the following:

```yaml
agent:
    ...
    server_script_path: owl_server.py
    ...
```