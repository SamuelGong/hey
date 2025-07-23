import re
import json
import subprocess

from hey.backend.code.base import Basic, extract_code_from_string


code_generation_system_prompt = """
You are a world-class programmer and your goal is to generate shell code to complete a specific subtask.
The subtask is one of the necessary steps to complete the overall task.
While you should focus on the subtask, description for the overall task is also provided for your reference.
You could only respond with your code.

When installing applications, exclusively use command-line mcp_tools instead of graphical installers, disk images, or even .zip files that contain them.
For example, if the user is using macOS, opt for “brew install” or a similar command rather than downloading .pkg or .dmg files.
Also be aware that after using “brew install,” you might not be able to start the application with the conventional "brew services start."
If this happens, retrieve and refer to the relevant documentation for instructions on customized start methods.

As for correct syntax, double check if you have added a space before the exclamation mark '!'.

The returned shell code should be formatted as follows:
```shell
shell code
```
"""


class Shell(Basic):
    def __init__(self):
        super().__init__()

    @staticmethod
    def parse_commands(code):
        # Remove escaped newlines (i.e., "\n" preceded by a backslash)
        code = re.sub(r'\\\n', ' ESCAPED_NEWLINE ', code)
        # Split by semicolons and newlines (handle both '\n' and ';' delimiters)
        commands = re.split(r'(?<!\\)[;\n]', code)
        # Restore the escaped newlines
        commands = [cmd.replace(' ESCAPED_NEWLINE ', '\\n') for cmd in commands]

        # Strip leading/trailing spaces for each command
        # any pay attention to the combination of && and &
        result = []
        for command in commands:
            command = command.strip()
            if not command:
                continue
            word_split = command.split()
            if word_split[-1] == "&" and '&&' in word_split:
                second_split = command.split('&&')
                for cmd in second_split:
                    cmd = cmd.strip()
                    result.append(cmd)
            else:
                result.append(command)

        return result

    def run_command_by_command(self, code):
        commands = self.parse_commands(code)

        result = []
        for command in commands:
            result.append({
                'command': command,
                'stdout': "",
                'stderr': "",
            })
            if command.split()[-1] == "&":
                background = True
                # Do not use in subprocess.PIPE, otherwise, the background process will exit as the main process exits
                # which may not be desirable
                # The possible choice is subprocess.DEVNULL or None (print to the terminal)
                # TODO: Current choice is subprocess.DEVNULL, can evaluate the issue if any
                process = subprocess.Popen(command,
                                           shell=True,
                                           stdout=subprocess.DEVNULL,
                                           stderr=subprocess.DEVNULL,
                                           executable="/bin/bash")
            else:
                background = False
                process = subprocess.Popen(command,
                                           shell=True,
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE,
                                           executable="/bin/bash")

            # Only wait for foreground process, otherwise the next command will be blocked
            if not background:
                stdout = process.communicate()[0].strip().decode("utf-8")
                stderr = process.communicate()[1].strip().decode("utf-8")
            else:
                stdout = "None (Background job and we do not wait for it)."
                stderr = "None (Background job and we do not wait for it)."

            result[-1].update({
                'stdout': stdout,
                'stderr': stderr,
            })

        return result

    def generate_code(self, query):
        system_prompt = code_generation_system_prompt
        user_query = query
        response = self.coding_llm.get_response(
            system_prompt=system_prompt,
            user_query=user_query
        )
        code = extract_code_from_string(response, 'shell')
        return code

    def execute_code(self, code):
        result = self.run_command_by_command(code=code)
        return json.dumps(result)  # important!
