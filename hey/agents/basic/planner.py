import json
import logging
from hey.mcp_tools.sync_client import get_mcp_client
from hey.agents.basic.prompt import planner_prompt_dict as new_planner_prompt_dict
from hey.backend.llm.registry import get_llm
from hey.utils.misc import extract_json_from_string


class BasicPlanner():
    def __init__(self, config, environment, mcp_server_script_file=None):
        self.config = config
        self.new_prompt_dict = new_planner_prompt_dict
        self.environment = environment
        self.llm = get_llm(config.llm)
        self.task_name_history = set()
        self.print_tag = "[Planning]"
        self.mcp_server_script_file = mcp_server_script_file

    def display_plan(self, task_list):
        task_names = [task["name"] for task in task_list]
        print(f"\n{self.print_tag} I now decompose the query into "
              f"{len(task_names)} task(s): {task_names}.")

    def plan(self, query):
        logging.info(f"Starting to plan")
        log_path = self.environment.get_log_path()

        mcp_client = get_mcp_client(
            log_path=log_path,
            server_script_file=self.mcp_server_script_file
        )
        tools = mcp_client.list_tools()
        new_tools = []
        for tool in tools:  # useful for smooth benchmarking
            if self.config.disable_asking and tool["name"] == "ask_user":
                continue
            new_tools.append(tool)
        # format method cannot be used here
        system_prompt = self.new_prompt_dict['plan_system_prompt'].replace(
            '{tool_list}', json.dumps(new_tools, indent=4)
        )

        user_query = self.new_prompt_dict['plan_user_query'].format(
            query=query,
            os_name=self.environment.get_os_name(),
            working_dir=self.environment.get_working_dir(),
            files_and_folders=self.environment.list_working_dir(),
            log_path=log_path
        )
        response = self.llm.get_response(
            system_prompt=system_prompt,
            user_query=user_query,
            verbose=False,
        )
        task_list = extract_json_from_string(response)
        logging.info(f"Planning ended")
        for task in task_list:
            self.task_name_history.add(task["name"])

        self.display_plan(task_list)
        return task_list

    def display_replan(self, task_name, adjust_result):
        print(f"\n{self.print_tag} For task {task_name} to run, my replan "
              f"advice is to {adjust_result['choice']} it.")

    def replan(self, query, pending_task):
        logging.info(f"Starting to replan")
        pending_task_name = pending_task["name"]
        dependency_states = self.environment.get_task_states(pending_task['dependencies'])
        log_path = self.environment.get_log_path()

        mcp_client = get_mcp_client(
            log_path=log_path,
            server_script_file=self.mcp_server_script_file
        )
        tools = mcp_client.list_tools()
        new_tools = []
        for tool in tools:  # useful for smooth benchmarking
            if self.config.disable_asking and tool["name"] == "ask_user":
                continue
            new_tools.append(tool)
        system_prompt = self.new_prompt_dict['replan_system_prompt'].replace(
            '{tool_list}', json.dumps(new_tools, indent=4)
        )

        user_query = self.new_prompt_dict['replan_user_query'].format(
            query=query,
            os_name=self.environment.get_os_name(),
            working_dir=self.environment.get_working_dir(),
            files_and_folders=self.environment.list_working_dir(),
            current_subtask=pending_task,
            dependency_states=dependency_states,
            log_path=log_path
        )
        response = self.llm.get_response(
            system_prompt=system_prompt,
            user_query=user_query,
            verbose=False
        )
        task_list = extract_json_from_string(response)

        adjust_result = {}
        if not task_list:
            if "[Remove]" in response:
                logging.info(f"Task {pending_task_name} is deemed as redundant")
                adjust_result["choice"] = "remove"
            else:
                logging.info(f"Task {pending_task_name} is about to run as is")
                adjust_result["choice"] = "retain"
        else:
            if isinstance(task_list, dict) and len(task_list) == 1:
                task_list = [task_list]
            logging.info(f"Task {pending_task_name} needs to be amended or replaced.\n"
                         f"Before: {json.dumps(pending_task, indent=4)}\n"
                         f"After: {json.dumps(task_list, indent=4)}")
            adjust_result["choice"] = "replace"
            adjust_result["detail"] = task_list

        logging.info(f"Replanning ended")
        self.display_replan(pending_task_name, adjust_result)
        return adjust_result
