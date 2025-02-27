import os
import shutil

def additional_packaging(addon_name=None):
    paths_to_remove = [
        f"output/{addon_name}/lib/PureCloudPlatformClientV2/__pycache__",
        f"output/{addon_name}/lib/PureCloudPlatformClientV2/apis/__pycache__",
        f"output/{addon_name}/lib/PureCloudPlatformClientV2/models/__pycache__"
    ]

    for remove_path in paths_to_remove:
        if os.path.isdir(remove_path):
            shutil.rmtree(remove_path)
