# VARIABLES---------------------------------------------------------------------
export HOME="/home/ubuntu"
export REPO="lunchbox"
export REPO_DIR="$HOME/$REPO"
export REPO_SNAKE_CASE=`echo $REPO | sed 's/-/_/g'`
export REPO_SUBPACKAGE="$REPO_DIR/python/$REPO_SNAKE_CASE"
export REPO_COMMAND_FILE="$REPO_SUBPACKAGE/command.py"
export PATH=":$HOME/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$HOME/.local/lib"
export PYTHONPATH="$REPO_DIR/python:$HOME/.local/lib"
export BUILD_DIR="$HOME/build"
export CONFIG_DIR="$REPO_DIR/docker/config"
export PDM_DIR="$HOME/pdm"
export SCRIPT_DIR="$REPO_DIR/docker/scripts"
export MIN_PYTHON_VERSION="3.7"
export MAX_PYTHON_VERSION="3.10"
export TEST_VERBOSITY=0
export TEST_PROCS="auto"
export JUPYTER_PLATFORM_DIRS=0
export JUPYTER_CONFIG_PATH=/home/ubuntu/.jupyter
alias cp=cp  # "cp -i" default alias asks you if you want to clobber files

# COLORS------------------------------------------------------------------------
export BLUE1='\033[0;34m'
export BLUE2='\033[0;94m'
export CYAN1='\033[0;36m'
export CYAN2='\033[0;96m'
export GREEN1='\033[0;32m'
export GREEN2='\033[0;92m'
export GREY1='\033[0;90m'
export GREY2='\033[0;37m'
export PURPLE1='\033[0;35m'
export PURPLE2='\033[0;95m'
export RED1='\033[0;31m'
export RED2='\033[0;91m'
export WHITE='\033[0;97m'
export YELLOW1='\033[0;33m'
export YELLOW2='\033[0;93m'
export CLEAR='\033[0m'

# GENERATE-FUNCTIONS------------------------------------------------------------
_x_repeat () {
    # Echo a given character until it reaches the width of the current terminal
    # args: character
    local width=`tput cols -T xterm`;
    for i in {1..$width}; do
        if [ "$SHELL" = "/usr/bin/zsh" ]; then
            echo -n - $1;
        else
            echo -n $1;
        fi;
    done;
}
export SPACER=`_x_repeat -`

_x_resolve_exit_code () {
    # Returns error code if either code is not 0
    # args: exit code 1, exit code 2
    if [ "$1" -ne "0" ]; then
        echo $1;
        return;
    elif [ "$2" -ne "0" ]; then
        echo $2;
        return;
    fi;
    echo 0;
}

_x_for_each_version () {
    # Runs a given command against multiple python versions
    # Expands version variable in command string
    # args: command (string)

    # create version array
    local min=`echo $MIN_PYTHON_VERSION | sed 's/3.//'`;
    local max=`echo $MAX_PYTHON_VERSION | sed 's/3.//'`;
    for i in {$min..$max}; do
        __versions[$i]="3.$i";
    done;

    # run command for each version
    local exit_code=0;
    for VERSION in $__versions; do
        eval "$1";
        exit_code=`_x_resolve_exit_code $exit_code $?`;
    done;
    return $exit_code;
}

_x_gen_pyproject () {
    # Generates pyproject.toml content given a mode
    # args: mode (dev, test or prod)
    if [ "$1" = "dev" ]; then
        # rolling-pin mangles formatting so use sed
        # add -dev to project.name to avoid circular and ambiguous dependencies
        cat $CONFIG_DIR/pyproject.toml \
            |  sed -E "s/name.*$REPO.*/name = \"$REPO-dev\"/";

    elif [ "$1" = "test" ]; then
        rolling-pin toml $CONFIG_DIR/pyproject.toml \
            --edit "project.requires-python=\">=$MIN_PYTHON_VERSION\"" \
            --delete "tool.pdm.dev-dependencies.lab" \
            --delete "tool.pdm.dev-dependencies.dev";

    elif [ "$1" = "prod" ]; then
        rolling-pin toml $CONFIG_DIR/pyproject.toml \
            --edit "project.requires-python=\">=$MIN_PYTHON_VERSION\"" \
            --delete "tool.pdm.dev-dependencies.lab" \
            --delete "tool.pdm.dev-dependencies.dev";

    elif [ "$1" = "package" ]; then
        rolling-pin toml $CONFIG_DIR/pyproject.toml \
            --edit "project.requires-python=\">=$MIN_PYTHON_VERSION\"" \
            --delete "tool.pdm.dev-dependencies" \
            --delete "tool.mypy" \
            --delete "tool.pdm" \
            --delete "tool.pytest";
    fi;
}

