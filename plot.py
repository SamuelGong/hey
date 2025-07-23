import re
import os
import sys
import queue
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Patch


def extract_timestamp(line):
    pattern = r'\[\((?P<date>\d{4}-\d{2}-\d{2})\)\s+(?P<time>\d{2}:\d{2}:\d{2}\.\d{3})\]'
    match = re.search(pattern, line)
    if match:
        # Combine captured groups
        timestamp_str = f"{match.group('date')} {match.group('time')}"
        # Convert to datetime object (optional)
        dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S.%f")
        return dt
    else:
        raise ValueError(f"Could not parse timestamp: {line}")


def do_analyze(log_path):
    with open(log_path, 'r') as f:
        lines = f.readlines()

    activities = []
    plan_queue = queue.Queue()
    task_dict = {}
    ref_timestamp = None
    for line in lines:
        if line.startswith('[INFO]') or line.startswith('[ERROR]'):
            timestamp = extract_timestamp(line)
            if 'Starting serving the query' in line:
                ref_timestamp = timestamp

            # plan
            elif "Starting to plan" in line or "Starting to replan" in line:
                plot_record = {
                    'type': 'plan',
                    'start_timestamp': (timestamp - ref_timestamp).total_seconds()
                }
                if "Starting to plan" in line:
                    plot_record["sub_type"] = "initial"
                else:
                    plot_record["sub_type"] = "adjust"
                plan_queue.put(plot_record)
            elif "Planning ended" in line or "Replanning ended" in line:
                plan_record = plan_queue.get()
                plan_record['end_timestamp'] = (timestamp - ref_timestamp).total_seconds()
                plan_record['duration'] = plan_record['end_timestamp'] - plan_record['start_timestamp']
                activities.append(plan_record)

            # execute
            elif "Starting to process task" in line:
                task_name = line.split('process task ')[1].split(' of type')[0]
                task_record = {
                    'type': 'process',
                    'name': task_name,
                    'start_timestamp': (timestamp - ref_timestamp).total_seconds(),
                    'phase': []
                }

                if "type Python" in line:
                    task_record["sub_type"] = "code"
                elif "type Shell" in line:
                    task_record["sub_type"] = "shell"
                elif "type Retrieval" in line:
                    task_record["sub_type"] = "native"
                elif "type Question" in line:
                    task_record["sub_type"] = "question"

                task_dict[task_name] = task_record
            elif "Starting to generate" in line or "Starting to amend" in line:
                task_name = line.split('for task ')[1].rstrip()
                task_record = task_dict[task_name]
                phase_info = {
                    'type': 'generation',
                    'start_timestamp': (timestamp - ref_timestamp).total_seconds(),
                }
                if "Starting to generate" in line:
                    phase_info['sub_type'] = "initial"
                else:  # "Starting to amend" in line
                    phase_info['sub_type'] = "adjust"
                task_record['phase'].append(phase_info)
            elif "generation ended for task" in line or "amended for task" in line:
                task_name = line.split('for task ')[1].rstrip()
                phase_info = task_dict[task_name]['phase'][-1]
                end_timestamp = (timestamp - ref_timestamp).total_seconds()
                phase_info.update({
                    'end_timestamp': end_timestamp,
                    'duration': end_timestamp - phase_info['start_timestamp']
                })
                task_dict[task_name]['phase'][-1] = phase_info
            elif ("Starting to run" in line
                  or "Starting to do native" in line
                  or "Starting to interact" in line):
                if "Starting to run" in line:
                    task_name = line.split('for task ')[1].rstrip()
                elif "Starting to do native" in line:
                    task_name = line.split('for task ')[1].split(' using query')[0]
                else:  # "Starting to interact" in line
                    task_name = line.split('for task ')[1].split(' by asking')[0]

                task_record = task_dict[task_name]
                phase_info = {
                    'type': 'run',
                    'start_timestamp': (timestamp - ref_timestamp).total_seconds(),
                }
                task_record['phase'].append(phase_info)
            elif ("Code run for task" in line
                  or "Retrieval done for task" in line
                  or "Interaction done for task" in line):

                task_name = line.split('for task ')[1].rstrip()
                phase_info = task_dict[task_name]['phase'][-1]
                end_timestamp = (timestamp - ref_timestamp).total_seconds()
                phase_info.update({
                    'end_timestamp': end_timestamp,
                    'duration': end_timestamp - phase_info['start_timestamp']
                })
                task_dict[task_name]['phase'][-1] = phase_info
            elif "Starting to evaluate" in line:
                task_name = line.split('for task ')[1].rstrip()
                task_record = task_dict[task_name]
                phase_info = {
                    'type': 'evaluate',
                    'start_timestamp': (timestamp - ref_timestamp).total_seconds(),
                }
                task_record['phase'].append(phase_info)
            elif "Evaluation of" in line and "ended for task" in line:
                task_name = line.split('for task ')[1].rstrip()
                phase_info = task_dict[task_name]['phase'][-1]
                end_timestamp = (timestamp - ref_timestamp).total_seconds()
                phase_info.update({
                    'end_timestamp': end_timestamp,
                    'duration': end_timestamp - phase_info['start_timestamp']
                })
                task_dict[task_name]['phase'][-1] = phase_info
            elif ("Processing for task" in line and "finished" in line
                  or "Task " in line and "not finished" in line):
                if "Processing for task" in line and "finished" in line:
                    task_name = line.split('Processing for task ')[1].split(' finished')[0]
                    success = True
                else:
                    task_name = line.split('Task ')[1].split(' not finished')[0]
                    success = False

                task_record = task_dict[task_name]
                end_timestamp = (timestamp - ref_timestamp).total_seconds()
                task_record.update({
                    'success': success,
                    'end_timestamp': end_timestamp,
                    'duration': end_timestamp - task_record['start_timestamp']
                })
                activities.append(task_record)
                del task_dict[task_name]

    return activities


