import sys
from hey.utils.misc import setup
from hey.agents.registry import get_agent
from hey.environments.registry import get_environment


def main():
    if len(sys.argv) < 2:
        print("Usage: hey '<your query>'")
        sys.exit(1)

    query = " ".join(sys.argv[1:])  # Combine all arguments into a single string
    # query = "Search the web to tell me who Zhifeng Jiang is?"
    config = setup()
    environment = get_environment(config)
    agent = get_agent(config.agent, environment)
    agent.serve(query)


if __name__ == '__main__':
    main()