_x_gen_pdm_files () {
    # Generate pyproject.tom, .pdm.toml and pdm.lock files
    # args: mode, python version

    # pyproject.toml
    _x_gen_pyproject $1 > $PDM_DIR/pyproject.toml;

    # pdm.lock
    rm -f $PDM_DIR/pdm.lock;
    cp -f $CONFIG_DIR/$1.lock $PDM_DIR/pdm.lock;

    # get python path
    local pypath=`_x_env_get_python $1 $2`;

    # .pdm.toml
    rolling-pin toml $CONFIG_DIR/pdm.toml \
        --edit "venv.prompt=\"$1-{python_version}\"" \
        --edit "python.path=\"$pypath\"" \
        --target $PDM_DIR/.pdm.toml;
}

# ENV-FUNCTIONS-----------------------------------------------------------------
_x_env_exists () {
    # determines if given env exists
    # args: environment name
    cd $PDM_DIR;
    local temp=`pdm venv list | grep $1`;
    if [ -n "$temp" ]; then
        echo "true";
    else
        echo "false";
    fi;
}

_x_env_get_path () {
    # gets path of given environment
    # args: environment name
    cd $PDM_DIR;
    pdm venv list | grep $1 | awk '{print $3}';
}

_x_env_get_python () {
    # gets python interpreter path of given environment
    # args: mode, python version
    local penv=`_x_env_get_path $1-$2`;
    if [ -n "$penv" ]; then
        echo $penv;
    else
        echo /usr/bin/python$2;
    fi;
}

_x_env_create () {
    # Create a virtual env given a mode and python version
    # args: mode, python_version
    cd $PDM_DIR;
    _x_gen_pdm_files $1 $2;
    pdm venv create -n $1-$2;
}

x_env_activate () {
    # Activate a virtual env given a mode and python version
    # args: mode, python_version
    local CWD=`pwd`;
    cd $PDM_DIR;
    _x_gen_pdm_files $1 $2;
    . `pdm venv activate $1-$2 | awk '{print $2}'`;
    cd $CWD;
}

_x_env_lock () {
    # Resolve dependencies listed in pyrproject.toml into a pdm.lock file
    # args: mode, python_version
    cd $PDM_DIR;
    x_env_activate $1 $2 && \
    pdm lock -v && \
    cat $PDM_DIR/pdm.lock > $CONFIG_DIR/$1.lock;
}

_x_env_sync () {
    # Install dependencies from a pdm.lock into a virtual env specified by a
    # given mode and python version
    # args: mode, python_version
    cd $PDM_DIR;
    x_env_activate $1 $2 && \
    # run `pdm lock`` if lock file is empty
    if [ `cat pdm.lock | wc -l` = 0 ]; then
        pdm lock -v
    fi && \
    pdm sync --no-self --dev --clean -v && \
    deactivate;
}

x_env_activate_dev () {
    # Activates dev environment
    x_env_activate dev $MAX_PYTHON_VERSION;
}

x_env_activate_prod () {
    # Activates prod environment
    x_env_activate prod $MAX_PYTHON_VERSION;
}

x_env_init () {
    # Create a virtual env with dependencies given a mode and python version
    # args: mode, python_version
    cd $PDM_DIR;
    _x_env_create $1 $2;
    _x_env_sync $1 $2;
}

# BUILD-FUNCTIONS---------------------------------------------------------------
_x_build () {
    # Build repo for testing, packaging and publishing
    # args: type (test or prod)
    x_env_activate_dev;
    rm -rf $BUILD_DIR;
    rolling-pin conform \
        $CONFIG_DIR/build.yaml \
        --groups base,$1;
    _x_gen_pyproject $1 > $BUILD_DIR/repo/pyproject.toml;
    touch $BUILD_DIR/repo/$REPO_SNAKE_CASE/py.typed;
}

_x_build_show_dir () {
    # Run tree command on build directory
    exa --tree --all $BUILD_DIR;
    echo;
}

_x_build_show_package () {
    # Run tree command on untarred pip package
    cd $BUILD_DIR/dist;
    mkdir /tmp/dist;
    local package=`ls | grep tar.gz`;
    tar xvf $package -C /tmp/dist;
    echo "\n${CYAN2}$package${CLEAR}";
    exa --tree --all /tmp/dist;
    rm -rf /tmp/dist;
    echo;
}

