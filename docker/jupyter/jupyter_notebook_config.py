c = get_config()
c.NotebookApp.iopub_data_rate_limit = 10000000
c.NotebookApp.notebook_dir = '/root/hidebound/notebooks'
c.NotebookApp.disable_check_xsrf = True
c.NotebookApp.password_required = False
c.NotebookApp.port = 9000
c.NotebookApp.terminado_settings = {'shell_command': ['/bin/zsh']}
c.NotebookApp.token = ''
