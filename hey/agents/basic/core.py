import os
import time
import json
import copy
import pickle
import dotenv
import logging
import threading
import traceback
import subprocess
from multiprocessing import Pool
import multiprocessing as mp

from hey.utils.misc import set_log
from hey.agents.base import BaseAgent
from hey.agents.basic.critic import BasicCritic
from hey.agents.basic.planner import BasicPlanner
from hey.agents.basic.const import END, INPUT_REQUIRED
from hey.mcp_tools.sync_client import get_mcp_client

dir_path = os.path.dirname(os.path.realpath(__file__))


class BasicAgent(BaseAgent):
    INPUT_TIMEOUT = 120

    def __init__(self, config, environment):
        self.environment = environment
        self.planner = BasicPlanner(
            config.planner,
            environment,
            config.mcp_server_script_file
        )
        self.critic = BasicCritic(config.critic, environment)
        self.config = config

        self.all_tasks = {}
        self.completed_task_names = []
        self.running_task_names = []
        self.pending_task_names = []

    def preprocessing_display(self, task):
        print_tag = "[Execution]"
        print(f"\n{print_tag} I now run task {task['name']} with tool {task['tool']}.\n"
              f"\tDetail: {task['description'][:500]}...")

    def evaluation_display(self, task, task_succeeded, evaluator_comment):
        print_tag = "[Evaluation]"
        if evaluator_comment:
            print(f"\n{print_tag} According to my evaluation, task {task['name']} "
                  f"{'succeeded' if task_succeeded else 'failed'} with score {evaluator_comment['score']}/10.\n"
                  f"\tDetail: {evaluator_comment['explanation'][:500]}...")
        else:
            print(f"\n{print_tag} According to my evaluation, task {task['name']} "
                  f"{'succeeded' if task_succeeded else 'failed'}.")

    def process_a_task(self, overall_task, task):  # this run in a new process
        task_name = task['name']
        task_tool = task['tool']
        dotenv.load_dotenv(dotenv_path='.env', override=True)
        log_path = self.environment.get_log_path()
        set_log(log_path=log_path)

        logging.info(f'Starting to process task {task_name} with tool {task_tool}')
        begin_time = time.perf_counter()

        retry_count = 0
        max_retries = self.config.task_retry_time_limit
        mcp_client = get_mcp_client(
            log_path=log_path,
            server_script_file=self.config.mcp_server_script_file
        )
        while retry_count <= max_retries:
            try:
                arguments = task['arguments']
                if "log_path" in arguments:  # to mitigate LLM's hallucination
                    arguments["log_path"] = self.environment.get_log_path()

                self.preprocessing_display(task)
                result = mcp_client.call_tool(
                    tool_name=task_tool,
                    tool_args=arguments
                )

                res_list = []
                for con in result.content:
                    res_list.append(con.text)
                result = "\n".join(res_list)

                logging.info(f'Task {task_name} with tool {task_tool} '
                             f'completed with result:\n{result}')
                if task_tool == "shell_code_task":
                    logging.info(f'[Debug] {result}')
                self.environment.set_task_result(
                    task=task,
                    result=result
                )
                task_succeeded, evaluator_comment \
                    = self.critic.evaluate_execution(overall_task, task)
                logging.info(f'Task {task_name} with tool {task_tool} '
                             f'{"succeeded" if task_succeeded else "failed"}:'
                             f'\n{json.dumps(evaluator_comment, indent=4)}')
            except Exception as e:
                result = f"Exception encountered: {e}\n{traceback.format_exc()}"
                logging.info(f'Task {task_name} with tool {task_tool} '
                             f'failed as {result}')

                task_succeeded = False
                self.environment.set_task_result(
                    task=task,
                    result=result
                )
                evaluator_comment = {
                    'score': 0,
                    'explanation': ''
                }

            self.evaluation_display(task, task_succeeded, evaluator_comment)
            if task_succeeded:
                break

            retry_count += 1
            if retry_count > max_retries:
                logging.error(f'Task {task_name} failed after {max_retries} retries')
                return

            logging.info(f'Retrying task {task_name} (Attempt {retry_count}/{max_retries})')
            self.critic.amend_arguments(overall_task, task, result, evaluator_comment)
            task = self.environment.get_task_state(task_name)  # refreshing

        end_time = time.perf_counter()
        duration = end_time - begin_time
        logging.info(f'Processing for task {task_name} with tool {task_tool} '
                     f'finished in {round(duration, 3)}s')

    def relay_input_for_workers(self):  # in a separate thread of the main process
        subscriber = self.environment.get_message_subscriber(
            channels=[INPUT_REQUIRED, END]
        )
        for message in subscriber.listen():
            raw_data = message['data']
            if not isinstance(raw_data, bytes):
                continue

            channel = message["channel"].decode()
            try:
                data = pickle.loads(raw_data)
            except Exception as e:
                logging.error(f'Unable to load data from channel {channel} due to {e}')
            if channel == INPUT_REQUIRED:
                from inputimeout import inputimeout, TimeoutOccurred
                try:
                    user_input = inputimeout(
                        prompt=data["prompt"],
                        timeout=self.INPUT_TIMEOUT
                    )
                    logging.info(f"User input got (length: {len(user_input)}).")
                except TimeoutOccurred:
                    user_input = ""
                    logging.error("Time's up! No user input received.")

                self.environment.set_data_for_subprocess(
                    data=user_input,
                    target_pid=data["target_pid"]
                )
            elif channel == END:
                logging.info(f"Asked to quit")
                break

    def refresh_pending_tasks(self):
        self.pending_task_names = []
        for task_name in self.all_tasks.keys():
            if (task_name not in self.running_task_names
                    and task_name not in self.completed_task_names):
                self.pending_task_names.append(task_name)

    def pending_tasks_exist(self):
        return len(self.pending_task_names) > 0

    def running_tasks_exist(self):
        return len(self.running_task_names) > 0

    @staticmethod
    def get_newly_finished_tasks(async_results):
        return [
            task_name for task_name, result in async_results.items()
            if result.ready()
        ]

    def set_tasks(self, task_list):
        for task in task_list:
            task_name = task["name"]
            self.all_tasks[task_name] = task
        self.refresh_pending_tasks()

        logging.info(f"Current plan:\n{json.dumps(self.all_tasks, indent=4)}")

    def get_a_ready_task(self):
        for task_name in self.pending_task_names:
            task = self.all_tasks[task_name]
            if set(task['dependencies']).issubset(self.completed_task_names):
                return task
        return None

    @staticmethod
    def propagate_exception(task_name, async_results):
        async_results[task_name].get(timeout=0)  # To propagate any exceptions

    def mark_completed_task(self, task_name, async_results):
        if task_name in self.running_task_names:
            del async_results[task_name]
            self.running_task_names.remove(task_name)
        elif task_name in self.pending_task_names:
            self.pending_task_names.remove(task_name)

        self.completed_task_names.append(task_name)  # even originally pending task needs to be appended

    def mark_running_task(self, task_name, result, async_results):
        self.pending_task_names.remove(task_name)
        self.running_task_names.append(task_name)
        async_results[task_name] = result

    # This is a very trick operation
    def replace_a_task(self, original_task, new_task_list):
        original_task_name = original_task["name"]
        del self.all_tasks[original_task_name]

        original_task_predecessors = original_task["dependencies"]
        original_task_successors = []
        for task_name, task in self.all_tasks.items():
            if original_task_name in task["dependencies"]:
                original_task_successors.append(task_name)

        # Step 1: Make sure that new_tasks use new_names
        # Step 1.1: Rename task in new_tasks, if necessary
        name_old_to_new = {}
        for task in new_task_list:
            old_name = task['name']
            if old_name in self.all_tasks:
                new_name = copy.deepcopy(old_name)
                while new_name in self.all_tasks:
                    new_name = new_name + '+'  # TODO: may try better idea
                # self.task_name_history.add(new_name)
                name_old_to_new[old_name] = new_name
        # Step 1.2: Fix dependencies name within new_tasks if necessary
        for task in new_task_list:
            for idx, dep_name in enumerate(task['dependencies']):
                if dep_name in name_old_to_new:
                    dep_new_name = name_old_to_new[dep_name]
                    task['dependencies'][idx] = dep_new_name

            if task['name'] in name_old_to_new:
                new_name = name_old_to_new[task['name']]
                task['name'] = new_name

        # Step 2: Align new_tasks with other tasks
        # Step 2.1: Align new_tasks with predecessors by adding necessary dependencies
        new_tasks_set = set(task['name'] for task in new_task_list)
        new_tasks_that_dont_depend_on_any_other_in_the_list = set()
        for task in new_task_list:
            dont_depend_on_any_other_in_the_list = True
            for dependency in task['dependencies']:
                if dependency in new_tasks_set:
                    dont_depend_on_any_other_in_the_list = False

            if dont_depend_on_any_other_in_the_list:
                new_tasks_that_dont_depend_on_any_other_in_the_list.add(task['name'])
                task['dependencies'] = original_task_predecessors

        # Step 2.2: Align new_tasks with successors by adding necessary dependencies
        tasks_that_no_one_depends_on = copy.deepcopy(new_tasks_set)
        for task in new_task_list:
            for dependency in task['dependencies']:
                if dependency in tasks_that_no_one_depends_on:
                    tasks_that_no_one_depends_on.remove(dependency)
        tasks_that_no_one_depends_on = list(tasks_that_no_one_depends_on)
        for task_name in original_task_successors:
            self.all_tasks[task_name]['dependencies'].remove(original_task_name)
            self.all_tasks[task_name]['dependencies'] += tasks_that_no_one_depends_on

        for task in new_task_list:
            task_name = task["name"]
            self.all_tasks[task_name] = task
        self.refresh_pending_tasks()

        # Avoid double replanning
        newly_ready_tasks = []
        for task_name, task in self.all_tasks.items():
            if task_name in new_tasks_that_dont_depend_on_any_other_in_the_list:
                newly_ready_tasks.append(task)
        return newly_ready_tasks

    def serve(self, query):
        start_time = time.perf_counter()
        logging.info(f"Starting serving the query: {query}")

        num_tasks_launched = 0
        try:
            all_tasks = self.planner.plan(query)
            self.set_tasks(all_tasks)
            async_results = {}

            # Because under the "spawn" start method, sub-processes cannot access the terminal input
            t = threading.Thread(target=self.relay_input_for_workers)
            t.start()

            abort = False
            mp.set_start_method("spawn", force=True)
            with Pool(processes=self.config.max_workers) as pool:
                # Loop until no pending tasks remain and all running tasks have finished
                while self.pending_tasks_exist() or self.running_tasks_exist():

                    # Step 1: Check which running tasks have completed
                    newly_finished_tasks = self.get_newly_finished_tasks(async_results)
                    for task_name in newly_finished_tasks:
                        try:
                            self.propagate_exception(task_name, async_results)
                        except Exception as e:  # TODO: if necessary, deal with it
                            logging.error(f"Task {task_name} not finished due to {e}\n"
                                          f"{traceback.format_exc()}")
                        self.mark_completed_task(task_name, async_results)

                    # Step 2: Schedule any tasks whose dependencies are met
                    while True:
                        ready_task = self.get_a_ready_task()
                        if not ready_task:
                            break

                        # Only try to replan for those tasks having dependencies
                        if ready_task["dependencies"]:
                            adjust_result = self.planner.replan(
                                query=query,
                                pending_task=ready_task
                            )
                            if adjust_result["choice"] == "retain":
                                num_tasks_launched += 1
                                logging.info(f"Num tasks launched: {num_tasks_launched}")
                                if num_tasks_launched > self.config.max_num_tasks_launched:
                                    logging.info(f"Exceeded max number of tasks. Aborting...")
                                    abort = True
                                    break
                                result = pool.apply_async(self.process_a_task, (query, ready_task))
                                self.mark_running_task(ready_task["name"], result, async_results)
                            elif adjust_result["choice"] == "remove":
                                self.mark_completed_task(ready_task["name"], async_results)

                                dummy_result = ("Skipped as the task is already done before, "
                                                "or deemed as irrelevant")
                                self.environment.set_task_result(
                                    task=ready_task,
                                    result=dummy_result
                                )  # TODO: if the task is running, the task_state may be later overwritten
                            else:  # choice == replace
                                derived_ready_tasks = self.replace_a_task(
                                    original_task=ready_task,
                                    new_task_list=adjust_result["detail"]
                                )
                                for derived_ready_task in derived_ready_tasks:
                                    num_tasks_launched += 1
                                    logging.info(f"Num tasks launched: {num_tasks_launched}")
                                    if num_tasks_launched > self.config.max_num_tasks_launched:
                                        logging.info(f"Exceeded max number of tasks. Aborting...")
                                        abort = True
                                        break
                                    result = pool.apply_async(self.process_a_task, (query, derived_ready_task))
                                    self.mark_running_task(derived_ready_task["name"], result, async_results)
                                if abort:
                                    break
                        else:
                            num_tasks_launched += 1
                            logging.info(f"Num tasks launched: {num_tasks_launched}")
                            if num_tasks_launched > self.config.max_num_tasks_launched:
                                logging.info(f"Exceeded max number of tasks. Aborting...")
                                abort = True
                                break
                            result = pool.apply_async(self.process_a_task, (query, ready_task))
                            self.mark_running_task(ready_task["name"], result, async_results)
                    if abort:
                        break

                    # Avoid busy waiting
                    if not ready_task and not newly_finished_tasks:
                        time.sleep(self.config.task_waiting_time_in_sec)
                        continue

        except Exception as e:
            print(f"Failed to serve query due to {e}")
            print(traceback.format_exc())
        finally:
            # to notify other threads to stop
            self.environment.publish_a_message(channel=END, message="done")

            # only need to do this when usnig owl's tools through mcp
            cmd = "ps aux | grep python | grep server.py | grep -v grep | awk '{print $2}' | xargs kill -9"
            try:
                subprocess.run(cmd, shell=True, check=True)
                print("Kill command executed successfully.")
            except subprocess.CalledProcessError as e:
                print(f"Error executing kill command: {e}")

        end_time = time.perf_counter()
        duration = end_time - start_time
        print(f"Query served in {round(duration, 3)}s")
        logging.info(f"Query served in {round(duration, 3)}s")