x_build_package () {
    # Generate pip package of repo in $HOME/build/repo
    x_env_activate_dev;
    x_build_prod;
    cd $BUILD_DIR/repo;
    echo "${CYAN2}BUILDING PIP PACKAGE${CLEAR}\n";
    pdm build --dest $BUILD_DIR/dist -v;
    rm -rf $BUILD_DIR/repo/build;
    _x_build_show_package;
}

x_build_prod () {
    # Build production version of repo for publishing
    echo "${CYAN2}BUILDING PROD REPO${CLEAR}\n";
    _x_build prod;
    _x_gen_pyproject package > $BUILD_DIR/repo/pyproject.toml;
    _x_build_show_dir;
}

_x_build_publish () {
    # Publish pip package of repo to PyPi
    # args: user, password, comment
    x_build_package;
    cd $BUILD_DIR;
    echo "${CYAN2}PUBLISHING PIP PACKAGE TO PYPI${CLEAR}\n";
    pdm publish \
        --no-build \
        --username "$1" \
        --password "$2" \
        --comment "$3" \
        --verbose;
}

x_build_publish () {
    # Run production tests first then publish pip package of repo to PyPi
    # args: user, password, comment
    x_test_prod;
    # break out if tests produced errors
    if [ "$?" -ne "0" ]; then
        echo "\n$SPACER";
        echo "${RED2}ERROR: Encountered error in testing, exiting before publish.${CLEAR}" >&2;
        return $?;
    else
        _x_build_publish $1 $2 $3;
    fi;
}

x_build_test () {
    # Build test version of repo for prod testing
    echo "${CYAN2}BUILDING TEST REPO${CLEAR}\n";
    _x_build test;
    _x_build_show_dir;
}

# DOCS-FUNCTIONS----------------------------------------------------------------
x_docs () {
    # Generate sphinx documentation
    x_env_activate_dev;
    cd $REPO_DIR;
    echo "${CYAN2}GENERATING DOCS${CLEAR}\n";
    mkdir -p docs;
    pandoc README.md -o sphinx/intro.rst;
    sphinx-build sphinx docs;
    cp -f sphinx/style.css docs/_static/style.css;
    touch docs/.nojekyll;
    mkdir -p docs/resources;
}

x_docs_architecture () {
    # Generate architecture.svg diagram from all import statements
    echo "${CYAN2}GENERATING ARCHITECTURE DIAGRAM${CLEAR}\n";
    x_env_activate_dev;
    rolling-pin graph \
        $REPO_DIR/python $REPO_DIR/docs/architecture.svg \
        --exclude 'test|mock|__init__' \
        --orient 'lr';
}

x_docs_full () {
    # Generate documentation, coverage report, architecture diagram and code
    # metrics
    x_docs && x_docs_metrics && x_docs_architecture && x_test_coverage;
}

x_docs_metrics () {
    # Generate code metrics report, plots and tables
    echo "${CYAN2}GENERATING METRICS${CLEAR}\n";
    x_env_activate_dev;
    cd $REPO_DIR;
    rolling-pin plot \
        $REPO_DIR/python $REPO_DIR/docs/plots.html;
    rolling-pin table \
        $REPO_DIR/python $REPO_DIR/docs;
}

# LIBRARY-FUNCTIONS-------------------------------------------------------------
_x_library_pdm_to_repo_dev () {
    # Copies pdm/pyproject.toml and pdm/pdm.lock to repo's pyproject.toml and
    # dev.lock files
    cp -f $PDM_DIR/pdm.lock $CONFIG_DIR/dev.lock;
    cat $PDM_DIR/pyproject.toml \
        | sed -E "s/name.*$REPO-dev.*/name = \"$REPO\"/" \
        > $CONFIG_DIR/pyproject.toml;
}

_x_library_pdm_to_repo_prod () {
    # Copies pdm/pdm.lock to repo's prod.lock
    cp -f $PDM_DIR/pdm.lock $CONFIG_DIR/prod.lock;
}

_x_library_sync () {
    # Sync lock with given environment
    # args: mode, python_version
    x_env_activate $1 $2;
    echo "${CYAN2}DEPENDENCY SYNC $1-$2${CLEAR}\n";
    cd $PDM_DIR;
    pdm sync --no-self --dev --clean -v;
    deactivate;
    x_env_activate_dev;
}

