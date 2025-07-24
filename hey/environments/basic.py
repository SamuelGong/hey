import logging
import os
import platform
from hey.backend.ipc.redis import RedisIPC
from hey.environments.base import BaseEnv


def _get_os_name():
    system = platform.system()

    if system == "Darwin":
        return 'macOS ' + platform.mac_ver()[0]
    elif system == "Linux":
        try:
            with open("/etc/os-release") as f:
                lines = f.readlines()
                for line in lines:
                    if line.startswith("PRETTY_NAME"):
                        return line.split("=")[1].strip().strip('"')
        except FileNotFoundError:
            pass

        return platform.version()
    else:
        return "Unknown Operating System"


class BasicEnv(BaseEnv, RedisIPC):
    def __init__(self):
        RedisIPC.__init__(self, root="hey")

    def get_message_subscriber(self, channels):
        return self.subscribe_channels(channels)

    def publish_a_message(self, channel, message):
        self.publish_a_value(
            channel=channel,
            value=message
        )

    def set_data_for_subprocess(self, data, target_pid):
        self.set_a_shared_value(
            key=[f"{target_pid}", "data_from_main_process"],
            value=data
        )

    def get_data_from_main_process(self, target_pid, blocked=False):
        data = self.get_a_shared_value(
            key=[f"{target_pid}", "data_from_main_process"],
            busy_waiting=blocked
        )
        self.delete_a_shared_value(
            key=[f"{target_pid}",
                 "data_from_main_process"]
        )
        return data


class AgentEnv(BasicEnv):
    COMPLETED_TASK_STATES = "completed_task_states"
    TRUNCATED_TEXT_LENGTH = 2000

    def __init__(self, config):
        BasicEnv.__init__(self)
        self.delete_all_keys()
        self.set_a_shared_value(
            key=self.COMPLETED_TASK_STATES,
            value={}
        )

        self.os_name = _get_os_name()
        logging.info(f"Recognized OS name: {self.os_name}")
        self.working_dir = config.working_dir
        self.log_path = config.log_path
        self.config = config

    def get_os_name(self):
        return self.os_name

    def get_working_dir(self):
        return self.working_dir

    def get_log_path(self):
        return self.log_path

    def list_working_dir(self):
        working_dir = self.config.working_dir
        if not os.path.exists(working_dir):
            return f'No such directory: {working_dir}'

        files_and_dirs = os.listdir(working_dir)
        return "\n".join(files_and_dirs)

    def update_task_state(self, task_name, task_state):
        all_task_states = self.get_a_shared_value(key=self.COMPLETED_TASK_STATES)

        state = {
            task_name: task_state
        }
        all_task_states.update(state)
        self.set_a_shared_value(
            key=self.COMPLETED_TASK_STATES,
            value=all_task_states
        )

    def set_task_result(self, task, result):
        state = {
            task["name"]: task
        }
        state[task["name"]].update({
            "result": result
        })

        all_task_states = self.get_a_shared_value(key=self.COMPLETED_TASK_STATES)
        if all_task_states is None:
            all_task_states = {}

        all_task_states.update(state)
        self.set_a_shared_value(
            key=self.COMPLETED_TASK_STATES,
            value=all_task_states
        )

    def get_task_state(self, task_name):
        all_task_states = self.get_a_shared_value(key=self.COMPLETED_TASK_STATES)
        return all_task_states.get(task_name, None)

    def get_task_states(self, task_names, clean_retrieval=False):
        task_states = []
        for task_name in task_names:
            task_state = self.get_task_state(task_name)
            if clean_retrieval:
                if task_state["tool"] == "do_googlesearch" and "result" in task_state:
                    del task_state["result"]  # avoid overwhelming text
            task_states.append({task_name: task_state})
        return task_states
