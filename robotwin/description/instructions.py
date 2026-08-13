import json
import re
import random
from importlib.resources import files
from typing import Any, Dict, List


def _description_path(kind: str, value: str):
    return files("robotwin.description").joinpath(kind, f"{value}.json")


def extract_placeholders(instruction: str) -> List[str]:
    """Extract all placeholders of the form {X} from an instruction."""
    placeholders = re.findall(r"{([^}]+)}", instruction)
    return placeholders


def filter_instructions(instructions: List[str], episode_params: Dict[str, str], rng: random.Random = None) -> List[str]:
    """
    Filter instructions to only include those that have all placeholders
    matching the available episode parameters. No more, no less.
    Also accept instructions that don't contain arm placeholder {[a-z]}.
    
    Args:
        instructions: List of instruction templates
        episode_params: Dictionary of episode parameters
        rng: Random number generator instance (if None, uses global random)
    """
    filtered_instructions = []
    # Create a copy to avoid modifying the original list
    instructions_copy = instructions.copy()
    
    if rng is None:
        random.shuffle(instructions_copy)
    else:
        rng.shuffle(instructions_copy)

    for instruction in instructions_copy:
        placeholders = extract_placeholders(instruction)
        # Remove {} from episode_params keys for comparison
        stripped_episode_params = {key.strip("{}"): value for key, value in episode_params.items()}

        # Get all arm-related parameters (single lowercase letters)
        arm_params = {key for key in stripped_episode_params.keys() if len(key) == 1 and "a" <= key <= "z"}
        non_arm_params = set(stripped_episode_params.keys()) - arm_params
        
        # Accept if we have exact match OR if the only missing parameters are arm parameters
        if set(placeholders) == set(stripped_episode_params.keys()) or (
                # Special case: accept if the only difference is missing arm parameters
                arm_params and set(placeholders).union(arm_params) == set(stripped_episode_params.keys()) and
                not arm_params.intersection(set(placeholders))):
            filtered_instructions.append(instruction)

    return filtered_instructions


def replace_placeholders(instruction: str, episode_params: Dict[str, str], rng: random.Random = None) -> str:
    """Replace all {X} placeholders in the instruction with corresponding values from episode_params.
    For arm placeholders {[a-z]}, add 'the ' in front and ' arm' after the value.
    If the value is a path to an existing JSON file, randomly choose one 'description' item and prepend 'the'.
    If the value contains '\' or '/' but the file does not exist, print a bold warning.
    
    Args:
        instruction: Instruction template with placeholders
        episode_params: Dictionary of episode parameters
        rng: Random number generator instance (if None, uses global random)
    """
    # Remove {} from episode_params keys for replacement
    stripped_episode_params = {key.strip("{}"): value for key, value in episode_params.items()}

    for key, value in stripped_episode_params.items():
        placeholder = "{" + key + "}"
        # Check if the value contains '\' or '/'
        if "\\" in value or "/" in value:
            json_path = _description_path("objects_description", value)
            if not json_path.is_file():
                raise ValueError(
                    f"RoboTwin object description does not exist: {value!r}"
                )

        # Check if the value is a path to an existing JSON file
        json_path = _description_path("objects_description", value)
        if json_path.is_file():
            with json_path.open("r", encoding="utf-8") as f:
                json_data = json.load(f)
            # Randomly choose one description and prepend 'the'
            descriptions = json_data.get("seen", [])
            if rng is None:
                description = random.choice(descriptions)
            else:
                description = rng.choice(descriptions)
            value = f"the {description}"
        # Check if the key is a single lowercase letter (arm placeholder)
        elif len(key) == 1 and "a" <= key <= "z":
            value = f"the {value} arm"
        else:
            value = f"{value}"

        instruction = instruction.replace(placeholder, value)

    return instruction