x_library_add () {
    # Add a given package to a given dependency group
    # args: package, group
    x_env_activate_dev;
    echo "${CYAN2}ADDING PACKAGE TO DEV DEPENDENCIES${CLEAR}\n";
    cd $PDM_DIR;
    if [ "$2" = '' ] || [ "$2" = 'default' ]; then
        pdm add --no-self $1 -v;
    else
        pdm add --no-self -dG $2 $1 -v;
    fi;
    _x_library_pdm_to_repo_dev;
}

x_library_graph_dev () {
    # Graph dependencies in dev environment
    x_env_activate_dev;
    echo "${CYAN2}DEV DEPENDENCY GRAPH${CLEAR}\n";
    cd $PDM_DIR;
    pdm list --graph;
}

x_library_graph_prod () {
    # Graph dependencies in prod environment
    x_env_activate_prod;
    echo "${CYAN2}PROD DEPENDENCY GRAPH${CLEAR}\n";
    cd $PDM_DIR;
    pdm list --graph;
    deactivate;
    x_env_activate_dev;
}

x_library_install_dev () {
    # Install all dependencies into dev environment
    x_library_lock_dev;
    x_library_sync_dev;
}

x_library_install_prod () {
    # Install all dependencies into prod environment
    x_library_lock_prod;
    x_library_sync_prod;
}

x_library_list_dev () {
    # List packages in dev environment
    x_env_activate_dev;
    echo "${CYAN2}DEV DEPENDENCIES${CLEAR}\n";
    cd $PDM_DIR;
    pdm list --sort name --fields name,version,groups;
}

x_library_list_prod () {
    # List packages in prod environment
    x_env_activate_prod;
    echo "${CYAN2}PROD DEPENDENCIES${CLEAR}\n";
    cd $PDM_DIR;
    pdm list --sort name --fields name,version,groups;
    deactivate;
    x_env_activate_dev;
}

x_library_lock_dev () {
    # Resolve dev.lock file
    x_env_activate_dev;
    echo "${CYAN2}DEV DEPENDENCY LOCK${CLEAR}\n";
    cd $PDM_DIR;
    pdm lock -v;
    _x_library_pdm_to_repo_dev;
}

x_library_lock_prod () {
    # Resolve prod.lock file
    x_env_activate_prod;
    echo "${CYAN2}PROD DEPENDENCY LOCK${CLEAR}\n";
    cd $PDM_DIR;
    pdm lock -v;
    _x_library_pdm_to_repo_prod;
    deactivate;
    x_env_activate_dev;
}

x_library_remove () {
    # Remove a given package from a given dependency group
    # args: package, group
    x_env_activate_dev;
    echo "${CYAN2}REMOVING PACKAGE FROM DEV DEPENDENCIES${CLEAR}\n";
    cd $PDM_DIR;
    if [ "$2" = '' ] || [ "$2" = 'default' ]; then
        pdm remove $1 -v;
    else
        pdm remove -dG $2 $1 -v;
    fi;
    _x_library_pdm_to_repo_dev;
}

x_library_search () {
    # Search for pip packages
    # args: package name
    x_env_activate_dev;
    cd $PDM_DIR;
    pdm search $1;
}

x_library_sync_dev () {
    # Sync dev environment with packages listed in dev.lock
    echo "${CYAN2}SYNC DEV DEPENDENCIES${CLEAR}\n";
    _x_library_sync dev $MAX_PYTHON_VERSION;
}

x_library_sync_prod () {
    # Sync prod environment with packages listed in prod.lock
    echo "${CYAN2}SYNC PROD DEPENDENCIES${CLEAR}\n";
    _x_for_each_version '_x_library_sync prod $VERSION';
}

x_library_update () {
    # Update a given package, or all packages, from a given dependency group
    # args: package, group
    x_env_activate_dev;
    echo "${CYAN2}UPDATING DEV DEPENDENCIES${CLEAR}\n";
    cd $PDM_DIR;
    if [ "$2" = '' ] || [ "$2" = 'default' ]; then
        pdm update --no-self $1 -v;
    else
        pdm update --no-self -dG $2 $1 -v;
    fi;
    _x_library_pdm_to_repo_dev;
}

# SESSION-FUNCTIONS-------------------------------------------------------------
x_session_app () {
    # Run app
    x_env_activate_dev;
    echo "${CYAN2}APP${CLEAR}\n";
    python3 $REPO_SUBPACKAGE/server/app.py;
}

