import socket
import random
import os
import gym_gazebo
from multiprocessing import Process

from launch import LaunchService, LaunchDescription
from launch.actions.execute_process import ExecuteProcess
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory, get_package_prefix


def start_launch_servide_process(ld):
    """Starts a Launch Service process. To be called from subclasses.

    Args:
         ld : LaunchDescription obj.
    """
    # Create the LauchService and feed the LaunchDescription obj. to it.
    ls = LaunchService()
    ls.include_launch_description(ld)
    p = Process(target=ls.run)
    p.start()

def is_port_in_use(port):
    """Checks if the given port is being used.

    Args:
        port(int): Port number.

    Returns:
        bool: True if the port is being used, False otherwise.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def get_exclusive_network_parameters():
    """Creates appropriate values for ROS_DOMAIN_ID and GAZEBO_MASTER_URI.

    Returns:
        Dictionary {ros_domain_id (string), ros_domain_id (string)}
    """
    random_port = random.randint(10000, 15000)
    while is_port_in_use(random_port):
        print("Randomly selected port is already in use, retrying.")
        random_port = random.randint(10000, 15000)
    return {'ros_domain_id':str(random_port),
     'gazebo_master_uri':"http://localhost:" + str(random_port)}

def generate_launch_description_mara(gzclient, real_speed):
    """
        Returns ROS2 LaunchDescription object.
        Args:
            real_speed: bool   True if RTF must be set to 1, False if RTF must be set to maximum.
    """
    urdf = os.path.join(get_package_share_directory('mara_description'), 'urdf', 'mara_robot_camera_top.urdf')
    mara = get_package_share_directory('mara_gazebo_plugins')
    install_dir = get_package_prefix('mara_gazebo_plugins')
    ros2_ws_path = os.path.abspath(os.path.join(install_dir, os.pardir))
    MARA_model_path = os.path.join(ros2_ws_path, 'src', 'MARA')
    MARA_plugin_path = os.path.join(ros2_ws_path, 'src', 'MARA', 'mara_gazebo_plugins', 'build')

    if not real_speed:
        world_path = os.path.join(os.path.dirname(gym_gazebo.__file__), 'worlds', 'empty__state_plugin__speed_up.world')
    else:
        world_path = os.path.join(os.path.dirname(gym_gazebo.__file__), 'worlds', 'empty__state_plugin.world')

    if 'GAZEBO_MODEL_PATH' in os.environ:
        os.environ['GAZEBO_MODEL_PATH'] =  (os.environ['GAZEBO_MODEL_PATH'] + ':' + install_dir + 'share'
                                            + ':' + MARA_model_path)
    else:
        os.environ['GAZEBO_MODEL_PATH'] =  install_dir + "/share" + ':' + MARA_model_path

    if 'GAZEBO_PLUGIN_PATH' in os.environ:
        os.environ['GAZEBO_PLUGIN_PATH'] = (os.environ['GAZEBO_PLUGIN_PATH'] + ':' + install_dir + '/lib'
                                            + ':' + MARA_plugin_path)
    else:
        os.environ['GAZEBO_PLUGIN_PATH'] = install_dir + '/lib' + ':' + MARA_plugin_path


    # Exclusive network segmentation, which allows to launch multiple instances of ROS2+Gazebo
    network_params = get_exclusive_network_parameters()
    os.environ["ROS_DOMAIN_ID"] = network_params.get('ros_domain_id')
    os.environ["GAZEBO_MASTER_URI"] = network_params.get('gazebo_master_uri')
    print("ROS_DOMAIN_ID=" + network_params.get('ros_domain_id'))
    print("GAZEBO_MASTER_URI=" + network_params.get('gazebo_master_uri'))

    try:
        envs = {}
        for key in os.environ.__dict__["_data"]:
            key = key.decode("utf-8")
            if (key.isupper()):
                envs[key] = os.environ[key]
    except Exception as e:
        print("Error with Envs: " + str(e))
        return None

    # Gazebo visual interfaze. GUI/no GUI options.
    if gzclient:
        gazebo_cmd = "gazebo"
    else:
        gazebo_cmd = "gzserver"

    # Creation of ROS2 LaunchDescription obj.
    ld = LaunchDescription([
        ExecuteProcess(
            cmd=[gazebo_cmd,'--verbose', '-s', 'libgazebo_ros_factory.so', '-s', 'libgazebo_ros_init.so', world_path], output='screen',
            env=envs
        ),
        Node(package='robot_state_publisher', node_executable='robot_state_publisher', output='screen', arguments=[urdf]),
        Node(package='mara_utils_scripts', node_executable='spawn_entity.py', output='screen'),
        Node(package='hros_cognition_mara_components', node_executable='hros_cognition_mara_components', output='screen',
            arguments=["-motors", install_dir + "/share/hros_cognition_mara_components/link_order.yaml"])
    ])
    return ld
