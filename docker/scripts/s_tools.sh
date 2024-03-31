# VARIABLES---------------------------------------------------------------------
export USER="ubuntu"
export HOME="/home/$USER"
export REPO="hidebound"
export REPO_DIR="$HOME/$REPO"
export S6_DIR="/etc/s6-overlay"
export S6_RC_DIR="$S6_DIR/s6-rc.d"

# FUNCTIONS---------------------------------------------------------------------
s_create_content () {
    # create contents.d item for s6 service
    # args: service
    mkdir -p "$S6_RC_DIR/user/contents.d";
    touch "$S6_RC_DIR/user/contents.d/$1";
}

s_create_oneshot () {
    # create oneshot s6 service
    # args: service
    s_create_content $1;
    mkdir -p "$S6_RC_DIR/$1/dependencies.d";
    mkdir -p "$S6_DIR/scripts";
    echo "$S6_DIR/scripts/$1.sh" > "$S6_RC_DIR/$1/up";
    echo oneshot > "$S6_RC_DIR/$1/type";
}

s_create_longrun () {
    # create longrun s6 service
    # args: service
    s_create_content $1;
    mkdir -p "$S6_RC_DIR/$1/dependencies.d";
    echo longrun > "$S6_RC_DIR/$1/type";
}

s_add_dependency () {
    # add dependency to s6 service
    # args: service, dependency
    touch "$S6_RC_DIR/$1/dependencies.d/$2";
}

_s_chmod () {
    # change permissions of give file
    # args: filepath
    touch $1;
    chown $USER:$USER $1;
    chmod 755 $1;
}

s_create_init () {
    # create s6 init service
    s_create_oneshot init;
    mkdir -p /etc/s6-overlay/scripts;
    _s_chmod /etc/s6-overlay/scripts/init.sh;
    cat << EOF > /etc/s6-overlay/scripts/init.sh
#!/command/with-contenv bash

if [ "\$SKIP_S6_SERVICE" != "true" ]; then
    mkdir -p $HOME/.jupyter;
    cp -ran $REPO_DIR/docker/config/jupyter/* $HOME/.jupyter/;
    cp $REPO_DIR/docker/config/zshrc $HOME/.zshrc;
fi;
EOF
}

s_create_jupyterlab () {
    # create s6 jupyterlab service
    s_create_longrun jupyterlab;
    mkdir -p /etc/s6-overlay/s6-rc.d/jupyterlab;
    _s_chmod /etc/s6-overlay/s6-rc.d/jupyterlab/run;
    cat << EOF > /etc/s6-overlay/s6-rc.d/jupyterlab/run
#!/command/with-contenv zsh

if [ "\$SKIP_S6_SERVICE" != "true" ]; then
    source $HOME/.zshrc &&
    x_env_activate_dev &&
    exec jupyter lab \\
        --notebook-dir="$REPO_DIR/notebooks" \\
        --ip=0.0.0.0 \\
        --no-browser \\
        --allow-root \\
        --port=8888 \\
        --ServerApp.token="" \\
        --ServerApp.password="" \\
        --ServerApp.allow_origin="*" \\
        --ServerApp.allow_remote_access=True \\
        --ServerApp.authenticate_prometheus=False \\
        --ServerApp.base_url="\$NB_PREFIX";
fi;
EOF
}

s_setup_services () {
    # setup s6 services
    s_create_init;
    s_create_jupyterlab;
    s_add_dependency jupyterlab init;
}
