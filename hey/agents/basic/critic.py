import json
import logging
import traceback

from hey.agents.basic.prompt import critic_prompt_dict as new_critic_prompt_dict
from hey.backend.llm.registry import get_llm
from hey.utils.misc import extract_json_from_string


class BasicCritic():
    def __init__(self, config, environment):
        self.config = config
        self.environment = environment
        self.llm = get_llm(config.llm)
        self.new_prompt_dict = new_critic_prompt_dict

    def evaluate_execution(self, overall_task, task):
        task_name = task["name"]
        logging.info(f"Starting to evaluate task {task_name} with tool {task['tool']}")
        task_state = self.environment.get_task_state(task_name)
        dependencies_states = self.environment.get_task_states(
            task["dependencies"],
            clean_retrieval=True
        )
        result = task_state["result"]

        system_prompt = self.new_prompt_dict['evaluate_system_prompt']
        user_query = self.new_prompt_dict['evaluate_user_query'].format(
            os_name=self.environment.get_os_name(),
            working_dir=self.environment.get_working_dir(),
            dependencies_states=json.dumps(dependencies_states, indent=4),
            task_description=task_state["description"],
            overall_task=overall_task,
            execution_result=json.dumps(result)
        )

        response = self.llm.get_response(
            system_prompt=system_prompt,
            user_query=user_query,
            verbose=False
        )
        evaluation_result = extract_json_from_string(response)
        try:
            score = evaluation_result["score"]
        except KeyError as e:
            logging.info(f"Evaluation failed due to {e}\n{traceback.format_exc()}\n"
                          f"It may because the query is too long: {len(user_query)}")
            score = self.config.success_score_threshold.retrieval  # TODO: temporarily sidestep this exception and move on

        if (score >= self.config
                .success_score_threshold.retrieval):
            succeeded = True
        else:
            succeeded = False
        task_state["most_recent_comment_from_evaluator"] = evaluation_result
        self.environment.update_task_state(task_name, task_state)

        logging.info(f"Evaluation ended for task {task_name}")
        return succeeded, evaluation_result

    def amend_arguments(self, overall_task, task, result, evaluator_comment):
        task_name = task["name"]
        logging.info(f"Starting to amend parameters for task {task_name} with tool {task['tool']}")
        task_state = self.environment.get_task_state(task_name)
        dependencies_states \
            = self.environment.get_task_states(task_names=task["dependencies"])

        system_prompt = self.new_prompt_dict[f'arguments_amend_system_prompt']
        user_query = self.new_prompt_dict['arguments_amend_user_query'].format(
            os_name=self.environment.get_os_name(),
            working_dir=self.environment.get_working_dir(),
            dependencies_states=json.dumps(dependencies_states, indent=4),
            current_task=task,
            overall_task=overall_task,
            execution_result=result,
            comment=evaluator_comment["explanation"]
        )
        response = self.llm.get_response(
            system_prompt=system_prompt,
            user_query=user_query
        )
        update = extract_json_from_string(response)

        if update:
            if "arguments" in update:
                update = update["arguments"]
            task_state.update({
                'arguments': update
            })
            self.environment.update_task_state(task_name, task_state)

            logging.info(f"Parameters amended for task {task_name}. "
                         f"New parameters: {json.dumps(update, indent=4)}")
        else:
            logging.info(f"Parameters not amended for task {task_name} "
                         f"as no valid arguments were extracted")