def replace_placeholders_unseen(instruction: str, episode_params: Dict[str, str], rng: random.Random = None) -> str:
    """Similar to replace_placeholders but uses 'unseen' descriptions from JSON files.
    For arm placeholders {[a-z]}, add 'the ' in front and ' arm' after the value.
    If the value is a path to an existing JSON file, randomly choose one 'unseen' description and prepend 'the'.
    If the value contains '\' or '/' but the file does not exist, print a bold warning.
    
    Args:
        instruction: Instruction template with placeholders
        episode_params: Dictionary of episode parameters
        rng: Random number generator instance (if None, uses global random)
    """
    # Remove {} from episode_params keys for replacement
    stripped_episode_params = {key.strip("{}"): value for key, value in episode_params.items()}

    for key, value in stripped_episode_params.items():
        placeholder = "{" + key + "}"
        # Check if the value contains '\' or '/'
        if "\\" in value or "/" in value:
            json_path = _description_path("objects_description", value)
            if not json_path.is_file():
                raise ValueError(
                    f"RoboTwin object description does not exist: {value!r}"
                )

        # Check if the value is a path to an existing JSON file
        json_path = _description_path("objects_description", value)
        if json_path.is_file():
            with json_path.open("r", encoding="utf-8") as f:
                json_data = json.load(f)
            # Randomly choose one unseen description and prepend 'the'
            if "unseen" in json_data and json_data["unseen"]:
                descriptions = json_data.get("unseen", [])
                if rng is None:
                    description = random.choice(descriptions)
                else:
                    description = rng.choice(descriptions)
                value = f"the {description}"
            else:
                # Fall back to seen descriptions if unseen is empty
                descriptions = json_data.get("seen", [])
                if rng is None:
                    description = random.choice(descriptions)
                else:
                    description = rng.choice(descriptions)
                value = f"the {description}"
        # Check if the key is a single lowercase letter (arm placeholder)
        elif len(key) == 1 and "a" <= key <= "z":
            value = f"the {value} arm"
        else:
            value = f"{value}"

        instruction = instruction.replace(placeholder, value)

    return instruction


def load_task_instructions(task_name: str) -> Dict[str, Any]:
    """Load the task instructions from the JSON file."""
    file_path = _description_path("task_instruction", task_name)
    if not file_path.is_file():
        raise ValueError(f"RoboTwin task instruction is not packaged: {task_name!r}")
    with file_path.open("r", encoding="utf-8") as f:
        task_data = json.load(f)
    return task_data


def generate_episode_descriptions(task_name: str, episodes: List[Dict[str, str]], max_descriptions: int = 1000000, seed: int = None):
    """
    Generate descriptions for episodes by replacing placeholders in instructions with parameter values.
    For each episode, filter instructions that have matching placeholders and generate up to
    max_descriptions by replacing placeholders with parameter values.
    Now also generates unseen descriptions.
    
    Args:
        task_name: Name of the task (JSON file name without extension)
        episodes: List of episode parameters
        max_descriptions: Maximum number of descriptions per episode
        seed: Random seed for reproducible results. If None, uses global random state.
    """
    # Create a local Random instance if seed is provided
    rng = random.Random(seed) if seed is not None else None
    
    # Load task instructions
    task_data = load_task_instructions(task_name)
    seen_instructions = task_data.get("seen", [])
    unseen_instructions = task_data.get("unseen", [])

    # Store generated descriptions for each episode
    all_generated_descriptions = []

    # Process each episode
    for i, episode in enumerate(episodes):
        # Filter instructions that have all placeholders matching episode parameters
        filtered_seen_instructions = filter_instructions(seen_instructions, episode, rng)
        filtered_unseen_instructions = filter_instructions(unseen_instructions, episode, rng)

        if filtered_seen_instructions == [] and filtered_unseen_instructions == []:
            print(f"Episode {i}: No valid instructions found")
            continue

        # Generate seen descriptions by replacing placeholders
        seen_episode_descriptions = []
        flag_seen = True
        while (len(seen_episode_descriptions) < max_descriptions and flag_seen and filtered_seen_instructions):
            for instruction in filtered_seen_instructions:
                if len(seen_episode_descriptions) >= max_descriptions:
                    flag_seen = False
                    break
                description = replace_placeholders(instruction, episode, rng)
                seen_episode_descriptions.append(description)

        # Generate unseen descriptions by replacing placeholders
        unseen_episode_descriptions = []
        flag_unseen = True
        while (len(unseen_episode_descriptions) < max_descriptions and flag_unseen and filtered_unseen_instructions):
            for instruction in filtered_unseen_instructions:
                if len(unseen_episode_descriptions) >= max_descriptions:
                    flag_unseen = False
                    break
                description = replace_placeholders_unseen(instruction, episode, rng)
                unseen_episode_descriptions.append(description)

        all_generated_descriptions.append({
            "episode_index": i,
            "seen": seen_episode_descriptions,
            "unseen": unseen_episode_descriptions,
        })

    return all_generated_descriptions
