from robotwin.config import load_task_config


def get_camera_config(camera_type):
    camera_args = load_task_config("_camera_config")

    assert camera_type in camera_args, f"camera {camera_type} is not defined"
    return camera_args[camera_type]
