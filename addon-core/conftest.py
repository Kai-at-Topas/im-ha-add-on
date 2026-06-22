def pytest_configure(config):
    # Unregister ROS launch_testing plugins that define hooks unknown to this
    # pytest version, causing PluginValidationError when running in a
    # ROS-sourced shell environment.
    ros_path = "/opt/ros"
    for plugin in list(config.pluginmanager.get_plugins()):
        module_file = getattr(plugin, "__file__", "") or ""
        if ros_path in module_file and "launch_testing" in module_file:
            config.pluginmanager.unregister(plugin)