x_session_lab () {
    # Run jupyter lab server
    x_env_activate_dev;
    echo "${CYAN2}JUPYTER LAB${CLEAR}\n";
    jupyter lab \
        --allow-root \
        --ip=0.0.0.0 \
        --no-browser;
}

x_session_python () {
    # Run python session with dev dependencies
    x_env_activate_dev;
    python3;
}

# TEST-FUNCTIONS----------------------------------------------------------------
x_test_coverage () {
    # Generate test coverage report
    x_env_activate_dev;
    echo "${CYAN2}GENERATING TEST COVERAGE REPORT${CLEAR}\n";
    cd $REPO_DIR;
    mkdir -p docs;
    pytest \
        -c $CONFIG_DIR/pyproject.toml \
        --numprocesses $TEST_PROCS \
        --verbosity $TEST_VERBOSITY \
        --cov=python \
        --cov-config=$CONFIG_DIR/pyproject.toml \
        --cov-report=html:docs/htmlcov \
        $REPO_DIR/python;
}

x_test_dev () {
    # Run all tests
    x_env_activate_dev;
    echo "${CYAN2}TESTING DEV${CLEAR}\n";
    cd $REPO_DIR;
    pytest \
        -c $CONFIG_DIR/pyproject.toml \
        --numprocesses $TEST_PROCS \
        --verbosity $TEST_VERBOSITY \
        $REPO_DIR/python;
}

x_test_fast () {
    # Test all code excepts tests marked with SKIP_SLOWS_TESTS decorator
    x_env_activate_dev;
    echo "${CYAN2}FAST TESTING DEV${CLEAR}\n";
    cd $REPO_DIR;
    SKIP_SLOW_TESTS=true && \
    pytest \
        -c $CONFIG_DIR/pyproject.toml \
        --numprocesses $TEST_PROCS \
        --verbosity $TEST_VERBOSITY \
        $REPO_DIR/python;
}

x_test_lint () {
    # Run linting and type checking
    x_env_activate_dev;
    cd $REPO_DIR;
    echo "${CYAN2}LINTING${CLEAR}\n";
    flake8 python --config $CONFIG_DIR/flake8.ini;
    echo "${CYAN2}TYPE CHECKING${CLEAR}\n";
    mypy python --config-file $CONFIG_DIR/pyproject.toml;
}

x_test_run () {
    # Run test in given environment
    # args: mode, python_version
    x_env_activate $1 $2;
    local exit_code=$?;

    cd $BUILD_DIR/repo;
    echo "${CYAN2}LINTING $1-$2${CLEAR}\n";
    flake8 --config flake8.ini $REPO_SUBPACKAGE;
    exit_code=`_x_resolve_exit_code $exit_code $?`;

    echo "${CYAN2}TYPE CHECKING $1-$2${CLEAR}\n";
    mypy --config-file pyproject.toml $REPO_SUBPACKAGE;
    exit_code=`_x_resolve_exit_code $exit_code $?`;

    echo "${CYAN2}TESTING $1-$2${CLEAR}\n";
    pytest \
        -c pyproject.toml \
        --numprocesses $TEST_PROCS \
        --verbosity $TEST_VERBOSITY \
        $REPO_SUBPACKAGE;
    exit_code=`_x_resolve_exit_code $exit_code $?`;

    deactivate;
    x_env_activate_dev;
    return $exit_code;
}

x_test_prod () {
    # Run tests across all support python versions
    x_env_activate_dev;
    x_build_test;
    _x_for_each_version 'x_test_run prod $VERSION';
}

# VERSION-FUNCTIONS-------------------------------------------------------------
x_version () {
    # Full resolution of repo: dependencies, linting, tests, docs, etc
    x_library_install_dev;
    x_test_lint;
    x_docs_full;
}

x_version_bump_major () {
    # Bump repo's major version
    x_env_activate_dev;
    echo "${CYAN2}BUMPING MAJOR VERSION${CLEAR}\n";
    cd $PDM_DIR
    pdm bump major;
    _x_library_pdm_to_repo_dev;
}

x_version_bump_minor () {
    # Bump repo's minor version
    x_env_activate_dev;
    echo "${CYAN2}BUMPING MINOR VERSION${CLEAR}\n";
    cd $PDM_DIR
    pdm bump minor;
    _x_library_pdm_to_repo_dev;
}

x_version_bump_patch () {
    # Bump repo's patch version
    x_env_activate_dev;
    echo "${CYAN2}BUMPING PATCH VERSION${CLEAR}\n";
    cd $PDM_DIR
    pdm bump patch;
    _x_library_pdm_to_repo_dev;
}