def plot_activities(data, plot_path):
    # Sort activities by start time.
    activities = sorted(data, key=lambda x: x["start_timestamp"])

    # Assign lanes so that overlapping activities are placed at different vertical levels.
    lanes = []
    for activity in activities:
        assigned = False
        for lane_index, lane_end in enumerate(lanes):
            if activity["start_timestamp"] >= lane_end:
                activity["lane"] = lane_index
                lanes[lane_index] = activity["end_timestamp"]
                assigned = True
                break
        if not assigned:
            activity["lane"] = len(lanes)
            lanes.append(activity["end_timestamp"])

    # Define color maps.
    activity_color_map = {
        "plan": "skyblue"
    }
    phase_color_map = {
        "generation": "cornflowerblue",
        "run": "orange",
        "evaluate": "indianred"
    }
    # Refined legend labels for process phases.
    refined_phase_labels = {
        "generation": "process-generation",
        "run": "process-run",
        "evaluate": "process-evaluate"
    }

    # Prepare the plot.
    fig, ax = plt.subplots(figsize=(12, 2 + len(lanes)))
    height = 0.8

    # Hide y-axis ticks and labels.
    ax.set_yticks([])
    # Remove the top, right, and left spines.
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)

    # Dictionaries to hold legend handles.
    activity_handles = {}
    phase_handles = {}

    for act in activities:
        start = act["start_timestamp"]
        end = act["end_timestamp"]
        lane = act["lane"]

        # For process activities, draw phases without outlines, then add an outer outline.
        if act["type"] == "process" and "phase" in act:
            # Draw each phase rectangle without black outlines.
            for phase in act["phase"]:
                p_start = phase["start_timestamp"]
                p_end = phase["end_timestamp"]
                p_width = p_end - p_start
                p_type = phase["type"]
                color = phase_color_map.get(p_type, "gray")
                rect = patches.Rectangle((p_start, lane - height / 2), p_width, height,
                                         facecolor=color, edgecolor=None, alpha=0.6)
                ax.add_patch(rect)
                if p_type not in phase_handles:
                    phase_handles[p_type] = Patch(facecolor=color, edgecolor="none",
                                                  label=refined_phase_labels.get(p_type, p_type))
            # Draw an outer rectangle covering the entire process activity.
            rect_outer = patches.Rectangle((start, lane - height / 2), end - start, height,
                                           facecolor="none", edgecolor="black", linewidth=1)
            ax.add_patch(rect_outer)
            # Annotate the overall process activity.
            label = act.get("name", act["type"])
            overall_center = (start + end) / 2
            formatted_label = "\n".join(label.split('_'))
            ax.text(overall_center, lane, formatted_label, ha="center", va="center", fontsize=9, color="black")
        else:
            # Draw non-process activities as a single rectangle.
            color = activity_color_map.get(act["type"], "gray")
            width = end - start
            rect = patches.Rectangle((start, lane - height / 2), width, height,
                                     facecolor=color, edgecolor="black", alpha=0.6)
            ax.add_patch(rect)
            # Currently "plan" does not need annotation
            label = act.get("name", act["type"])
            if act["type"] not in activity_handles:
                activity_handles[act["type"]] = Patch(facecolor=color, edgecolor="black", label=act["type"])

    # Combine legend handles.
    handles = list(activity_handles.values()) + list(phase_handles.values())
    # Place legend above the plot area in a single row (4 columns) and turn off the frame.
    ax.legend(handles=handles, bbox_to_anchor=(0.5, -0.5), loc="lower center", ncol=4, frameon=False)

    # Configure axes.
    ax.set_xlabel("Time (s)")
    ax.set_xlim(0, max(act["end_timestamp"] for act in activities) + 5)
    ax.set_ylim(-0.5, len(lanes) - 0.5)
    plt.title("Activity Timeline")
    plt.tight_layout()
    plt.savefig(plot_path, bbox_inches="tight", dpi=300)


def main():
    if len(sys.argv) < 2:
        print("Usage: code plot.py '<path to log>'")
        sys.exit(1)

    log_path = sys.argv[1]
    plot_path = os.path.join(os.path.dirname(log_path),
                             os.path.basename(log_path).split(".")[0] + ".png")
    activities = do_analyze(log_path)
    plot_activities(activities, plot_path)


if __name__ == '__main__':
    main()
