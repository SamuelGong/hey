from hey.environments.basic import AgentEnv

registered_environments = {
    'basic': AgentEnv
}


def get_environment(config):
    return registered_environments[config.environment.type](config)
