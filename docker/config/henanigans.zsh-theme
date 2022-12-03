# henanigans zsh theme

# ---COLORS---------------------------------------------------------------------
local BLACK="\e[30m"
local RED="\e[31m"
local GREEN="\e[32m"
local YELLOW="\e[33m"
local BLUE="\e[34m"
local MAGENTA="\e[35m"
local CYAN="\e[36m"
local LIGHT_GRAY="\e[37m"
local DARK_GRAY="\e[90m"
local LIGHT_RED="\e[91m"
local LIGHT_GREEN="\e[92m"
local LIGHT_YELLOW="\e[93m"
local LIGHT_BLUE="\e[94m"
local LIGHT_MAGENTA="\e[95m"
local LIGHT_CYAN="\e[96m"
local WHITE="\e[97m"
local GREY1="\e[38;5;244m"

# ---EXPORTS--------------------------------------------------------------------
export TERM=xterm-color
export LS_OPTIONS='--color-auto'
export CLICOLOR=TRUE
export LSCOLORS=GafahacabahababaGaGaGa

# ---FUNCTIONS------------------------------------------------------------------
function _bg() {
 echo "%{$BLACK%}"
}

function _user() {
 echo "%{$CYAN%}%n%{$reset_color%}"
}

function _at() {
 echo "%{$YELLOW%}@%{$reset_color%}"
}

function _hostname() {
 echo "%{$GREEN%}%m%{$reset_color%}"
}

function _dir() {
 local _max_pwd_length="200"
 if [[ $(echo -n $PWD | wc -c) -gt ${_max_pwd_length} ]]; then
   echo "%{$YELLOW%}:%-2~ ... %3~%{$reset_color%} "
 else
   echo "%{$YELLOW%}:%~%{$reset_color%} "
 fi
}

function _prompt() {
 echo "%{$RED%}>%{$reset_color%}"
}

function _text() {
 echo "%{$WHITE%} "
}

function _date() {
 echo "%{$YELLOW%}%D{%F}T%{$reset_color%}"
}

function _time() {
 echo "%{$RED%}%D{%H:%M:%S}%{$reset_color%}"
}

function _timezone() {
 echo "%{$YELLOW%}%D{%z}%{$reset_color%}"
}

# ---PROMPTS--------------------------------------------------------------------
ZSH_THEME_GIT_PROMPT_PREFIX="%{$GREY1%}"
ZSH_THEME_GIT_PROMPT_SUFFIX="%{$reset_color%} "

export PROMPT='$(_user)$(_at)$(_hostname)$(_dir)
$(git_prompt_info)$(_prompt)$(_text)'

export RPROMPT='$(_date)$(_time)$(_timezone)'
